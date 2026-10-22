#!/usr/bin/env python3
"""Synthetic tests for private RAM CSV validator; no original ROM or capture required."""
import csv
import importlib.util
import tempfile
from pathlib import Path

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location("ram_validator",HERE/"private_ram_probe_validate.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
FIELDS=("ram_000f","ram_0011","ram_0016","ram_0017","ram_0094","ram_013a","ram_013c")

def write_csv(path, frames):
    with path.open("w",newline="",encoding="utf-8") as stream:
        writer=csv.DictWriter(stream,fieldnames=("frame",*FIELDS))
        writer.writeheader()
        for frame in frames:
            writer.writerow({"frame":frame,**{field:str((frame+i)%256) for i,field in enumerate(FIELDS)}})

def main():
    with tempfile.TemporaryDirectory() as directory:
        root=Path(directory)
        valid=root/"valid.csv"
        write_csv(valid,range(1,322))
        result=module.analyze(valid,321)
        assert result["continuous"] and result["frames"]==321
        gap=root/"gap.csv"
        write_csv(gap,[*range(1,160),*range(161,322)])
        try: module.analyze(gap,321)
        except ValueError: pass
        else: raise AssertionError("frame gap was accepted")
        short=root/"short.csv"
        write_csv(short,range(1,321))
        try: module.analyze(short,321)
        except ValueError: pass
        else: raise AssertionError("short capture was accepted")
        bad=root/"bad.csv"
        bad.write_text("frame,unexpected\n1,0\n",encoding="utf-8")
        try: module.analyze(bad,1)
        except ValueError: pass
        else: raise AssertionError("invalid schema was accepted")
    print("VPD_PRIVATE_RAM_VALIDATOR_TEST_PASS valid=321 gaps_rejected=yes short_rejected=yes schema_rejected=yes")
if __name__=="__main__": main()
