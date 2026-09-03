"""Assemble the standalone explorer: one file, openable straight from disk.

Emits a complete document rather than a fragment. This matters for a local
file: without a charset declaration the browser falls back to the system code
page, and every multi-byte UTF-8 character shows a stray capital A-circumflex
in front of it. Declaring UTF-8 in the first bytes of the head is what stops it.
"""
from pathlib import Path

V = Path(r"E:\Water\Global\viz")
head = (V / "head.html").read_text(encoding="utf-8")
body = (V / "body.html").read_text(encoding="utf-8")
data = (V / "grace_basins.json").read_text(encoding="utf-8")
app = (V / "app.js").read_text(encoding="utf-8")

# The payload rides in an application/json block rather than a JS literal, so
# nothing in the data can end the script early. Escaping "<" is what guarantees
# it: JSON has no unescaped "<" outside strings, and inside them it becomes a
# unicode escape that JSON.parse turns back into the original character.
data = data.replace("<", "\u003c")

doc = (
    "<!doctype html>\n"
    '<html lang="en">\n'
    "<head>\n"
    '<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    '<meta name="color-scheme" content="light dark">\n'
    + head
    + "</head>\n<body>\n"
    + body
    + '\n<script type="application/json" id="data">' + data + "</script>\n"
    + "<script>\n" + app + "\n</script>\n"
    + "</body>\n</html>\n"
)

out = V / "grace_basin_explorer.html"
out.write_text(doc, encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size/1e6:.2f} MB)")
