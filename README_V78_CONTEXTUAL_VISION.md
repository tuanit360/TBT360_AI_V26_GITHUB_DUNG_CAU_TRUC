# V78 – Contextual architecture-vision baseline

Adds multi-scale pixel context (5×5 and 13×13), trainable weights, validation-based early stopping, per-project evaluation and versioned checkpoints, while retaining all V77 modules. This is a **learned pixel baseline**, **not** a CNN, full semantic understanding, metric BIM recognition or guaranteed improvement over V77.

On Windows with Python 3.11 and dependencies: `TRAIN_VISION_V78_WINDOWS.bat` runs the included **synthetic** demonstration. For a real annotated dataset, run:

`python -m tools.train_vision_v78 --dataset DATASET --checkpoint output/v78.npz --report output/v78.json`

Each project must occur in exactly one split (train/validation/test). Only validation selects epochs; test is evaluated once after selection. Report contains per-class and per-project metrics. Compare on the same real independent test set before accepting any model. The included sample checkpoint is not suitable for production. No EXE is shipped or proven to work on Windows.
