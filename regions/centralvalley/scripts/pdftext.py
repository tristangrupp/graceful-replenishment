"""Minimal stdlib-only PDF text extractor.

Written because pypdf is not installed in the shared venv and the venv must not
be modified. Decompresses FlateDecode content streams and pulls literal strings
out of Tj/TJ operators. Good enough to read a legend table; not a general PDF
parser. Anything it cannot decode is reported, never silently dropped.
"""
import re
import sys
import zlib
from pathlib import Path


def extract(path):
    data = Path(path).read_bytes()
    out = []
    nfail = 0
    for m in re.finditer(rb"stream\r?\n", data):
        start = m.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        raw = data[start:end]
        try:
            txt = zlib.decompress(raw)
        except Exception:
            nfail += 1
            continue
        out.append(txt)
    return out, nfail


TJ = re.compile(rb"\((?:\\.|[^()\\])*\)")


def unescape(b):
    b = b[1:-1]
    b = b.replace(rb"\(", b"(").replace(rb"\)", b")").replace(rb"\\", b"\\")
    return b.decode("latin-1")


def page_text(stream):
    lines = []
    for chunk in re.split(rb"(?:TJ|Tj|'|\")", stream):
        strs = TJ.findall(chunk)
        if strs:
            lines.append("".join(unescape(s) for s in strs))
    return lines


if __name__ == "__main__":
    streams, nfail = extract(sys.argv[1])
    print(f"# streams decoded={len(streams)} failed={nfail}", file=sys.stderr)
    for s in streams:
        if b"Tj" not in s and b"TJ" not in s:
            continue
        for ln in page_text(s):
            if ln.strip():
                print(ln)
