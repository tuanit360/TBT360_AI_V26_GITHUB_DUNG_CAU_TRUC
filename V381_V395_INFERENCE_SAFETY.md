# V381–V395 cumulative inference hardening

One batch (not 15 independent releases). Worker preflights numeric count,
seed, strength, guidance, scale and sharpening including NaN/infinity
before importing PyTorch or Diffusers. Diffusers invocation runs under
torch.inference_mode() to avoid autograd activation retention. Empty
Diffusers image result fails explicitly. Offline local checkpoint absence
is rejected before heavy model inference imports. No UI changes.
Real AI generation requires checkpoint + user-hardware evidence.
