# V366–V380 aggregate low-VRAM inference adjustment

Retains the exact existing UI and image-generation workflow.
Uses Diffusers' built-in sequential CPU offload whenever CUDA reports
under 6 GiB total VRAM, even if the existing UI memory-mode choice
was not explicitly set to its most conservative value. The 4 GiB
NVIDIA workstation-class case no longer tries to place the entire
SD1.5 pipeline permanently on the GPU.

The strategy is applied after pipeline loading; system RAM and
installed accelerate/diffusers dependencies are still required.
Regression uses test doubles only. This batch does not prove real
SD1.5 inference on the user's computer.
