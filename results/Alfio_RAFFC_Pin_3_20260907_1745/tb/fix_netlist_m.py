import re
from pathlib import Path

src = Path(r"d:\proj\spice-analyzer\results\Alfio_RAFFC_Pin_3_20260907_1745\tb\Alfio_RAFFC_Pin_3")
text = src.read_text(encoding="utf-8")
pat = re.compile(r"w='([^']+)'\s+m='([^']+)'", re.I)

def repl(mo):
    w, m = mo.group(1), mo.group(2)
    return f"w='({w})*({m})' mult='{m}'"

new, n = pat.subn(repl, text)
src.write_text(new, encoding="utf-8", newline="\n")
print("replacements", n)
print(new)
