import h5py, numpy as np
from pathlib import Path
P = Path(r"E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5")
f = h5py.File(P, "r")

def walk(name, obj):
    if isinstance(obj, h5py.Dataset):
        attrs = {k: (v.decode() if isinstance(v, bytes) else v) for k, v in obj.attrs.items()}
        s = "; ".join(f"{k}={v!r}" for k, v in attrs.items())
        if len(s) > 300: s = s[:300] + "...[trunc]"
        try:
            a = obj[()]
            rng = f"min={np.nanmin(a):.6g} max={np.nanmax(a):.6g}" if a.dtype.kind in "fiu" else "non-numeric"
        except Exception as e:
            rng = f"err {e}"
        print(f"D {name:45s} shape={str(obj.shape):18s} dtype={obj.dtype} {rng}  | {s}")
    else:
        attrs = {k: (v.decode() if isinstance(v, bytes) else v) for k, v in obj.attrs.items()}
        print(f"G {name:45s} attrs={attrs}")

print("=== ROOT ATTRS ===")
for k, v in f.attrs.items():
    v = v.decode() if isinstance(v, bytes) else v
    print(f"  {k}: {str(v)[:800]}")
print("\n=== TREE ===")
f.visititems(walk)
f.close()
