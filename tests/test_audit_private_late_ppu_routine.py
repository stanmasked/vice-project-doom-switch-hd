"""Synthetic ROM-free tests for original late PPU instruction-to-write audit."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_late_ppu_routine import audit, PCS, WRITES, HEADER


def synthetic(root,mutation=None):
    trace=root/"invented_cpu_callbacks.tsv"
    witness=root/"invented_readonly_complete.txt"
    events=[]
    for frame in (10,11,12):
        base=frame*30000+1000
        for pc,offset in PCS:
            a=x=0
            if pc in ("E371","E373","E376","E379"):a=15
            if pc in ("E37B","E37D","E380","E383","E384","E387","E38A"):a=2
            if pc=="E38E":a=14
            if pc in ("E384","E387","E38A","E38E"):x=1
            events.append([str(frame),str(base+offset),"PC",pc,"00",
                           f"{a:02X}",f"{x:02X}","00","24"])
        for pc,port,value,register in WRITES:
            offset=next(t for name,t in PCS if name==pc)
            a=x=0
            if value==15:a=15
            if pc=="E387":a=2;x=1
            if pc=="E384":x=1;a=2
            if pc=="E38E":a=14;x=1
            events.append([str(frame),str(base+offset),"WR",port,
                           f"{value:02X}",f"{a:02X}",f"{x:02X}","00","24"])
    if mutation=="cpu_register":
        for item in events:
            if item[0]=="11" and item[2]=="PC" and item[3]=="E38E":
                item[5]="0F"
    if mutation=="ppu_write":
        for item in events:
            if item[0]=="11" and item[2]=="WR" and item[3]=="2006" and item[4]=="0F":
                item[4]="0E"
    if mutation=="mapper_write":
        for item in events:
            if item[0]=="12" and item[2]=="WR" and item[3]=="8001" and item[4]=="02":
                item[4]="03"
    if mutation=="cpu_offset":
        for item in events:
            if item[0]=="12" and item[2]=="PC" and item[3]=="E38E":
                item[1]=str(int(item[1])+1)
    if mutation=="duplicate_pc":
        events.append(next(row.copy() for row in events
                           if row[0]=="12" and row[2]=="PC" and row[3]=="E38E"))
    if mutation=="missing_pc":
        events=[row for row in events if not(row[0]=="11" and row[2]=="PC"
                                             and row[3]=="E369")]
    if mutation=="clock_regression":
        for row in events:
            if row[0]=="11" and row[2]=="PC" and row[3]=="E373":
                row[1]="1"
    events.sort(key=lambda row:(int(row[0]),int(row[1]),0 if row[2]=="PC" else 1))
    with trace.open("w",encoding="ascii",newline="") as f:
        w=csv.writer(f,delimiter="\t",lineterminator="\n")
        w.writerow(HEADER)
        w.writerows(events)
    witness.write_text(
        "format=private_stage155_cpu_sequence_v1\n"
        "first_observed_frame=1\n"
        "last_observed_frame=12\n"
        "frame_gaps=0\n"
        "callback_events="+str(len(events))+"\n"
        "rom_identity_verified=yes\n"
        "movie_readonly_verified="+("no" if mutation=="not_readonly" else "yes")+"\n",
        encoding="ascii")
    return trace,witness


class LatePpuTests(unittest.TestCase):
    def test_exact_late_routine_with_mm3_and_ppumask(self):
        with tempfile.TemporaryDirectory() as d:
            result=audit(*synthetic(Path(d)),start=10,stop=12)
            self.assertEqual(result["frames_verified"],3)
            self.assertEqual(result["exact_instruction_pc_cycle_matches"],48)
            self.assertEqual(result["exact_instruction_to_register_write_matches"],27)
            self.assertEqual(result["mmc3_chr_register_sequence"],
                             ["8000=00","8001=00","8000=01","8001=02"])
            self.assertFalse(result["ppumask_sprite_rendering_enabled"])
            self.assertFalse(result["visible_scanline_origin_verified"])

    def test_reject_changed_cpu_register(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"CPU register changed"):
                audit(*synthetic(Path(d),"cpu_register"),start=10,stop=12)

    def test_reject_changed_ppu_address(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"actual PPU/MMC3 write differ"):
                audit(*synthetic(Path(d),"ppu_write"),start=10,stop=12)

    def test_reject_changed_mapper_bank(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"actual PPU/MMC3 write differ"):
                audit(*synthetic(Path(d),"mapper_write"),start=10,stop=12)

    def test_reject_changed_cpu_cycles(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"cycle offset differs"):
                audit(*synthetic(Path(d),"cpu_offset"),start=10,stop=12)

    def test_reject_duplicate_cpu_instruction(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"duplicated"):
                audit(*synthetic(Path(d),"duplicate_pc"),start=10,stop=12)

    def test_reject_missing_cpu_instruction(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"missing"):
                audit(*synthetic(Path(d),"missing_pc"),start=10,stop=12)

    def test_reject_cpu_clock_reset(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"epoch changed"):
                audit(*synthetic(Path(d),"clock_regression"),start=10,stop=12)

    def test_reject_non_readonly_movie(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"provenance incomplete"):
                audit(*synthetic(Path(d),"not_readonly"),start=10,stop=12)

    def test_reject_linked_private_trace(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            trace,witness=synthetic(root)
            link=root/"alias.tsv"
            try:link.symlink_to(trace)
            except OSError:self.skipTest("symlinks unsupported")
            with self.assertRaisesRegex(ValueError,"linked"):
                audit(link,witness,start=10,stop=12)


if __name__=="__main__":
    unittest.main()
