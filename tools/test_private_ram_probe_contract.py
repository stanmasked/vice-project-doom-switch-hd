#!/usr/bin/env python3
"""Source-contract tests for generated private RAM probe; no ROM required."""
import importlib.util
from pathlib import Path
path=Path(__file__).with_name("generate_private_ram_probe.py")
spec=importlib.util.spec_from_file_location("ram_probe",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
def main():
    lua=module.make_lua("probe.csv",321)
    assert "if samples >= 321 then" in lua
    assert "samples = samples + 1" in lua
    assert "assert(out:close())" in lua
    assert 'os.rename("probe.csv.pending", "probe.csv")' in lua
    assert "out:flush()" in lua
    assert "memory.readbyte(address)" in lua
    assert 'out:write("frame,ram_000f,ram_0011,ram_0016,ram_0017,ram_0094,ram_013a,ram_013c\\n")' in lua
    for address in ("0x000F","0x0011","0x0016","0x0017","0x0094","0x013A","0x013C"):
        assert address in lua
    for name,frames in (("../unsafe.csv",321),("bad\\\"name.csv",321),("bad\\\\name.csv",321),("probe.csv",0)):
        try: module.make_lua(name,frames)
        except ValueError: pass
        else: raise AssertionError("unsafe probe configuration accepted")
    print("VPD_PRIVATE_RAM_PROBE_CONTRACT_PASS bounded=321 atomic_rename=yes")
if __name__=="__main__": main()
