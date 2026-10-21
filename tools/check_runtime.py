import sys, json, importlib
modules = ['torch','torchvision','gradio','diffusers','transformers','accelerate','safetensors','PIL','peft','datasets','tensorboard']
errors={}
versions={}
for name in modules:
    try:
        m=importlib.import_module(name)
        versions[name]=getattr(m,'__version__','available')
    except Exception as exc:
        errors[name]=f'{type(exc).__name__}: {exc}'
try:
    import torch
    cuda=torch.cuda.is_available()
    device=torch.cuda.get_device_name(0) if cuda else 'CPU only'
except Exception:
    cuda=False;device='Not checked'
print(json.dumps({'ok':not errors,'python':sys.executable,'versions':versions,'errors':errors,'cuda':cuda,'device':device},ensure_ascii=False,indent=2))
sys.exit(0 if not errors else 2)
