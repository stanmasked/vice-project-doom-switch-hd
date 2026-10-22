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
    assert "if frame >= 321 then" in lua
    assert "assert(out:close())" in lua
    assert 'os.rename("probe.csv.pending", "probe.csv")' in lua
    assert "out:flush()" in lua
    assert "memory.readbyte(address)" in lua
    for name,frames in (("../unsafe.csv",321),("probe.csv",0)):
        try: module.make_lua(name,frames)
        except ValueError: pass
        else: raise AssertionError("unsafe probe configuration accepted")
    print("VPD_PRIVATE_RAM_PROBE_CONTRACT_PASS bounded=321 atomic_rename=yes")
if __name__=="__main__": main()
