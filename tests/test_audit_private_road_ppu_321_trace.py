"""Synthetic 321-frame CPU source events, no NES data."""
from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_road_ppu_321_trace import audit

ANCHORS={600:(79,79),744:(136,134),800:(144,139),920:(24,19)}
CYCLE_OFFSETS=(800,807,24283,24287)
PCS=("E8EC","E8F1","E369","E36C")

def fixture(folder:Path):
    w=["frame\tordinal\tpc\tvalue\tcycle"]
    r=["frame\tram_0d\tppu_2005_writes"]
    for f in range(600,921):
        second,ram=ANCHORS.get(f,(42,18))
        for n,(pc,value,offset) in enumerate(zip(
                PCS,(0,second,0,0),CYCLE_OFFSETS),start=1):
            w.append(f"{f}\t{n}\t{pc}\t{value:02X}\t{f*30000+offset}")
        r.append(f"{f}\t{ram:02X}\t4")
    c=["format=private_road_ppu321_raw_v1",
       "first_observed_frame=0","last_observed_frame=920",
       "frame_gaps=0","frames_sampled=321",
       "cpu_writer_events=1284","registerwrite_2005_events=1284",
       "postframe_ram_samples=321","movie_frames=1000",
       "rom_identity_verified=yes","movie_readonly_verified=yes"]
    (folder/"road_321_writers.tsv").write_text("\n".join(w)+"\n")
    (folder/"road_321_postframe.tsv").write_text("\n".join(r)+"\n")
    (folder/"COMPLETE.txt").write_text("\n".join(c)+"\n")

def change(dir:Path,name,old,new):
    file=dir/name
    data=file.read_text()
    assert old in data
    file.write_text(data.replace(old,new,1))

class Ppu321RawTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        fixture(self.root)
    def tearDown(self):
        self.tmp.cleanup()
    def bad(self,name,old,new):
        change(self.root,name,old,new)
        with self.assertRaises(ValueError):audit(self.root)
    def test_complete_invented_321_frames(self):
        result=audit(self.root)
        self.assertEqual(result["frames_checked"],321)
        self.assertEqual(result["cpu_pc_callbacks"],1284)
        self.assertFalse(result["effective_ppu_scroll_proven"])
        self.assertFalse(result["source_rom_fm2_sha256_join_verified"])
    def test_missing_writer(self):
        self.bad("road_321_writers.tsv","600\t1\tE8EC\t00\t18000800\n","")
    def test_wrong_source_pc(self):
        self.bad("road_321_writers.tsv","600\t2\tE8F1","600\t2\tE8EC")
    def test_wrong_ordinal(self):
        self.bad("road_321_writers.tsv","600\t4\tE36C","600\t5\tE36C")
    def test_bad_early_cycle_gap(self):
        self.bad("road_321_writers.tsv",
                 "600\t2\tE8F1\t4F\t18000807",
                 "600\t2\tE8F1\t4F\t18000808")
    def test_wrong_second_anchor(self):
        self.bad("road_321_writers.tsv",
                 "800\t2\tE8F1\t90\t24000807",
                 "800\t2\tE8F1\t91\t24000807")
    def test_wrong_ram_anchor(self):
        self.bad("road_321_postframe.tsv","744\t86\t4","744\t87\t4")
    def test_missing_frame(self):
        self.bad("road_321_postframe.tsv","920\t13\t4\n","")
    def test_bad_real_write_count(self):
        self.bad("road_321_postframe.tsv","600\t4F\t4","600\t4F\t3")
    def test_forged_source_hash_field(self):
        with (self.root/"COMPLETE.txt").open("a") as f:
            f.write("rom_sha256=0"*2+"\n")
        with self.assertRaises(ValueError):audit(self.root)
    def test_readonly_proof_missing(self):
        self.bad("COMPLETE.txt","movie_readonly_verified=yes","movie_readonly_verified=no")
    def test_truncated_complete_report(self):
        self.bad("COMPLETE.txt","frames_sampled=321","frames_sampled=320")
    def test_wrong_early_pc_value(self):
        self.bad("road_321_writers.tsv",
                 "600\t1\tE8EC\t00","600\t1\tE8EC\t01")
    def test_wrong_writer_schema(self):
        self.bad("road_321_writers.tsv","frame\tordinal\tpc\tvalue\tcycle",
                 "frame\tordinal\tpc\tcycle")
if __name__=="__main__":unittest.main()
