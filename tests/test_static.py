from pathlib import Path
import ast
import re
base=Path(__file__).resolve().parents[1]
source=(base/'app'/'generate.py').read_text(encoding='utf8')
ast.parse(source)
assert 'share=False' in source
assert 'model_is_pretrained' in source
assert 'fine_tuned_on_user_dataset' in source
assert 'enable_sequential_cpu_offload' in source
assert (base/'CHAY_TBT360_AI_WINDOWS.bat').exists()
print('STATIC PASS')
