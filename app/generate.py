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

ROOT = Path(os.environ['TBT360_HOME']).resolve() if os.environ.get('TBT360_HOME') else Path(__file__).resolve().parents[1]
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
    import torch
    from diffusers import AutoPipelineForImage2Image
    if memory_mode in PIPELINES:
        return PIPELINES[memory_mode]
    dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    pipe = AutoPipelineForImage2Image.from_pretrained(
        MODEL_ID, torch_dtype=dtype, use_safetensors=True, cache_dir=str(CACHE),
        local_files_only=os.environ.get('TBT360_OFFLINE') == '1')
    if torch.cuda.is_available():
        if memory_mode == 'Tiết kiệm VRAM tối đa':
            pipe.enable_sequential_cpu_offload()
            placement = 'CUDA sequential CPU offload (rất chậm nhưng tiết kiệm VRAM)'
        else:
            pipe.to('cuda')
            placement = 'CUDA trực tiếp (nhanh hơn, dùng nhiều VRAM hơn)'
    else:
        pipe.to('cpu')
        placement = 'CPU (có thể rất chậm)'
    if memory_mode == 'Tiết kiệm VRAM tối đa' or not torch.cuda.is_available():
        pipe.enable_attention_slicing()
    try:
        pipe.enable_vae_slicing()
    except (AttributeError, ValueError):
        pass
    PIPELINES[memory_mode] = (pipe, placement)
    return PIPELINES[memory_mode]


def installed_loras():
    choices = ['Không dùng LoRA']
    for path in sorted(LORA_DIR.iterdir()):
        if not path.is_dir():
            continue
        weights = path / 'pytorch_lora_weights.safetensors'
        status = path / 'training_status.json'
        if not weights.is_file() or not status.is_file():
            continue
        try:
            record = json.loads(status.read_text(encoding='utf-8'))
            if record.get('status') != 'SUCCEEDED':
                continue
            if weights.stat().st_size != record.get('weights_bytes'):
                continue
            digest = hashlib.sha256(weights.read_bytes()).hexdigest()
            if digest != record.get('weights_sha256'):
                continue
            choices.append(path.name)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
    return choices


def select_lora(pipe, memory_mode, adapter_name):
    current = ACTIVE_LORA.get(memory_mode, 'Không dùng LoRA')
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
    ACTIVE_LORA[memory_mode] = adapter_name


def create(source_image, brief, preserve, steps, count, seed, aspect, fit_mode, memory_mode, lora_name, style, guidance, scale, sharpness, progress=gr.Progress()):
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
                'images':[], 'quality_method':'diagnostics only, no learned aesthetics or BIM validation'}
            for index in range(int(count)):
                progress(index / int(count), desc=f'Đang sinh ảnh {index+1}/{int(count)}')
                current_seed=seed0+index
                generator=torch.Generator(device='cpu').manual_seed(current_seed)
                result=pipe(prompt=prompt,negative_prompt=NEGATIVE,image=source,
                    strength=1-float(preserve),guidance_scale=float(guidance),
                    num_inference_steps=int(steps),generator=generator).images[0]
                fname=f'architecture_option_{index+1:02d}_seed_{current_seed}.png'
                result = postprocess_image(result, scale, sharpness)
                result.save(run_dir/fname, optimize=True)
                generated.append((result,f'Phương án {index+1} · seed {current_seed}'))
                diag = image_diagnostics(result)
                manifest['images'].append({'file':fname,'seed':current_seed,
                    'diagnostics':diag,'review_flags':diagnostic_notes(diag)})
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
            raise gr.Error('Không đủ VRAM. Hãy chọn Tiết kiệm VRAM tối đa, 1 phương án, 10–15 bước, và đóng các ứng dụng GPU khác.') from exc
        except Exception as exc:
            raise gr.Error(f'Không tạo được ảnh: {type(exc).__name__}: {exc}. Xem README_RUN.md để xử lý.') from exc


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


with gr.Blocks(title='TBT360 AI Studio V81 · Training & Architecture') as ui:
    gr.Markdown('# TBT360 AI V81 · Thiết kế & Huấn luyện trên một màn hình')
    gr.Markdown('**Ảnh tham chiếu → nhiều phương án concept; ưu tiên nhất quán, kiểm soát VRAM và xuất kết quả có thể tái lập.** '
      'Không đăng nhập. Không cần BIM. Lần đầu cần tải mô hình qua Internet. '
      '**LoRA chỉ được coi là đã huấn luyện riêng sau khi chạy TRAIN_LORA_WINDOWS.bat thành công.**')
    with gr.Accordion('NẠP ẢNH HUẤN LUYỆN – IMPORT DATASET (chỉ thao tác tại đây)', open=True):
        gr.Markdown('**1. Chọn ảnh → 2. Nhập mã công trình và mô tả → 3. Nhấn LƯU ẢNH → 4. XEM ẢNH.** '
                    'Ảnh được lưu bên cạnh EXE; không tự huấn luyện, không yêu cầu tìm thư mục Windows.')
        with gr.Row():
            with gr.Column(scale=1):
                dataset_upload = gr.File(label='1 · NẠP NHIỀU ẢNH (kéo thả hoặc bấm chọn)',
                                         file_count='multiple', file_types=['image'])
                dataset_project = gr.Textbox(label='2 · Mã công trình', value='office_demo_01')
                dataset_caption = gr.Textbox(label='3 · Nhãn / mô tả của nhóm ảnh',
                    value='Contemporary office building, architectural facade, realistic proportions',
                    lines=2)
                with gr.Row():
                    dataset_save = gr.Button('LƯU ẢNH VÀ NHÃN NHÁP', variant='primary')
                    dataset_view = gr.Button('XEM ẢNH ĐÃ NẠP')
                dataset_status = gr.JSON(label='Trạng thái nạp dữ liệu')
            with gr.Column(scale=2):
                dataset_gallery = gr.Gallery(label='Ảnh trong công trình (tối đa 40 ảnh mới nhất)',
                                             columns=4, height=320, object_fit='contain')
        def save_dataset(files, project, caption):
            from app.dataset_import import import_images, preview_project
            try:
                result = import_images(ROOT, files, project, caption)
                gallery, summary = preview_project(ROOT, project)
                result['project_summary'] = summary
                return result, gallery
            except (ValueError, OSError) as exc:
                return {'error': str(exc), 'training_started': False}, []
        def show_dataset(project):
            from app.dataset_import import preview_project
            return preview_project(ROOT, project)
        dataset_save.click(save_dataset,
                           inputs=[dataset_upload, dataset_project, dataset_caption],
                           outputs=[dataset_status, dataset_gallery])
        dataset_view.click(show_dataset, inputs=dataset_project,
                           outputs=[dataset_gallery, dataset_status])
        gr.Markdown('**Lưu ý:** Đây là bước thu thập và gán nhãn nháp. Để LoRA học thật cần duyệt dữ liệu, '
                    'chia tập theo công trình và chạy bộ huấn luyện trên NVIDIA CUDA. '
                    'Không tự động đưa ảnh mới vào model.')
    info=gr.Textbox(value=machine_info,label='Cấu hình máy',interactive=False)
    check=gr.Button('KIỂM TRA MÔI TRƯỜNG / LoRA')
    report=gr.Textbox(label='Báo cáo tiền kiểm',lines=5,interactive=False)
    check.click(preflight,outputs=report)
    with gr.Tabs():
        with gr.Tab('01 · Thiết kế & sinh ảnh'):
            with gr.Row():
                with gr.Column(scale=1, min_width=360):
                    reference=gr.Image(label='Ảnh công trình tham chiếu',type='pil',sources=['upload'],height=270)
                    brief=gr.Textbox(label='Mô tả phương án (tiếng Anh cho SD1.5)',lines=3,
                        placeholder='Contemporary office, natural materials, coherent glazing, real-world proportions')
                    preset=gr.Dropdown(choices=list(PRESETS),value='Cân bằng · mặc định',label='Cấu hình nhanh')
                    style=gr.Dropdown(choices=list(STYLE),value='Kiến trúc chân thực',label='Phong cách')
                    preserve=gr.Slider(0.15,0.85,value=0.55,step=0.05,label='Giữ cấu trúc ảnh gốc (cao = ít thay đổi)')
                    with gr.Accordion('Thông số kỹ thuật',open=False):
                        aspect=gr.Dropdown(choices=list(['Vuông 1:1','Ngang 4:3','Ngang 3:2','Dọc 3:4','Dọc 2:3']),
                            value='Ngang 4:3',label='Tỷ lệ ảnh')
                        fit_mode=gr.Radio(choices=['Giữ đủ ảnh (thêm viền)','Cắt đầy khung'],
                            value='Giữ đủ ảnh (thêm viền)',label='Khớp ảnh')
                        memory_mode=gr.Radio(choices=['Cân bằng','Tiết kiệm VRAM tối đa'],
                            value='Tiết kiệm VRAM tối đa',label='Quản lý GPU')
                        steps=gr.Slider(10,50,value=28,step=1,label='Số bước xử lý')
                        guidance=gr.Slider(1,12,value=7.0,step=0.5,label='Mức bám mô tả (CFG)')
                        count=gr.Slider(1,4,value=2,step=1,label='Số phương án')
                        seed=gr.Number(value=-1,precision=0,label='Seed (-1 = ngẫu nhiên)')
                        lora_name=gr.Dropdown(choices=installed_loras(),value='Không dùng LoRA',label='LoRA đã xác minh')
                        refresh_lora=gr.Button('Làm mới danh sách LoRA')
                        refresh_lora.click(lambda: gr.update(choices=installed_loras(),value='Không dùng LoRA'),outputs=lora_name)
                    with gr.Accordion('Hậu xử lý ảnh · không phải AI upscale',open=False):
                        scale=gr.Radio(choices=[1,2,4],value=1,label='Hệ số phóng Lanczos')
                        sharpness=gr.Slider(0,1,value=0.2,step=0.1,label='Làm nét nhẹ')
                    start=gr.Button('TẠO PHƯƠNG ÁN',variant='primary',size='lg')
                with gr.Column(scale=2,min_width=380):
                    gallery=gr.Gallery(label='Các phương án kiến trúc',columns=2,height=630,object_fit='contain')
                    export=gr.File(label='Tải ZIP ảnh, seed và cấu hình')
                    status=gr.Textbox(label='Trạng thái / thông báo',lines=3,interactive=False)
            preset.change(apply_preset,inputs=preset,outputs=[steps,guidance,preserve,count])
            start.click(create,
                inputs=[reference,brief,preserve,steps,count,seed,aspect,fit_mode,memory_mode,lora_name,
                    style,guidance,scale,sharpness],
                outputs=[gallery,export,status],concurrency_limit=1,show_progress='full')
        with gr.Tab('02 · Trạng thái AI'):
            gr.Markdown('Kiểm tra GPU, CUDA, thư viện và LoRA trước khi huấn luyện/sinh ảnh.')
            gr.Button('Kiểm tra lại môi trường').click(preflight,outputs=report)
            gr.Markdown('### V79 · Khả năng chạy trên CPU và model offline')
            readiness = gr.JSON(label='Kiểm tra model SD1.5, LoRA và cấu hình đề xuất')
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
        with gr.Tab('03 · Kiểm tra ảnh & dữ liệu'):
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
        with gr.Tab('04 · AI nâng cao (SDXL / ControlNet / x4)'):
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
            adv_button.click(run_advanced,inputs=[adv_input,adv_prompt,adv_model,adv_control,adv_strength,adv_steps,adv_cfg,adv_control_strength,adv_seed,adv_low],outputs=[adv_output,adv_metadata],concurrency_limit=1)
            upscale_button.click(run_upscale,inputs=[adv_output,adv_prompt,adv_seed,adv_low],outputs=[upscale_output,upscale_metadata],concurrency_limit=1)
        with gr.Tab('05 · Kiểm tra dữ liệu huấn luyện'):
            gr.Markdown('Phát hiện ảnh trùng chính xác và ảnh gần trùng (perceptual hash), caption đơn điệu và cảnh báo nguy cơ overfit. Báo cáo dữ liệu không tự chứng minh mô hình tổng quát hóa.')
            audit_button = gr.Button('KIỂM TRA DATASET ĐÃ CHUẨN BỊ')
            audit_report = gr.JSON(label='Audit dataset/ prepared')
            def audit_data():
                from tools.audit_training import audit
                return audit(ROOT/'dataset'/'prepared')
            audit_button.click(audit_data,outputs=audit_report)
        with gr.Tab('06 · Phản hồi & kiểm tra BIM'):
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
        with gr.Tab('07 · Chất lượng & giới hạn'):
            gr.Markdown("""### Những gì ứng dụng thực sự làm
- Sinh ảnh concept theo ảnh tham chiếu bằng mô hình SD1.5 image-to-image.
- Xuất hình ảnh cùng seed, mô tả, thông số, nguồn và trạng thái LoRA để tái lập.
- Gắn chỉ số độ sáng, tỷ lệ gần đen/trắng, độ tương phản và độ phân giải cho từng ảnh; chỉ là chẩn đoán, không phải AI chấm đẹp.
- Phóng lớn bằng Lanczos và làm nét truyền thống; **không** tăng chi tiết thực bằng AI super-resolution.
- Không dựng hoặc kiểm chứng mô hình BIM, kích thước kỹ thuật, mặt bằng hay số tầng.
- Kết quả đẹp phụ thuộc ảnh huấn luyện, caption, GPU, mô hình nền và cách kiểm định; tăng steps không bảo đảm đẹp hơn.
- Chỉ tuyên bố LoRA đã huấn luyện nếu có checkpoint và hash khớp.""")

if __name__=='__main__':
    ui.queue(default_concurrency_limit=1,max_size=4).launch(
      server_name='127.0.0.1',server_port=7861,inbrowser=True,share=False,
      allowed_paths=[str(OUTPUT)])
