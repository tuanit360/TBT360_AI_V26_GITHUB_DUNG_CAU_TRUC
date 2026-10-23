import gc
import hashlib
import io
import json
import os
import random
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path

import gradio as gr
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from app.quality import image_diagnostics, diagnostic_notes

ROOT = Path(os.environ['BIMAI360_HOME']).resolve() if os.environ.get('BIMAI360_HOME') else (Path(os.environ['TBT360_HOME']).resolve() if os.environ.get('TBT360_HOME') else Path(__file__).resolve().parents[1])
OUTPUT = ROOT / 'output'
CACHE = ROOT / 'models'
OUTPUT.mkdir(exist_ok=True)
CACHE.mkdir(exist_ok=True)
MODEL_ID = str(ROOT / 'models' / 'sd15') if (ROOT / 'models' / 'sd15' / 'model_index.json').is_file() else 'stable-diffusion-v1-5/stable-diffusion-v1-5'
DEFAULT_PROMPT = ('professional architectural photography, contemporary office building, '
    'realistic facade design, coherent windows and volumes, sustainable architecture, '
    'detailed materials, high quality architectural visualization')
NEGATIVE = ('watermark, text, captions, logo, oversaturated, low quality, '
    'crooked lines, warped perspective, blurry facade, duplicated buildings')
PIPELINES = {}
GPU_DISABLED_FOR_SESSION = False
ACTIVE_LORA = {}
LORA_DIR = ROOT / 'loras'
LORA_DIR.mkdir(exist_ok=True)
LOCK = threading.Lock()
PRESETS = {
    'Xem nhanh · ít VRAM': {'steps': 15, 'guidance': 6.5, 'preserve': 0.55, 'count': 1},
    'Cân bằng · mặc định': {'steps': 28, 'guidance': 7.0, 'preserve': 0.55, 'count': 2},
    'Chi tiết · chậm hơn': {'steps': 40, 'guidance': 7.5, 'preserve': 0.60, 'count': 2},
    'Ý tưởng mới · sáng tạo': {'steps': 32, 'guidance': 7.0, 'preserve': 0.28, 'count': 4},
}
STYLE = {
    'Kiến trúc chân thực': 'realistic architectural photography, natural daylight, physically plausible materials',
    'Nội thất': 'professional interior photography, cohesive furniture, true-to-life lighting',
    'Ngoại thất chiều tối': 'architectural dusk photography, balanced warm artificial lighting, realistic sky',
    'Phối cảnh xanh': 'biophilic sustainable architecture, mature landscape, realistic vegetation',
    'Tôn trọng hình khối': 'respect the source building proportions, maintain facade organization and camera viewpoint',
}


def apply_preset(preset):
    entry = PRESETS[preset]
    return entry['steps'], entry['guidance'], entry['preserve'], entry['count']


def postprocess_image(image, scale, sharpness):
    # Honest deterministic resampling: does not invent AI details.
    result = image.convert('RGB')
    if int(scale) > 1:
        result = result.resize(
            (result.width * int(scale), result.height * int(scale)),
            Image.Resampling.LANCZOS,
        )
    if float(sharpness) > 0:
        result = result.filter(ImageFilter.UnsharpMask(
            radius=1.2, percent=int(75 * float(sharpness)), threshold=3))
    return result


def safe_prompt(brief, style):
    if style not in STYLE:
        raise ValueError('Phong cách không hợp lệ')
    if len(brief or '') > 2000:
        raise ValueError('Mô tả quá dài')
    return ', '.join(part for part in [DEFAULT_PROMPT, STYLE[style], (brief or '').strip()] if part)



def dimensions(aspect):
    return {'Vuông 1:1': (512,512), 'Ngang 4:3': (576,448),
            'Ngang 3:2': (640,448), 'Dọc 3:4': (448,576),
            'Dọc 2:3': (448,640)}[aspect]


def prepare_image(image, aspect, fit_mode):
    source = ImageOps.exif_transpose(image).convert('RGB')
    target_size = dimensions(aspect)
    if fit_mode == 'Giữ đủ ảnh (thêm viền)':
        result = ImageOps.pad(source, target_size, color=(230,231,230), method=Image.Resampling.LANCZOS)
    else:
        result = ImageOps.fit(source, target_size, method=Image.Resampling.LANCZOS)
    return result, hashlib.sha256(source.tobytes()).hexdigest()


def get_pipeline(memory_mode):
    global GPU_DISABLED_FOR_SESSION
    import torch
    from diffusers import AutoPipelineForImage2Image
    use_cuda = (
        not GPU_DISABLED_FOR_SESSION
        and os.environ.get('BIMAI360_FORCE_CPU') != '1'
        and torch.cuda.is_available()
    )
    cache_key = (memory_mode, 'cuda' if use_cuda else 'cpu')
    if cache_key in PIPELINES:
        return PIPELINES[cache_key]
    dtype = torch.float16 if use_cuda else torch.float32
    pipe = AutoPipelineForImage2Image.from_pretrained(
        MODEL_ID, torch_dtype=dtype, use_safetensors=True, cache_dir=str(CACHE),
        local_files_only=os.environ.get('TBT360_OFFLINE') == '1')
    if use_cuda:
        try:
            if memory_mode == 'Tiết kiệm VRAM tối đa':
                pipe.enable_sequential_cpu_offload()
                placement = 'CUDA sequential CPU offload (rất chậm nhưng tiết kiệm VRAM)'
            else:
                pipe.to('cuda')
                placement = 'CUDA trực tiếp (nhanh hơn, dùng nhiều VRAM hơn)'
        except (RuntimeError, AssertionError) as exc:
            # A visible GPU can fail during device placement. Recreate a clean
            # fp32 CPU pipeline rather than reuse a partially offloaded instance.
            import logging
            logging.getLogger('bimai360').warning(
                'GPU initialization failed; retrying clean CPU pipeline: %s',
                type(exc).__name__,
            )
            del pipe
            GPU_DISABLED_FOR_SESSION = True
            use_cuda = False
            cache_key = (memory_mode, 'cpu')
            if cache_key in PIPELINES:
                return PIPELINES[cache_key]
            pipe = AutoPipelineForImage2Image.from_pretrained(
                MODEL_ID, torch_dtype=torch.float32, use_safetensors=True,
                cache_dir=str(CACHE),
                local_files_only=os.environ.get('TBT360_OFFLINE') == '1',
            )
            pipe.to('cpu')
            placement = 'CPU dự phòng (GPU khởi tạo thất bại)'
    else:
        pipe.to('cpu')
        placement = 'CPU (có thể rất chậm)'
    if memory_mode == 'Tiết kiệm VRAM tối đa' or not use_cuda:
        pipe.enable_attention_slicing()
    try:
        pipe.enable_vae_slicing()
    except (AttributeError, ValueError):
        pass
    PIPELINES[cache_key] = (pipe, placement)
    return PIPELINES[cache_key]


def installed_loras():
    from app.lora_validation import verified_adapters
    return ['Không dùng LoRA'] + verified_adapters(LORA_DIR)


def select_lora(pipe, memory_mode, adapter_name):
    # Offloaded CUDA pipelines can report CPU as their active device.
    # Track the actual pipeline instance, not its transient device.
    device_key = id(pipe)
    current = ACTIVE_LORA.get(device_key, 'Không dùng LoRA')
    if current == adapter_name:
        return
    if current != 'Không dùng LoRA':
        pipe.unload_lora_weights()
    if adapter_name != 'Không dùng LoRA':
        import re
        if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', adapter_name):
            raise ValueError('Tên LoRA không hợp lệ')
        if adapter_name not in installed_loras():
            raise ValueError('LoRA không có trạng thái hoàn thành hoặc hash không khớp')
        path = LORA_DIR / adapter_name
        if not (path / 'pytorch_lora_weights.safetensors').is_file():
            raise ValueError('Không tìm thấy trọng số LoRA')
        pipe.load_lora_weights(str(path), weight_name='pytorch_lora_weights.safetensors')
    ACTIVE_LORA[device_key] = adapter_name


def create(source_image, brief, preserve, steps, count, seed, aspect, fit_mode, memory_mode, lora_name, style, guidance, scale, sharpness, progress=gr.Progress()):
    global GPU_DISABLED_FOR_SESSION
    if source_image is None:
        raise gr.Error('Hãy nạp một ảnh phối cảnh tham chiếu.')
    if not isinstance(source_image, Image.Image):
        raise gr.Error('Ảnh đầu vào không hợp lệ.')
    if not (10 <= int(steps) <= 50 and 1 <= int(count) <= 4 and 0.15 <= float(preserve) <= 0.85):
        raise gr.Error('Thông số sinh ảnh ngoài giới hạn an toàn.')
    if not (1.0 <= float(guidance) <= 12.0) or int(scale) not in (1, 2, 4):
        raise gr.Error('Thông số hậu xử lý hoặc guidance không hợp lệ.')
    if not (0.0 <= float(sharpness) <= 1.0):
        raise gr.Error('Độ sắc nét không hợp lệ.')
    from app.architecture_preflight import inspect_reference, cpu_generation_recommendation
    inspection = inspect_reference(source_image)
    if not inspection['ready']:
        raise gr.Error('; '.join(inspection['blocking']))
    with LOCK:
        started = time.perf_counter()
        try:
            import torch
            pipe, runtime = get_pipeline(memory_mode)
            select_lora(pipe, memory_mode, lora_name)
            source, digest = prepare_image(source_image, aspect, fit_mode)
            seed0 = int(seed) if int(seed) >= 0 else random.SystemRandom().randint(1,2**31-2)
            prompt = safe_prompt(brief, style)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            run_dir = OUTPUT / f'run_{timestamp}_{seed0}'
            run_dir.mkdir(parents=True,exist_ok=False)
            source.save(run_dir/'reference_prepared.png')
            generated=[]
            manifest={'schema':'tbt360.image_generation.v1','model':MODEL_ID,
                'model_is_pretrained':True,'lora_name':lora_name,
                'fine_tuned_on_user_dataset':lora_name != 'Không dùng LoRA',
                'fine_tune_training_verified':lora_name in installed_loras() and lora_name != 'Không dùng LoRA',
                'output_type':'concept_images_not_BIM',
                'original_image_sha256_pixels':digest,'prompt':prompt,
                'negative_prompt':NEGATIVE,'preserve':float(preserve),
                'strength':1-float(preserve),'steps':int(steps),'guidance_scale':float(guidance),
                'style':style,'output_scale':int(scale),'unsharp_amount':float(sharpness),
                'postprocess_method':'PIL Lanczos + optional unsharp mask (not AI super-resolution)',
                'aspect':aspect,
                'fit_mode':fit_mode,'memory_mode':memory_mode,'runtime':runtime,
                'images':[], 'quality_method':'diagnostics only, no learned aesthetics or BIM validation',
                'input_preflight':inspection,
                'cpu_advice':cpu_generation_recommendation(torch.cuda.is_available(), steps, count, scale)}
            for index in range(int(count)):
                progress(index / int(count), desc=f'Đang sinh ảnh {index+1}/{int(count)}')
                current_seed=seed0+index
                generator=torch.Generator(device='cpu').manual_seed(current_seed)
                result=pipe(prompt=prompt,negative_prompt=NEGATIVE,image=source,
                    strength=1-float(preserve),guidance_scale=float(guidance),
                    num_inference_steps=int(steps),generator=generator).images[0]
                fname=f'architecture_option_{index+1:02d}_seed_{current_seed}.png'
                result = postprocess_image(result, scale, sharpness)
                from app.generated_image_gate import validate_generated_image
                quality_evidence = validate_generated_image(
                    result, prepared_input=source if int(scale) == 1 else None)
                result.save(run_dir/fname, optimize=True)
                generated.append((str(run_dir/fname), f'Phương án {index+1} · seed {current_seed}'))
                diag = image_diagnostics(result)
                manifest['images'].append({'file':fname,'seed':current_seed,
                    'diagnostics':diag,'visual_output_gate':quality_evidence,
                    'review_flags':diagnostic_notes(diag)})
                del result
                # Avoid forcing GPU synchronization/cache flush after every image.
                # Offload and pipeline lifetime are managed by Diffusers.
            progress(1, desc='Đang tạo gói kết quả')
            manifest['elapsed_seconds']=round(time.perf_counter()-started,2)
            (run_dir/'generation.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
            archive_path=run_dir.with_suffix('.zip')
            with zipfile.ZipFile(archive_path,'w',zipfile.ZIP_DEFLATED) as archive:
                for path in sorted(run_dir.iterdir()):
                    archive.write(path,arcname=path.name)
            status=(f'Sinh thành công {len(generated)} phương án; {manifest["elapsed_seconds"]} giây. '
                f'Chế độ: {runtime}. Đã lưu ảnh + seed + tham số vào {archive_path.name}. ' +
                ('Đây là ảnh concept, không phải BIM. LoRA hợp lệ đã được áp dụng.' if lora_name != 'Không dùng LoRA' else 'Đây là ảnh concept pretrained, chưa fine-tune trên ảnh riêng.'))
            return generated, str(archive_path), status
        except torch.cuda.OutOfMemoryError as exc:
            # Evict the failed CUDA pipeline. Never silently retry the same
            # diffusion operation: explicit user action preserves seed/output.
            import logging
            GPU_DISABLED_FOR_SESSION = True
            for key in tuple(PIPELINES):
                if key[1] == 'cuda':
                    failed_pipe, _ = PIPELINES.pop(key)
                    ACTIVE_LORA.pop(id(failed_pipe), None)
            logging.getLogger('bimai360').warning(
                'CUDA OOM; GPU disabled for this session. Next attempt uses CPU.'
            )
            raise gr.Error(
                'GPU hết VRAM. Lần thử tiếp theo sẽ dùng CPU; '
                'hãy chọn 1 ảnh, 10–15 bước.'
            ) from exc
        except Exception:
            # Preserve the original exception and traceback for diagnostics.
            raise


def preflight():
    results = []
    try:
        import torch
        results.append(f'PyTorch {torch.__version__}')
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            vram = props.total_memory / 2**30
            results.append(f'CUDA: {props.name} ({vram:.1f} GiB VRAM)')
            if vram < 6:
                results.append('CẢNH BÁO: VRAM thấp, chọn tiết kiệm tối đa; có thể OOM')
            if vram < 8:
                results.append('LoRA training không hỗ trợ trong cấu hình này; dùng GPU >=8 GiB')
        else:
            results.append('CẢNH BÁO: Không thấy GPU CUDA; CPU sinh ảnh rất chậm')
        from diffusers import AutoPipelineForImage2Image
        results.append('Diffusers: import OK')
    except Exception as exc:
        results.append(f'LỖI phụ thuộc: {type(exc).__name__}: {exc}')
    results.append(f'LoRA đã xác minh SHA256: {len(installed_loras())-1}')
    results.append('Kiểm tra này chưa tải mô hình và chưa chứng minh sinh ảnh thành công')
    return '\n'.join(results)


def machine_info():
    try:
        import torch
        if torch.cuda.is_available():
            props=torch.cuda.get_device_properties(0)
            return f'GPU: {props.name} · VRAM: {props.total_memory/2**30:.1f} GiB · Torch: {torch.__version__}'
        return f'Không nhận GPU CUDA; xử lý trên CPU (rất chậm). Torch: {torch.__version__}'
    except Exception as exc:
        return f'Chưa thiết lập PyTorch: {exc}'


with gr.Blocks(title='BIM AI Kiến Trúc 360 V271 · Thiết kế kiến trúc') as ui:
    gr.Markdown('# BIM AI Kiến Trúc 360 V271 · Không gian làm việc')
    gr.Markdown('**QUY TRÌNH:** Tạo phương án → Kiểm tra → Bàn giao → Dữ liệu → Đào tạo. Chọn tab ngang, sau đó chọn chức năng bên dưới.')
    from app.local_workspace import setup_runtime_log
    setup_runtime_log(ROOT)
    with gr.Tabs():
        with gr.Tab("01 · TẠO PHƯƠNG ÁN"):
            with gr.Tabs():
                with gr.Tab("Thiết kế và sinh ảnh"):
                    with gr.Row():
                        with gr.Column(scale=1, min_width=360):
                            reference=gr.Image(label='Ảnh công trình tham chiếu',type='pil',sources=['upload'],height=270)
                            gr.Markdown('### Kiểm tra ảnh và chẩn đoán tại chỗ')
                            reference_render = gr.HTML(
                                label='Ảnh kiểm tra trực tiếp',
                                value='<p>Chưa kiểm tra ảnh.</p>',
                            )
                            reference_check_status = gr.Textbox(
                                label='Kết quả kiểm tra ảnh đầu vào',
                                interactive=False,
                            )
                            image_debug_log = gr.Textbox(
                                label='LOG CHẨN ĐOÁN ẢNH (có thể bôi đen và Ctrl+C)',
                                lines=9,
                                interactive=False,
                                show_copy_button=True,
                            )
                            def run_reference_diagnostic(image):
                                from datetime import datetime, timezone
                                from app.reference_image_check import inspect_reference_image
                                from app.diagnostic_image_render import render_diagnostic_image
                                from app.local_workspace import record_operation
                                import logging
                                timestamp = datetime.now(timezone.utc).isoformat()
                                try:
                                    preview, message = inspect_reference_image(image)
                                    if preview is None:
                                        record_operation(ROOT, 'check_model', 'failed')
                                        return '<p>Không thể hiển thị ảnh.</p>', message, (
                                            f'{timestamp} | IMAGE_INPUT | FAIL | {message}'
                                        )
                                    markup = render_diagnostic_image(preview)
                                    record_operation(ROOT, 'check_model', 'completed')
                                    log = (
                                        f'{timestamp} | IMAGE_INPUT | PASS | '
                                        f'{preview.width}x{preview.height} RGB | '
                                        'INLINE_PNG_DATA_URI | Không dùng endpoint /file='
                                    )
                                    return markup, message, log
                                except Exception as exc:
                                    logging.getLogger('bimai360').exception('Reference render failed')
                                    record_operation(ROOT, 'check_model', 'failed')
                                    message = 'Kiểm tra ảnh thất bại; xem runtime_errors.log'
                                    return '<p>Lỗi kết xuất ảnh.</p>', message, (
                                        f'{timestamp} | IMAGE_INPUT | FAIL | '
                                        f'{type(exc).__name__} | {message}'
                                    )
                            gr.Button(
                                'KIỂM TRA VÀ HIỂN THỊ ẢNH (KHÔNG CẦN AI)'
                            ).click(
                                run_reference_diagnostic,
                                inputs=reference,
                                outputs=[
                                    reference_render, reference_check_status,
                                    image_debug_log,
                                ],
                                api_name='kiem_tra_truyen_anh',
                            )
                            def gradio_image_transport_smoke():
                                from PIL import Image
                                from app.diagnostic_image_render import render_diagnostic_image
                                return render_diagnostic_image(
                                    Image.new('RGB', (128, 96), (60, 120, 180))
                                )
                            gr.Button(
                                'KIỂM TRA RENDER ĐỘC LẬP (KHÔNG CẦN AI)'
                            ).click(
                                gradio_image_transport_smoke,
                                outputs=reference_render,
                                api_name='kiem_tra_render_doc_lap',
                            )
                            def refresh_image_debug_log():
                                from app.local_workspace import read_runtime_log
                                return read_runtime_log(ROOT, lines=80)
                            gr.Button('LẤY LOG MỚI NHẤT ĐỂ COPY').click(
                                refresh_image_debug_log, outputs=image_debug_log,
                            )
                            brief=gr.Textbox(label='Mô tả phương án (tiếng Việt; mô hình SD1.5 dùng mô tả tiếng Anh)',lines=3,
                                value='Contemporary office building, dark vertical facade fins, rooftop garden, urban corner site, realistic architectural visualization, daylight',
                                placeholder='Nhập mô tả phương án hoặc chọn nội dung mẫu')
                            preset=gr.Dropdown(choices=list(PRESETS),value='Xem nhanh · ít VRAM',label='Chọn mức chất lượng')
                            style=gr.Dropdown(choices=list(STYLE),value='Kiến trúc chân thực',label='Phong cách')
                            preserve=gr.Slider(0.15,0.85,value=0.55,step=0.05,label='Giữ cấu trúc ảnh gốc (cao = ít thay đổi)')
                            with gr.Accordion('Thông số kỹ thuật',open=False):
                                aspect=gr.Dropdown(choices=list(['Vuông 1:1','Ngang 4:3','Ngang 3:2','Dọc 3:4','Dọc 2:3']),
                                    value='Ngang 4:3',label='Tỷ lệ ảnh')
                                fit_mode=gr.Radio(choices=['Giữ đủ ảnh (thêm viền)','Cắt đầy khung'],
                                    value='Giữ đủ ảnh (thêm viền)',label='Khớp ảnh')
                                memory_mode=gr.Radio(choices=['Cân bằng','Tiết kiệm VRAM tối đa'],
                                    value='Tiết kiệm VRAM tối đa',label='Quản lý GPU')
                                steps=gr.Slider(10,50,value=15,step=1,label='Số bước xử lý')
                                guidance=gr.Slider(1,12,value=7.0,step=0.5,label='Mức bám mô tả (CFG)')
                                count=gr.Slider(1,4,value=1,step=1,label='Số phương án')
                                seed=gr.Number(value=-1,precision=0,label='Seed (-1 = ngẫu nhiên)')
                                lora_name=gr.Dropdown(choices=installed_loras(),value='Không dùng LoRA',label='Bộ tinh chỉnh AI (LoRA) đã xác minh')
                                refresh_lora=gr.Button('Làm mới danh sách LoRA')
                                refresh_lora.click(lambda: gr.update(choices=installed_loras(),value='Không dùng LoRA'),outputs=lora_name)
                            with gr.Accordion('Hậu xử lý ảnh · không phải AI upscale',open=False):
                                scale=gr.Radio(choices=[1,2,4],value=1,label='Hệ số phóng Lanczos')
                                sharpness=gr.Slider(0,1,value=0.2,step=0.1,label='Làm nét nhẹ')
                            start=gr.Button('TẠO PHƯƠNG ÁN',variant='primary',size='lg')
                        with gr.Column(scale=2,min_width=380):
                            gallery=gr.HTML(value='<p>Chưa có ảnh AI. Hãy kiểm tra model và nhấn TẠO PHƯƠNG ÁN.</p>')
                            export=gr.File(label='Tải gói ảnh và thông số tạo ảnh (ZIP)')
                            status=gr.Textbox(label='Tiến trình và thông báo',lines=3,interactive=False)
                    gr.Markdown('**Bắt đầu:** Nạp ảnh → Chọn cấu hình → Tạo phương án → Xem kết quả. Nếu thiếu checkpoint, phần mềm phải báo thiếu thay vì xuất ảnh giả.')
                    readiness_button = gr.Button('KIỂM TRA GPU / MODEL TRƯỚC KHI TẠO')
                    readiness_result = gr.JSON(label='Khả năng chạy AI thực tế')
                    def show_readiness():
                        from app.cpu_readiness import inspect_local_assets
                        try:
                            import torch
                            cuda = torch.cuda.is_available()
                        except (ImportError, RuntimeError):
                            cuda = False
                        result = inspect_local_assets(ROOT, cuda_available=cuda)
                        result['trained_architecture_vlm_bundled'] = False
                        result['photo_to_full_bim_model_bundled'] = False
                        return result
                    readiness_button.click(show_readiness, outputs=readiness_result)
                    gr.Markdown('**Máy GPU nhỏ:** mặc định xem nhanh 1 phương án, 15 bước. Chế độ tiết kiệm bộ nhớ có thể xử lý chậm; muốn nhanh hơn cần GPU đủ bộ nhớ để chạy trực tiếp. Ảnh đầu ra chỉ được chấp nhận nếu qua kiểm tra chất lượng.')
                    preset.change(apply_preset,inputs=preset,outputs=[steps,guidance,preserve,count])
                    def create_with_feedback(*arguments, progress=gr.Progress()):
                        from app.image_generation_contract import image_generation_contract
                        from app.cpu_readiness import inspect_local_assets
                        offline = os.environ.get('TBT360_OFFLINE') == '1'
                        readiness = inspect_local_assets(ROOT) if offline else None
                        return image_generation_contract(
                            ROOT, create, arguments,
                            progress=progress, offline=offline,
                            readiness=readiness,
                        )
                    start.click(
                        create_with_feedback,
                        inputs=[
                            reference, brief, preserve, steps, count, seed,
                            aspect, fit_mode, memory_mode, lora_name, style,
                            guidance, scale, sharpness,
                        ],
                        outputs=[gallery, export, status, image_debug_log],
                        concurrency_limit=1,
                        show_progress='full',
                    )
                with gr.Tab("Mô hình 2D / 3D"):
                    with gr.Accordion('BIMAI360 · TẠO MẶT BẰNG / MẶT ĐỨNG SƠ BỘ TỪ KÍCH THƯỚC', open=True):
                        gr.Markdown('Tạo vỏ công trình chữ nhật từ kích thước **bạn nhập**, cùng ID tường và tầng cho BIM. '
                                    '**Chưa suy diễn mặt bằng từ ảnh, chưa bố trí phòng/cửa/MEP hay xuất IFC.**')
                        with gr.Row():
                            scheme_project = gr.Textbox(value='office_121', label='Mã công trình')
                            scheme_width = gr.Number(value=12, label='Ngang (m)')
                            scheme_depth = gr.Number(value=8, label='Sâu (m)')
                            scheme_height = gr.Number(value=3.2, label='Chiều cao mỗi tầng (m)')
                            scheme_floors = gr.Number(value=3, precision=0, label='Số tầng')
                        scheme_button = gr.Button('TẠO PHƯƠNG ÁN VỎ BIM / MẶT BẰNG / MẶT ĐỨNG', variant='primary')
                        sample_button = gr.Button('DÙNG DỰ ÁN MẪU / TẠO BIM CONCEPT 2 TẦNG')
                        gr.Markdown('**Dự án mẫu:** hình học canonical tường/sàn/mái/cửa theo kích thước có sẵn, không phải AI suy luận từ ảnh.')
                        scheme_archive = gr.File(label='ZIP gồm BIM canonical JSON + 2 bản vẽ SVG')
                        scheme_report = gr.JSON(label='Thông tin mô hình vỏ sơ bộ')
                        def export_schematic(project, width, depth, height, floors):
                            from app.local_workspace import record_operation
                            record_operation(ROOT, 'concept_export', 'started')
                            from app.schematic_architecture import create_schematic, render_views
                            from app.bim_transaction import canonical_checksum
                            try:
                                model = create_schematic(project, width, depth, height, floors)
                                from app.schematic_slabs import add_schematic_slabs
                                model = add_schematic_slabs(model)
                                from app.schematic_roof import add_gable_roof
                                model = add_gable_roof(model)
                                from app.wall_openings import add_wall_opening
                                model = add_wall_opening(
                                    model, 'W01_01', 'DOOR_01', 1.0, 0.0, 1.0, 2.1)
                                model = add_wall_opening(
                                    model, 'W01_03', 'WINDOW_01', 2.0, 0.9, 1.5, 1.3)
                                from app.schematic_delivery_audit import audit_schematic_building
                                delivery_audit = audit_schematic_building(model)
                                files = render_views(model)
                                files['KIEM_TRA_HINH_HOC.json'] = json.dumps(
                                    delivery_audit, ensure_ascii=False, indent=2)
                                from app.schematic_multiview import schematic_multiview
                                extra = schematic_multiview(model)
                                meta = extra.pop('view_meta')
                                files.update(extra)
                                files['view_meta.json'] = json.dumps(meta, ensure_ascii=False, indent=2)
                                from app.schematic_dxf import export_plan_dxf
                                files['schematic_plan.dxf'] = export_plan_dxf(model)
                                target = OUTPUT / ('schematic_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
                                target.mkdir()
                                (target / 'canonical_bim_handoff.json').write_text(
                                    json.dumps(model, ensure_ascii=False, indent=2), encoding='utf-8')
                                for file_name, contents in files.items():
                                    (target / file_name).write_text(contents, encoding='utf-8')
                                from app.canonical_3d_export import export_building_glb
                                wall_mesh = export_building_glb(model, target / 'schematic_walls.glb')
                                (target / 'schematic_wall_id_mapping.json').write_text(
                                    json.dumps({'canonical_wall_entity_ids': wall_mesh['wall_entity_ids'],
                                                'geometry_source': wall_mesh['geometry_source'],
                                                'geometry_verified': wall_mesh['geometry_verified'],
                                                'canonical_slab_entity_ids': wall_mesh['slab_entity_ids'],
                                                'canonical_roof_entity_ids': wall_mesh['roof_entity_ids']},
                                               ensure_ascii=False, indent=2), encoding='utf-8')
                                from app.handoff_roundtrip import verify_exported_handoff
                                roundtrip_report = verify_exported_handoff(target, model)
                                (target / 'KIEM_TRA_MO_LAI.json').write_text(
                                    json.dumps(roundtrip_report, ensure_ascii=False, indent=2),
                                    encoding='utf-8')
                                archive_path = str(target) + '.zip'
                                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
                                    for path in sorted(target.iterdir()):
                                        archive.write(path, path.name)
                                record_operation(ROOT, 'concept_export', 'completed')
                                return archive_path, {
                                    'entity_count': len(model['entities']), 'levels': len(model['levels']),
                                    'model_checksum': canonical_checksum(model),
                                    'kiem_tra_hinh_hoc': delivery_audit,
                                    'kiem_tra_mo_lai': roundtrip_report,
                                    'source': 'explicit_user_constraints', 'ifc_export_ready': False,
                                    'limitations': 'Mô hình vỏ theo kích thước nhập, chưa suy ra mặt bằng từ ảnh',
                                }
                            except Exception as exc:
                                record_operation(ROOT, 'concept_export', 'failed')
                                from app.generation_failures import explain_generation_failure
                                return None, {
                                    'trang_thai': 'KHÔNG THỂ TẠO BIM',
                                    'loai_loi': type(exc).__name__,
                                    'huong_dan': 'Xem Tài khoản → Nhật ký hoạt động hoặc kiểm tra gói dữ liệu',
                                    'chi_tiet': str(exc)[:250] if isinstance(exc, ValueError) else
                                                'Lỗi xuất BIM hoặc kiểm tra mở lại; xem nhật ký để xác định bước lỗi.',
                                }
                        def generate_native_sample():
                            return export_schematic('OFFICE_001_DEMO', 12.0, 9.0, 3.2, 2)
                        sample_button.click(generate_native_sample, outputs=[scheme_archive, scheme_report], api_name='tao_bim_mau')
                        gr.Markdown('**Trước khi tạo BIM:** đây là mô hình từ kích thước nhập, không phải AI suy luận từ ảnh. Nếu xuất tệp thất bại, báo cáo bên dưới sẽ ghi trạng thái bằng tiếng Việt thay vì chỉ hiển thị Error.')
                        scheme_button.click(export_schematic,
                                            inputs=[scheme_project, scheme_width, scheme_depth, scheme_height, scheme_floors],
                                            outputs=[scheme_archive, scheme_report], api_name='tao_bim')
                    with gr.Accordion('BIMAI360 · PHÂN KHU CÔNG NĂNG SƠ BỘ', open=False):
                        gr.Markdown('Chia vỏ nhà chữ nhật thành hai khu linh hoạt theo tỷ lệ 55/45, '
                                    'dùng cùng dữ liệu canonical để xuất sơ đồ. **Không phải AI suy ra từ ảnh** '
                                    'và chưa có cửa, giao thông, MEP hoặc kiểm chứng tiêu chuẩn.')
                        with gr.Row():
                            zone_project = gr.Textbox(value='office_136', label='Mã công trình')
                            zone_width = gr.Number(value=12, label='Ngang (m)')
                            zone_depth = gr.Number(value=8, label='Sâu (m)')
                            zone_height = gr.Number(value=3.2, label='Cao tầng (m)')
                        zone_button = gr.Button('TẠO HAI KHU CÔNG NĂNG / XUẤT BIM JSON + SVG')
                        zone_file = gr.File(label='ZIP phương án phân khu')
                        zone_report = gr.JSON(label='Trạng thái kiểm chứng')
                        def export_zoning(project, width, depth, height):
                            from app.schematic_zoning import add_two_zone_sketch, zoning_svg
                            from app.bim_transaction import canonical_checksum
                            try:
                                data = add_two_zone_sketch(project, width, depth, height)
                                target = OUTPUT / ('zoning_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
                                target.mkdir()
                                (target / 'canonical_bim_handoff.json').write_text(
                                    json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
                                (target / 'zoning_plan.svg').write_text(zoning_svg(data), encoding='utf-8')
                                archive_path = str(target) + '.zip'
                                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as archive:
                                    for path in sorted(target.iterdir()):
                                        archive.write(path, path.name)
                                from app.zoning_validation import validate_zoning
                                consistency = validate_zoning(data)
                                return archive_path, {'zones': 2, 'wall_count': 5,
                                                      'geometry_consistency': consistency,
                                                      'canonical_checksum': canonical_checksum(data),
                                                      'source': 'user_dimensions_simple_55_45_split',
                                                      'image_to_bim_ml_performed': False,
                                                      'code_compliance_verified': False,
                                                      'ifc_export_ready': False}
                            except (ValueError, OSError) as exc:
                                raise gr.Error(str(exc)) from exc
                        zone_button.click(export_zoning, inputs=[zone_project, zone_width, zone_depth, zone_height],
                                          outputs=[zone_file, zone_report])
                with gr.Tab("Nhận dạng AI"):
                    with gr.Accordion('BIMAI360 · PHÂN TÍCH ẢNH CHO PHƯƠNG ÁN BIM', open=True):
                        gr.Markdown('Quan sát ảnh, gắn đúng mã công trình và tạo JSON cho bước mô hình lớn. '
                                    'Chưa chạy VLM/segmentation nên sẽ **không tự đoán** số tầng hoặc kích thước.')
                        with gr.Row():
                            observation_image = gr.Image(type='pil', label='Ảnh công trình')
                            with gr.Column():
                                observation_project = gr.Textbox(value='office_116', label='Mã công trình')
                                from app.vi_labels import IMAGE_ROLES
                                observation_role = gr.Dropdown(
                                    choices=list(IMAGE_ROLES),
                                    value='Ảnh phối cảnh ngoại thất', label='Loại ảnh đầu vào (chọn theo nội dung thực tế)')
                                observation_button = gr.Button('PHÂN TÍCH ẢNH / XUẤT JSON', variant='primary')
                                observation_file = gr.File(label='Tải dữ liệu ảnh JSON (định dạng kết nối)')
                        observation_report = gr.JSON(label='Kết quả kiểm tra ảnh (tiếng Việt)')
                        def observe_architecture(image, project, role):
                            from app.architecture_observation import inspect_architecture
                            try:
                                from app.vi_labels import image_role_code, translate_report
                                observation = inspect_architecture(
                                    image, project, image_role_code(role))
                                output_path = OUTPUT / ('observation_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
                                output_path.write_text(json.dumps(observation, ensure_ascii=False, indent=2), encoding='utf-8')
                                return translate_report(observation), str(output_path)
                            except (OSError, ValueError) as exc:
                                raise gr.Error(str(exc)) from exc
                        observation_button.click(observe_architecture,
                                                 inputs=[observation_image, observation_project, observation_role],
                                                 outputs=[observation_report, observation_file])
                    with gr.Accordion('BIMAI360 · THỬ NGHIỆM AI NHẬN DIỆN KIẾN TRÚC (VLM)', open=False):
                        gr.Markdown('Chỉ chạy khi bạn có **checkpoint VLM tương thích lưu trên máy và GPU CUDA**. '
                                    'Đây là suy luận hình ảnh thực, không phải tạo BIM/IFC và chưa có model huấn luyện sẵn.')
                        with gr.Row():
                            vlm_image = gr.Image(type='pil', label='Ảnh phối cảnh')
                            with gr.Column():
                                vlm_project = gr.Textbox(value='office_146', label='Mã công trình')
                                vlm_model_path = gr.Textbox(label='Thư mục checkpoint VLM trên máy',
                                                             placeholder='models/architecture_vlm')
                                vlm_button = gr.Button('CHẠY VLM THẬT / XUẤT JSON')
                        vlm_report = gr.JSON(label='Quan sát và trạng thái kiểm chứng')
                        vlm_file = gr.File(label='Tải dữ liệu suy luận (JSON)')
                        def run_architecture_vlm(image, model_path, project):
                            from app.local_workspace import record_operation
                            record_operation(ROOT, 'vlm_inference', 'started')
                            from app.architecture_vlm import infer_architecture
                            try:
                                observation = infer_architecture(image, model_path, project)
                                output_path = OUTPUT / ('vlm_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
                                output_path.write_text(json.dumps(observation, ensure_ascii=False, indent=2), encoding='utf-8')
                                return observation, str(output_path)
                            except (OSError, ValueError, RuntimeError, ImportError) as exc:
                                raise gr.Error(str(exc)[:400]) from exc
                        vlm_button.click(run_architecture_vlm,
                                         inputs=[vlm_image, vlm_model_path, vlm_project],
                                         outputs=[vlm_report, vlm_file])
                        gr.Markdown('**Bước duyệt thiết kế:** chỉ khi VLM đã chạy thành công và '
                                    'bạn cung cấp kích thước thực, mới tạo BIM concept.')
                        with gr.Row():
                            approved_width = gr.Number(value=12, label='Ngang do bạn xác nhận (m)')
                            approved_depth = gr.Number(value=8, label='Sâu do bạn xác nhận (m)')
                            approved_height = gr.Number(value=3.2, label='Cao tầng do bạn xác nhận (m)')
                            approved_floors = gr.Number(value=3, precision=0, label='Số tầng xác nhận')
                        vlm_approved = gr.Checkbox(value=False, label='Tôi xác nhận kích thước và chấp thuận tạo BIM concept')
                        approve_button = gr.Button('DUYỆT VLM + XUẤT MÔ HÌNH CONCEPT', variant='secondary')
                        approval_output = gr.File(label='Canonical BIM concept đã duyệt (JSON)')
                        approval_report = gr.JSON(label='Kết quả duyệt')
                        def approve_vlm_proposal(observation, width, depth, height, floors, approved):
                            from app.architecture_evidence import approve_schematic_from_vlm
                            from app.bim_transaction import canonical_checksum
                            try:
                                model = approve_schematic_from_vlm(
                                    observation, {'width_m': width, 'depth_m': depth,
                                                  'floor_height_m': height, 'floor_count': floors,
                                                  'user_approved': approved})
                                destination = OUTPUT / ('approved_concept_' +
                                    datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
                                destination.write_text(json.dumps(model, ensure_ascii=False, indent=2),
                                                       encoding='utf-8')
                                return str(destination), {'canonical_sha256': canonical_checksum(model),
                                                          'entities': len(model['entities']),
                                                          'image_dimensions_inferred': False,
                                                          'ifc_export_ready': False}
                            except (ValueError, KeyError, TypeError, OSError) as exc:
                                raise gr.Error(str(exc)[:400]) from exc
                        approve_button.click(approve_vlm_proposal,
                                             inputs=[vlm_report, approved_width, approved_depth,
                                                     approved_height, approved_floors, vlm_approved],
                                             outputs=[approval_output, approval_report])

                    with gr.Accordion('BIMAI360 · ĐỐI CHIẾU NHIỀU GÓC NHÌN AI', open=False):
                        gr.Markdown('Đối chiếu các tệp JSON VLM đã suy luận thực cho **cùng công trình**. '
                                    'Báo xung đột số tầng / mái / mặt đứng; không tự sửa BIM khi AI bất đồng.')
                        multimodal_files = gr.File(label='Chọn nhiều JSON kết quả VLM',
                                                   file_types=['.json'], file_count='multiple')
                        compare_button = gr.Button('KIỂM TRA XUNG ĐỘT KIẾN TRÚC')
                        compare_report = gr.JSON(label='Độ nhất quán và bằng chứng từng góc nhìn')
                        def inspect_multiview(files):
                            from app.architecture_multiview import reconcile_architecture_observations
                            try:
                                if not files or len(files) > 12:
                                    raise ValueError('Chọn từ 1 đến 12 kết quả JSON')
                                observations = []
                                for file in files:
                                    path = Path(file if isinstance(file, (str, Path)) else file.name)
                                    if path.stat().st_size > 1000000:
                                        raise ValueError('Tệp JSON quá lớn')
                                    observations.append(json.loads(path.read_text(encoding='utf-8')))
                                return reconcile_architecture_observations(observations)
                            except (ValueError, KeyError, OSError, UnicodeError) as exc:
                                raise gr.Error(str(exc)[:400]) from exc
                        compare_button.click(inspect_multiview, inputs=multimodal_files,
                                             outputs=compare_report)
                        gr.Markdown('**Duyệt đề xuất đa ảnh → BIM concept:** các kích thước dưới đây do bạn nhập, '
                                    'không đoán từ ảnh; xung đột cần được bạn xác nhận rõ.')
                        with gr.Row():
                            multi_width = gr.Number(value=12, label='Ngang (m)')
                            multi_depth = gr.Number(value=8, label='Sâu (m)')
                            multi_height = gr.Number(value=3.2, label='Cao tầng (m)')
                            multi_floors = gr.Number(value=3, precision=0, label='Số tầng đã xác nhận')
                        multi_approved = gr.Checkbox(value=False, label='Tôi xác nhận kích thước thật')
                        multi_acknowledge = gr.Checkbox(value=False, label='Tôi đã xem và chấp nhận khác biệt với kết quả AI')
                        multi_export_button = gr.Button('XUẤT BIM CONCEPT TỪ BẰNG CHỨNG ĐA ẢNH')
                        multi_export_file = gr.File(label='JSON BIM concept')
                        multi_export_report = gr.JSON(label='Kiểm tra bàn giao')
                        def export_multiview_concept(files, width, depth, height, floors, approved, acknowledged):
                            from app.local_workspace import record_operation
                            record_operation(ROOT, 'concept_export', 'started')
                            from app.architecture_multiview import reconcile_architecture_observations
                            from app.multiview_bim_approval import approve_multiview_concept
                            from app.bim_transaction import canonical_checksum
                            try:
                                if not files or len(files) > 12:
                                    raise ValueError('Cần 1–12 tệp JSON VLM từ cùng công trình')
                                observations = []
                                for file in files:
                                    path = Path(file if isinstance(file, (str, Path)) else file.name)
                                    if path.stat().st_size > 1000000:
                                        raise ValueError('Tệp dữ liệu VLM quá lớn')
                                    observations.append(json.loads(path.read_text(encoding='utf-8')))
                                review = reconcile_architecture_observations(observations)
                                from app.architecture_design_review import (
                                    create_reviewed_architecture_proposal, verify_reviewed_proposal)
                                constraints = {'width_m': width, 'depth_m': depth,
                                    'floor_height_m': height, 'floor_count': floors,
                                    'user_approved': approved}
                                model, review = create_reviewed_architecture_proposal(
                                    observations, constraints, acknowledged)
                                integrity = verify_reviewed_proposal(
                                    model, observations, constraints, acknowledged)
                                output_path = OUTPUT / ('approved_multiview_' +
                                    datetime.now().strftime('%Y%m%d_%H%M%S_%f') + '.json')
                                output_path.write_text(json.dumps(model, ensure_ascii=False, indent=2),
                                                       encoding='utf-8')
                                return str(output_path), {'entities': len(model['entities']),
                                    'sha256': canonical_checksum(model),
                                    'conflicts': model['concept_source']['multiview_conflict_fields'],
                                    'dimensions_from_user': True, 'ifc_export_ready': False,
                                    'approval_replay': integrity,
                                    'ai_advisory': model['design_evidence_review']['advisory_hypotheses']}
                            except (ValueError, KeyError, TypeError, OSError, UnicodeError) as exc:
                                raise gr.Error(str(exc)[:400]) from exc
                        multi_export_button.click(export_multiview_concept,
                            inputs=[multimodal_files, multi_width, multi_depth, multi_height,
                                    multi_floors, multi_approved, multi_acknowledge],
                            outputs=[multi_export_file, multi_export_report])

                with gr.Tab("Ảnh nâng cao"):
                    gr.Markdown('**Pipeline thật khi có checkpoint**: SDXL hoặc SD1.5; ControlNet Canny giữ cạnh hình; x4 diffusion upscale. Cần NVIDIA GPU và tải model riêng. Khả năng chạy phụ thuộc VRAM; không có bảo đảm chất lượng kỹ thuật/BIM.')
                    with gr.Row():
                        with gr.Column():
                            adv_input = gr.Image(label='Ảnh gốc',type='pil')
                            adv_prompt = gr.Textbox(label='Prompt kiến trúc',value=DEFAULT_PROMPT,lines=3)
                            adv_model = gr.Radio(['SD 1.5','SDXL 1.0'],value='SD 1.5',label='Model nền')
                            adv_control = gr.Checkbox(label='ControlNet Canny: giữ biên hình khối',value=False)
                            adv_strength = gr.Slider(0.1,0.9,0.45,step=0.05,label='Mức thay đổi ảnh (strength)')
                            adv_control_strength = gr.Slider(0,2,0.9,step=0.1,label='Độ mạnh ControlNet')
                            adv_steps = gr.Slider(10,60,30,step=1,label='Số bước')
                            adv_cfg = gr.Slider(1,15,6.5,step=0.5,label='CFG')
                            adv_seed = gr.Number(value=42,precision=0,label='Seed')
                            adv_low = gr.Checkbox(value=True,label='Tiết kiệm VRAM bằng CPU offload')
                            adv_button = gr.Button('SINH ẢNH AI NÂNG CAO',variant='primary')
                        with gr.Column():
                            adv_output = gr.Image(label='Kết quả',type='pil')
                            adv_metadata = gr.JSON(label='Thông số và trạng thái thực thi')
                            upscale_button = gr.Button('AI SUPER-RESOLUTION x4 (nguồn: ảnh kết quả)')
                            upscale_output = gr.Image(label='Kết quả AI x4',type='pil')
                            upscale_metadata = gr.JSON(label='Thông tin upscale')
                    def run_advanced(image, prompt, model, control, strength, steps, cfg, control_strength, seed, low):
                        from app.advanced import generate_advanced
                        try:
                            return generate_advanced(image,prompt,model,control,strength,steps,cfg,control_strength,int(seed),low)
                        except Exception as exc:
                            raise gr.Error(f'Pipeline nâng cao chưa chạy thành công: {type(exc).__name__}: {exc}') from exc
                    def run_upscale(image, prompt, seed, low):
                        from app.advanced import upscale_ai
                        try:
                            return upscale_ai(image,prompt,int(seed),low)
                        except Exception as exc:
                            raise gr.Error(f'AI upscale chưa chạy thành công: {type(exc).__name__}: {exc}') from exc
                    gr.Markdown('**Sinh ảnh nâng cao cần GPU NVIDIA CUDA.** Nếu máy không nhận CUDA, nút sẽ bị khóa. Muốn thử trên CPU, dùng mục Thiết kế và sinh ảnh.')
                    def check_advanced_gpu():
                        try:
                            import torch
                            available = torch.cuda.is_available()
                        except (ImportError, RuntimeError):
                            available = False
                        return (gr.update(interactive=available),
                                gr.update(interactive=available))
                    ui.load(check_advanced_gpu, outputs=[adv_button, upscale_button])
                    adv_button.click(run_advanced,inputs=[adv_input,adv_prompt,adv_model,adv_control,adv_strength,adv_steps,adv_cfg,adv_control_strength,adv_seed,adv_low],outputs=[adv_output,adv_metadata],concurrency_limit=1)
                    upscale_button.click(run_upscale,inputs=[adv_output,adv_prompt,adv_seed,adv_low],outputs=[upscale_output,upscale_metadata],concurrency_limit=1)
                with gr.Accordion('V84 · GIỮ CẤU TRÚC KIẾN TRÚC / EDGE CONTROL', open=False):
                    gr.Markdown('Tạo ảnh biên và gói dữ liệu tham chiếu cùng seed. '
                                '**Đây chưa phải ControlNet đã chạy; không tự khẳng định hình học được bảo toàn.**')
                    with gr.Row():
                        structure_input = gr.Image(label='Ảnh kiến trúc gốc', type='pil')
                        structure_output = gr.Image(label='Ảnh cạnh kiến trúc', type='pil', interactive=False)
                    with gr.Row():
                        edge_threshold = gr.Slider(10, 240, value=95, step=5, label='Ngưỡng phát hiện cạnh')
                        structure_seed = gr.Number(value=42, precision=0, label='Seed đối chiếu')
                    gr.Markdown('**Bước 1:** Tải ảnh kiến trúc vào ô bên trái. **Bước 2:** Chọn ngưỡng rồi tạo ảnh biên. **Bước 3:** Nếu cần, xuất gói dữ liệu. Chức năng này tạo ảnh biên trên CPU, không chạy AI ControlNet.')
                    structure_preview = gr.Button('TẠO ẢNH BIÊN THAM CHIẾU', variant='primary', interactive=False)
                    structure_export = gr.Button('XUẤT ZIP ẢNH GỐC VÀ ẢNH BIÊN', interactive=False)
                    structure_file = gr.File(label='Tải gói ZIP ảnh biên và thông số')
                    structure_status = gr.Markdown('**Chưa có ảnh:** Hãy tải ảnh vào ô bên trái để bắt đầu.')
                    def image_input_state(image):
                        has_image = image is not None
                        message = ('**Đã nhận ảnh.** Chọn ngưỡng cạnh rồi bấm **Tạo ảnh biên tham chiếu**.'
                                   if has_image else '**Chưa có ảnh:** Hãy tải ảnh vào ô bên trái để bắt đầu.')
                        return (gr.update(interactive=has_image),
                                gr.update(interactive=has_image), message, None, None)
                    structure_input.change(
                        image_input_state, inputs=structure_input,
                        outputs=[structure_preview, structure_export, structure_status,
                                 structure_output, structure_file])
                    def edge_preview(image, threshold):
                        from app.structure_guidance import structure_reference
                        if image is None:
                            return None, '**Chưa có ảnh:** Vui lòng tải ảnh kiến trúc trước.'
                        try:
                            output = structure_reference(image, threshold)
                            return output, '**Đã tạo ảnh biên.** Bạn có thể tải gói ZIP để dùng làm tham chiếu.'
                        except ValueError as exc:
                            return None, '**Không tạo được ảnh biên:** ' + str(exc)
                    structure_preview.click(
                        edge_preview, inputs=[structure_input, edge_threshold],
                        outputs=[structure_output, structure_status])
                    def save_structure(image, threshold, seed):
                        from app.structure_guidance import export_structure_package
                        if image is None:
                            return None, '**Chưa có ảnh:** Vui lòng tải ảnh kiến trúc trước.'
                        folder = OUTPUT / ('control_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
                        try:
                            _, report = export_structure_package(image, folder, threshold, seed)
                            archive = str(folder) + '.zip'
                            with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output_zip:
                                for path in sorted(folder.iterdir()):
                                    output_zip.write(path, path.name)
                            return archive, '**Đã xuất ZIP ảnh biên** theo ngưỡng ' + str(report['threshold']) + '.'
                        except (ValueError, OSError) as exc:
                            return None, '**Không xuất được ZIP:** ' + str(exc)
                    structure_export.click(
                        save_structure, inputs=[structure_input, edge_threshold, structure_seed],
                        outputs=[structure_file, structure_status])
        with gr.Tab("02 · KIỂM TRA"):
            with gr.Tabs():
                with gr.Tab("Ảnh đầu vào"):
                    with gr.Accordion('V86 · KIỂM TRA ẢNH TRƯỚC KHI SINH / CPU GUARD', open=True):
                        gr.Markdown('**Bước kiểm soát chất lượng ảnh:** kiểm tra cạnh, tỷ lệ khung và cảnh báo board/collage. '
                                    'Kết quả là quy tắc kỹ thuật, không phải AI đã hiểu BIM.')
                        preflight_image = gr.Image(label='Chọn ảnh tham chiếu để kiểm tra', type='pil')
                        preflight_button = gr.Button('KIỂM TRA ẢNH – PHÁT HIỆN NGUY CƠ NHIỄU', variant='primary')
                        preflight_result = gr.JSON(label='Báo cáo ảnh')
                        def inspect_architecture_reference(image):
                            from app.architecture_preflight import inspect_reference
                            return inspect_reference(image)
                        preflight_button.click(inspect_architecture_reference,
                                               inputs=preflight_image, outputs=preflight_result)
                    with gr.Accordion('V85 · SO SÁNH CHẤT LƯỢNG ẢNH TRƯỚC / SAU', open=False):
                        gr.Markdown('So sánh hai ảnh và xuất kết quả kèm checksum. '
                                    '**Chênh lệch pixel không phải điểm đẹp, độ chính xác BIM hoặc bằng chứng LoRA tốt hơn.**')
                        with gr.Row():
                            before_img = gr.Image(label='Ảnh tham chiếu', type='pil')
                            after_img = gr.Image(label='Ảnh kết quả', type='pil')
                        comparison_seed = gr.Number(value=42, precision=0, label='Seed sử dụng (nhập theo lượt tạo)')
                        compare_button = gr.Button('SO SÁNH VÀ XUẤT BÁO CÁO', variant='primary')
                        compare_preview = gr.Image(label='Ảnh trước / sau', interactive=False)
                        compare_report = gr.JSON(label='Độ lệch pixel/cạnh và giới hạn đánh giá')
                        compare_file = gr.File(label='ZIP kết quả QA')
                        def compare_and_export(reference, result, seed):
                            from app.architecture_quality_compare import export_comparison
                            folder = OUTPUT / ('compare_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
                            try:
                                preview, report = export_comparison(reference, result, folder, seed)
                                archive = str(folder) + '.zip'
                                with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as out:
                                    for item in sorted(folder.iterdir()):
                                        out.write(item, item.name)
                                return preview, report, archive
                            except (ValueError, OSError) as exc:
                                raise gr.Error(str(exc)) from exc
                        compare_button.click(compare_and_export,
                                             inputs=[before_img, after_img, comparison_seed],
                                             outputs=[compare_preview, compare_report, compare_file])
                        gr.Markdown('**Đây là chỉ số chẩn đoán tự động, không phải điểm đẹp hoặc xác minh thiết kế.** Giúp phát hiện ảnh quá tối, cháy sáng hay độ phân giải thấp.')
                        inspect_image = gr.Image(label='Ảnh cần kiểm tra', type='pil', sources=['upload'])
                        inspect_button = gr.Button('Phân tích ảnh', variant='primary')
                        inspect_report = gr.JSON(label='Chỉ số và cảnh báo')
                        def inspect(image):
                            if image is None:
                                return {'error': 'Chưa tải ảnh'}
                            metrics = image_diagnostics(image)
                            return {'metrics':metrics,'review_flags':diagnostic_notes(metrics),
                                    'disclaimer':'Không đánh giá độ đẹp, tính chính xác BIM hay độ giống ảnh gốc'}
                        inspect_button.click(inspect,inputs=inspect_image,outputs=inspect_report)
                        gr.Markdown('Khi sinh ảnh, mỗi kết quả được lưu chỉ số vào `generation.json` trong ZIP kết quả để đối chiếu giữa các lần chạy.')
                with gr.Tab("Mô hình BIM"):
                    with gr.Accordion('BIMAI360 · KIỂM TRA FILE BÀN GIAO BIM', open=False):
                        gr.Markdown('Nạp **canonical_bim_handoff.json** để kiểm tra ID, tầng, host, '
                                    'tọa độ và ràng buộc 2D/3D. Kiểm tra dữ liệu, không biến ảnh thành IFC.')
                        bim_audit_file = gr.File(label='Chọn canonical_bim_handoff.json',
                                                 file_types=['.json'], file_count='single')
                        bim_audit_button = gr.Button('KIỂM TRA TÍNH TOÀN VẸN BIM', variant='primary')
                        bim_audit_report = gr.JSON(label='Báo cáo kiểm tra BIM')
                        def inspect_bim_handoff(upload):
                            from app.bim_transaction import validate_document, canonical_checksum
                            if upload is None:
                                return {'valid': False, 'reason': 'Chưa nạp JSON'}
                            try:
                                source_path = Path(upload if isinstance(upload, (str, Path)) else upload.name)
                                if source_path.stat().st_size > 5 * 1024 * 1024:
                                    raise ValueError('JSON vượt 5 MB')
                                record = json.loads(source_path.read_text(encoding='utf-8'))
                                canonical = validate_document(record)
                                return {'valid': True, 'entities': len(canonical['entities']),
                                        'levels': len(canonical['levels']),
                                        'sha256': canonical_checksum(canonical),
                                        'ifc_export_ready': False,
                                        'message': 'Dữ liệu hợp lệ theo hợp đồng, không phải chứng nhận IFC.'}
                            except (ValueError, TypeError, OSError, UnicodeError, KeyError) as exc:
                                return {'valid': False, 'reason': str(exc)[:250]}
                        bim_audit_button.click(inspect_bim_handoff, inputs=bim_audit_file,
                                               outputs=bim_audit_report)
                        gr.Markdown('**Có sự đồng ý của người dùng:** phản hồi được ghi chờ duyệt; không tự đưa ảnh xấu/ảnh sai vào huấn luyện. Kiểm BIM chỉ kiểm tra subset hình học có tọa độ mét, không xác nhận thiết kế kỹ thuật.')
                        with gr.Row():
                            with gr.Column():
                                fb_project = gr.Textbox(label='Mã công trình', placeholder='office_A01')
                                fb_hash = gr.Textbox(label='SHA256 ảnh đầu ra (64 ký tự hex)')
                                fb_rating = gr.Slider(1, 5, value=3, step=1, label='Chấm điểm 1–5')
                                fb_comment = gr.Textbox(label='Góp ý / lỗi hình học', lines=3)
                                fb_consent = gr.Checkbox(label='Đồng ý lưu phản hồi để con người xem xét', value=False)
                                fb_submit = gr.Button('GHI NHẬN PHẢN HỒI')
                                fb_result = gr.JSON(label='Trạng thái đánh giá')
                                def collect_feedback(project, image_hash, rating, comment, consent):
                                    from learning.core import append_feedback
                                    try:
                                        return append_feedback(ROOT/'feedback'/'review_queue.jsonl', {'project_id': project, 'output_sha256':image_hash, 'rating':int(rating), 'comment':comment, 'consent':consent})
                                    except ValueError as exc:
                                        return {'error':str(exc)}
                                fb_submit.click(collect_feedback, inputs=[fb_project, fb_hash, fb_rating, fb_comment, fb_consent], outputs=fb_result)
                            with gr.Column():
                                bim_json = gr.File(label='Tệp canonical BIM JSON', file_types=['.json'])
                                bim_button = gr.Button('KIỂM TRA HÌNH HỌC BIM')
                                bim_result = gr.JSON(label='Các lỗi nhận diện')
                                def check_bim_file(path):
                                    from learning.core import validate_bim
                                    if not path:
                                        return {'error':'Chưa có file BIM JSON'}
                                    try:
                                        return validate_bim(json.loads(Path(path).read_text(encoding='utf-8')))
                                    except (ValueError,OSError) as exc:
                                        return {'error':str(exc)}
                                bim_button.click(check_bim_file, inputs=bim_json, outputs=bim_result)
                with gr.Tab("Chất lượng và giới hạn"):
                    gr.Markdown("""### Những gì ứng dụng thực sự làm
                    oncept theo ảnh tham chiếu bằng mô hình SD1.5 image-to-image.
                    ảnh cùng seed, mô tả, thông số, nguồn và trạng thái LoRA để tái lập.
                     độ sáng, tỷ lệ gần đen/trắng, độ tương phản và độ phân giải cho từng ảnh; chỉ là chẩn đoán, không phải AI chấm đẹp.
                    bằng Lanczos và làm nét truyền thống; **không** tăng chi tiết thực bằng AI super-resolution.
                     hoặc kiểm chứng mô hình BIM, kích thước kỹ thuật, mặt bằng hay số tầng.
                    p phụ thuộc ảnh huấn luyện, caption, GPU, mô hình nền và cách kiểm định; tăng steps không bảo đảm đẹp hơn.
                    bố LoRA đã huấn luyện nếu có checkpoint và hash khớp.""")

        with gr.Tab("03 · BÀN GIAO"):
            with gr.Tabs():
                with gr.Tab("Trung tâm xuất file"):
                    gr.Markdown('### Trung tâm xuất và nhận dữ liệu\nTệp đã tạo nằm trong thư mục **output/**; nút này chỉ hiển thị tệp sẵn có, không tạo kết quả giả.')
                    export_refresh = gr.Button('LÀM MỚI DANH SÁCH KẾT QUẢ')
                    export_items = gr.Dropdown(label='Tệp kết quả đã tạo', choices=[], interactive=True)
                    export_button = gr.Button('CHỌN TỆP ĐỂ TẢI')
                    export_file = gr.File(label='TẢI TỆP', interactive=False)
                    def list_existing_exports():
                        extensions = {'.zip', '.json', '.glb', '.dxf', '.svg', '.png', '.csv', '.jpg'}
                        candidates = sorted((p for p in OUTPUT.rglob('*')
                            if p.is_file() and p.suffix.lower() in extensions
                            and len(p.relative_to(OUTPUT).parts) <= 4),
                            key=lambda p: p.stat().st_mtime, reverse=True)[:100]
                        return gr.update(choices=[p.relative_to(OUTPUT).as_posix() for p in candidates], value=None)
                    def choose_existing_export(relative):
                        from app.local_workspace import record_operation
                        record_operation(ROOT, 'export_file', 'started')
                        if not relative:
                            raise gr.Error('Hãy chọn một tệp trước khi tải')
                        filepath = (OUTPUT / relative).resolve()
                        if OUTPUT.resolve() not in filepath.parents or not filepath.is_file():
                            raise gr.Error('Đường dẫn xuất không hợp lệ')
                        record_operation(ROOT, 'export_file', 'completed')
                        return str(filepath)
                    export_refresh.click(list_existing_exports, outputs=export_items)
                    export_button.click(choose_existing_export, inputs=export_items, outputs=export_file)


                with gr.Tab("Chuẩn bị bàn giao BIM"):
                    with gr.Accordion('V83 · CROP BOARD / CHUẨN PROMPT / BÀN GIAO BIM (một màn hình)', open=False):
                        gr.Markdown('**Tách ảnh board theo lưới do bạn chọn, xem trước, xuất ảnh tham chiếu và JSON cho BIM.** '
                                    'Không tự xóa logo/chữ, không đoán kích thước thực hoặc xuất IFC giả.')
                        with gr.Row():
                            with gr.Column():
                                crop_input = gr.Image(type='pil', label='Chọn ảnh board cần tách')
                                crop_rows = gr.Slider(1, 8, value=2, step=1, label='Số hàng trên board')
                                crop_cols = gr.Slider(1, 8, value=3, step=1, label='Số cột trên board')
                                crop_button = gr.Button('TÁCH ẢNH VÀ XEM TRƯỚC', variant='primary')
                                crop_result = gr.Gallery(label='Các ảnh con, cần chọn và kiểm tra', columns=3, height=290)
                            with gr.Column():
                                handoff_img = gr.Image(type='pil', label='Chọn 1 ảnh sạch để bàn giao')
                                handoff_project = gr.Textbox(value='office_demo_83', label='Mã công trình')
                                handoff_prompt = gr.Textbox(value='Contemporary office building, coherent facade, daylight',
                                                            label='Prompt đã dùng')
                                handoff_seed = gr.Number(value=42, precision=0, label='Seed cố định')
                                handoff_button = gr.Button('XUẤT THAM CHIẾU CHO CAD/BIM')
                                handoff_file = gr.File(label='ZIP tham chiếu + JSON')
                                handoff_report = gr.JSON(label='Trạng thái bàn giao')
                        with gr.Row():
                            building_type = gr.Dropdown(['office building', 'residential building', 'school building'],
                                                        value='office building', label='Loại công trình')
                            floors = gr.Slider(1, 30, value=5, step=1, label='Số tầng mô tả')
                            facade = gr.Dropdown(['curtain wall facade', 'rendered masonry facade', 'mixed glazing facade'],
                                                 value='curtain wall facade', label='Mặt đứng')
                            roof = gr.Dropdown(['flat roof', 'pitched roof'], value='flat roof', label='Mái')
                        arch_prompt_button = gr.Button('TẠO PROMPT KIẾN TRÚC ĐỒNG NHẤT')
                        arch_prompt_result = gr.Textbox(label='Prompt kiến trúc đề xuất', lines=3)
                        def crop_board(image, rows, cols):
                            from app.architecture_crop import propose_crops
                            try:
                                return [(item['image'], f"Hàng {item['row']} · Cột {item['column']} · cần duyệt")
                                        for item in propose_crops(image, rows, cols)]
                            except (ValueError, OSError) as exc:
                                raise gr.Error(str(exc)) from exc
                        crop_button.click(crop_board, inputs=[crop_input, crop_rows, crop_cols], outputs=crop_result)
                        def prompt_architecture(kind, count, face, roof_type):
                            from app.bim_handoff import build_prompt
                            return build_prompt(kind, count, face, roof_type, 'corner perspective', 'natural daylight',
                                                'concrete, glass and metal')
                        arch_prompt_button.click(prompt_architecture, inputs=[building_type, floors, facade, roof],
                                                 outputs=arch_prompt_result)
                        def handoff_export(image, project, prompt, seed):
                            import tempfile
                            from app.bim_handoff import export_handoff
                            if image is None:
                                raise gr.Error('Chọn ảnh sạch trước khi bàn giao')
                            export_dir = OUTPUT / ('handoff_' + datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
                            try:
                                report = export_handoff(image, export_dir, project_id=project, prompt=prompt, seed=int(seed))
                                archive = str(export_dir) + '.zip'
                                with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output_zip:
                                    for path in sorted(export_dir.iterdir()):
                                        if path.is_file():
                                            output_zip.write(path, path.name)
                                return archive, report
                            except (ValueError, OSError) as exc:
                                raise gr.Error(str(exc)) from exc
                        handoff_button.click(handoff_export, inputs=[handoff_img, handoff_project, handoff_prompt, handoff_seed],
                                             outputs=[handoff_file, handoff_report])
        with gr.Tab("04 · DỮ LIỆU"):
            with gr.Tabs():
                with gr.Tab("Nạp và xem ảnh"):
                    with gr.Accordion('NẠP ẢNH HUẤN LUYỆN – IMPORT DATASET (chỉ thao tác tại đây)', open=True):
                        gr.Markdown('**1. Chọn ảnh → 2. Nhập mã công trình và mô tả → 3. Nhấn LƯU ẢNH → 4. XEM ẢNH.** '
                                    'Ảnh được lưu bên cạnh EXE; không tự huấn luyện, không yêu cầu tìm thư mục Windows.')
                        with gr.Row():
                            with gr.Column(scale=1):
                                dataset_zip = gr.File(label='NẠP GÓI ZIP DỮ LIỆU KIẾN TRÚC (tối đa 500 ảnh/lượt)',
                                                      file_count='single', file_types=['.zip'])
                                dataset_upload = gr.File(label='1 · NẠP NHIỀU ẢNH (kéo thả hoặc bấm chọn)',
                                                         file_count='multiple', file_types=['image'])
                                dataset_project = gr.Textbox(label='2 · Mã công trình', value='office_demo_01')
                                dataset_caption = gr.Textbox(label='3 · Nhãn / mô tả của nhóm ảnh',
                                    value='Contemporary office building, architectural facade, realistic proportions',
                                    lines=2)
                                with gr.Row():
                                    dataset_save = gr.Button('LƯU ẢNH VÀ NHÃN NHÁP', variant='primary')
                                    dataset_view = gr.Button('XEM ẢNH ĐÃ NẠP')
                                    dataset_view_all = gr.Button('XEM TẤT CẢ DATASET CÓ SẴN')
                                dataset_import_zip = gr.Button('NẠP ẢNH TỪ ZIP VÀO DATASET')
                                dataset_v81_bundle = gr.Button('NẠP ZIP TỰ ĐỘNG – KHÔNG CẦN TÌM MANIFEST', variant='primary')
                                dataset_status = gr.JSON(label='Trạng thái nạp dữ liệu')
                            with gr.Column(scale=2):
                                dataset_gallery = gr.Gallery(label='THƯ VIỆN ẢNH V81 (xem tất cả bằng một nút)',
                                                             columns=4, height=320, object_fit='contain')
                        def save_dataset(files, project, caption):
                            from app.local_workspace import record_operation
                            record_operation(ROOT, 'dataset_import', 'started')
                            from app.dataset_import import import_images, preview_project
                            try:
                                result = import_images(ROOT, files, project, caption)
                                gallery, summary = preview_project(ROOT, project)
                                result['project_summary'] = summary
                                record_operation(ROOT, 'dataset_import', 'completed')
                                return result, gallery
                            except (ValueError, OSError) as exc:
                                record_operation(ROOT, 'dataset_import', 'failed')
                                return {'error': str(exc), 'training_started': False}, []
                        def show_dataset(project):
                            from app.dataset_import import preview_project
                            return preview_project(ROOT, project)
                        dataset_save.click(save_dataset,
                                           inputs=[dataset_upload, dataset_project, dataset_caption],
                                           outputs=[dataset_status, dataset_gallery])
                        def save_zip_dataset(archive, project, caption):
                            from app.dataset_zip_import import import_zip_archive
                            from app.dataset_import import preview_project
                            if not archive:
                                return {'error': 'Hãy chọn file ZIP trước'}, []
                            try:
                                result = import_zip_archive(ROOT, archive, project, caption)
                                gallery, summary = preview_project(ROOT, project)
                                result['project_summary'] = summary
                                return result, gallery
                            except (ValueError, OSError, RuntimeError) as exc:
                                return {'error': str(exc), 'training_started': False}, []
                        dataset_import_zip.click(save_zip_dataset,
                                                 inputs=[dataset_zip, dataset_project, dataset_caption],
                                                 outputs=[dataset_status, dataset_gallery])
                        def import_smart_archive(archive, project, caption):
                            from app.dataset_auto_import import import_any_zip
                            from app.dataset_import import preview_all_projects
                            if not archive:
                                return {'error': 'Chọn file ZIP có ảnh trước khi nhấn Nạp'}, []
                            try:
                                result = import_any_zip(ROOT, archive, project, caption)
                                gallery, overview = preview_all_projects(ROOT)
                                result['overview'] = overview
                                return result, gallery
                            except (ValueError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
                                return {
                                    'error': str(exc),
                                    'suggestion': 'Chọn đúng ZIP ảnh; RAR/SVG/DXF không hỗ trợ nạp như ảnh. Không cần mở dataset trong Windows.',
                                    'training_started': False,
                                }, []
                        dataset_v81_bundle.click(import_smart_archive,
                                                 inputs=[dataset_zip, dataset_project, dataset_caption],
                                                 outputs=[dataset_status, dataset_gallery])

                        dataset_view.click(show_dataset, inputs=dataset_project,
                                           outputs=[dataset_gallery, dataset_status])
                        def show_all_datasets():
                            from app.dataset_import import preview_all_projects
                            return preview_all_projects(ROOT)
                        dataset_view_all.click(show_all_datasets,
                                               outputs=[dataset_gallery, dataset_status])
                        gr.Markdown('**Lưu ý:** Đây là bước thu thập và gán nhãn nháp. Để LoRA học thật cần duyệt dữ liệu, '
                                    'chia tập theo công trình và chạy bộ huấn luyện trên NVIDIA CUDA. '
                                    'Không tự động đưa ảnh mới vào model.')
                with gr.Tab("Kiểm tra dữ liệu"):
                    gr.Markdown('Phát hiện ảnh trùng chính xác và ảnh gần trùng (perceptual hash), caption đơn điệu và cảnh báo nguy cơ overfit. Báo cáo dữ liệu không tự chứng minh mô hình tổng quát hóa.')
                    audit_button = gr.Button('KIỂM TRA DATASET ĐÃ CHUẨN BỊ')
                    audit_report = gr.JSON(label='Audit dataset/ prepared')
                    def audit_data():
                        from tools.audit_training import audit
                        return audit(ROOT/'dataset'/'prepared')
                    audit_button.click(audit_data,outputs=audit_report)
        with gr.Tab("05 · ĐÀO TẠO"):
            with gr.Tabs():
                with gr.Tab("Checkpoint LoRA"):
                    with gr.Accordion('V83 · KIỂM TRA LO RA ĐÃ HUẤN LUYỆN THẬT', open=False):
                        gr.Markdown('**Nạp ảnh không có nghĩa mô hình đã học.** Chỉ công nhận checkpoint có trạng thái '
                                    'SUCCEEDED và SHA256/size đúng. LoRA SD1.5 hiện phải chạy huấn luyện bằng '
                                    'môi trường NVIDIA CUDA riêng; CPU Portable không thực hiện bước này.')
                        lora_check_button = gr.Button('KIỂM TRA CHECKPOINT LO RA VÀ BẰNG CHỨNG')
                        lora_check_report = gr.JSON(label='Kết quả checkpoint thực tế')
                        def check_train_evidence():
                            from app.lora_evidence import training_evidence
                            return training_evidence(ROOT)
                        lora_check_button.click(check_train_evidence, outputs=lora_check_report)
                with gr.Tab("Môi trường AI"):
                    info=gr.Textbox(value=machine_info,label='Cấu hình máy',interactive=False)
                    check=gr.Button('KIỂM TRA MÔI TRƯỜNG / LoRA')
                    report=gr.Textbox(label='Báo cáo tiền kiểm',lines=5,interactive=False)
                    check.click(preflight,outputs=report)
                    gr.Markdown('Kiểm tra GPU, CUDA, thư viện và LoRA trước khi huấn luyện/sinh ảnh.')
                    gr.Button('Kiểm tra lại môi trường').click(preflight,outputs=report)
                    gr.Markdown('### V79 · Khả năng chạy trên CPU và model offline')
                    readiness = gr.JSON(label='Kiểm tra mô hình AI, bộ tinh chỉnh và cấu hình đề xuất')
                    def inspect_readiness():
                        from app.cpu_readiness import inspect_local_assets
                        try:
                            import torch
                            has_cuda = torch.cuda.is_available()
                        except (ImportError, RuntimeError):
                            has_cuda = False
                        return inspect_local_assets(ROOT, cuda_available=has_cuda)
                    gr.Button('Kiểm tra tài nguyên cục bộ (không tải model)').click(
                        inspect_readiness, outputs=readiness)
                    gr.Markdown('Nếu chỉ có CPU: ưu tiên preset Xem nhanh, 15 bước, 1 ảnh; thời gian chạy phụ thuộc CPU. '
                                'Model hợp lệ trong danh mục chưa chứng minh sinh ảnh thành công.')
                    gr.Markdown('**LoRA:** chuẩn bị dữ liệu bằng `KIEM_TRA_DU_LIEU_WINDOWS.bat`, sau đó chạy `TRAIN_LORA_WINDOWS.bat` trên máy build có GPU NVIDIA đủ VRAM. Kết quả huấn luyện được xác minh SHA256.')
        with gr.Tab("06 · TÀI KHOẢN"):
            with gr.Tabs():
                with gr.Tab("Truy cập cục bộ"):
                    gr.Markdown('### Truy cập nhanh trên máy này\n**Chế độ cục bộ** không cần mật khẩu; đây không phải tài khoản máy chủ. Không lưu mật khẩu trong EXE.')
                    profile_name = gr.Textbox(value='Người dùng cục bộ', label='Tên hiển thị')
                    profile_open = gr.Button('MỞ WORKSPACE TRÊN MÁY NÀY', variant='primary')
                    profile_status = gr.JSON(label='Phiên cục bộ')
                    def open_local_workspace(name):
                        from app.local_workspace import save_local_profile
                        return save_local_profile(ROOT, name)
                    profile_open.click(open_local_workspace, inputs=profile_name, outputs=profile_status)


                with gr.Tab("Nhật ký hoạt động"):
                    gr.Markdown('### Nhật ký trực tiếp · không chứa mật khẩu')
                    refresh_logs = gr.Button('LÀM MỚI LOG')
                    runtime_logs = gr.Textbox(label='Nhật ký gần nhất', lines=14, interactive=False)
                    def load_runtime_logs():
                        from app.local_workspace import read_runtime_log
                        return read_runtime_log(ROOT)
                    refresh_logs.click(load_runtime_logs, outputs=runtime_logs)
                    gr.Markdown('**Khi mọi tab báo Connection errored out:** đóng EXE, mở Command Prompt trong thư mục Portable và chạy `BIMAI360.exe --diagnostics`. ZIP sẽ nằm trong thư mục logs, không cần mở giao diện.')
                    diagnostic_button = gr.Button('XUẤT GÓI CHẨN ĐOÁN ZIP')
                    diagnostic_output = gr.File(label='ZIP chẩn đoán để gửi hỗ trợ')
                    def export_diagnostics():
                        from app.diagnostic_bundle import build_diagnostic_zip
                        return build_diagnostic_zip(ROOT)
                    diagnostic_button.click(
                        export_diagnostics, outputs=diagnostic_output,
                        api_name='xuat_chan_doan',
                    )
                    gr.Markdown('Nhấn LÀM MỚI LOG khi cần; không tự gửi yêu cầu định kỳ gây nghẽn hàng đợi.')



if __name__ == '__main__':
    gradio_temp = ROOT / 'output' / 'gradio_temp'
    gradio_temp.mkdir(parents=True, exist_ok=True)
    os.environ['GRADIO_TEMP_DIR'] = str(gradio_temp)
    ui.queue(default_concurrency_limit=2,max_size=32).launch(
      server_name='127.0.0.1',server_port=7861,inbrowser=True,share=False,
      allowed_paths=[str(OUTPUT), str(ROOT / 'logs'), str(gradio_temp)])
