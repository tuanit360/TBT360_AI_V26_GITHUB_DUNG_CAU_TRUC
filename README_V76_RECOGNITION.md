# V76 Raster Recognition Baseline / Nhan dien ban ve raster

This version implements a **deterministic connected-component image algorithm**, **not trained machine learning**. It works for isolated bright filled, axis-aligned shapes on a dark background. User specifies the BIM category, physical extent and elevation; it cannot infer those from pixels.

Run from source root:

```cmd
python -m tools.recognize_v76 demo_data\v76_raster\plan.png --bounds 0 0 10 10 --category wall --reference demo_data\v76_raster\reference.json --output result_v76.json
```

The output contains unverified proposals in meters, raster bounding boxes, geometry comparison and image SHA256. Inputs are synthetic example raster and authored labels. In a real plan, hatching, crossing lines, text, rotations and disconnected boundaries cause false recognition. Independent measurement calibration and validation are required. No BIM dimensions are reliably inferred without scale.

Before a learned model can be claimed, collect licensed annotated real plans, group by project, hold out test buildings, train an actual model and report per-class precision/recall, IoU and metric deviation. No checkpoint/model weights or GPU training are included. Existing V75 modules remain unchanged.

Windows EXE is NOT included; build steps from README_PORTABLE.md remain the intended path and have not been validated on Windows in this environment.
