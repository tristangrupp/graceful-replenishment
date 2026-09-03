"""Try to read GSFC netCDF metadata from the partially downloaded first chunk."""
import shutil, os
src = r"E:\Water\Oregan\analysis\tmp\parts\part00"
dst = r"E:\Water\Oregan\analysis\tmp\peek.nc"
shutil.copyfile(src, dst)
print("peek size", os.path.getsize(dst))

with open(dst, "rb") as f:
    magic = f.read(8)
print("magic bytes:", magic)

try:
    import h5py
    with h5py.File(dst, "r") as h:
        print("\n=== HDF5 (netCDF-4) structure ===")
        def show(name, obj):
            kind = "DSET" if isinstance(obj, h5py.Dataset) else "GRP "
            extra = ""
            if isinstance(obj, h5py.Dataset):
                extra = f" shape={obj.shape} dtype={obj.dtype}"
            print(f"  {kind} {name}{extra}")
            for k, v in obj.attrs.items():
                print(f"        @{k} = {str(v)[:200]}")
        h.visititems(show)
        print("\n=== root attrs ===")
        for k, v in h.attrs.items():
            print(f"  @{k} = {str(v)[:300]}")
except Exception as e:
    print("h5py failed:", type(e).__name__, e)

try:
    from netCDF4 import Dataset
    d = Dataset(dst)
    print("\n=== netCDF classic header ===")
    print(d)
    d.close()
except Exception as e:
    print("netCDF4 failed:", type(e).__name__, e)
