"""Synthetic-only tests for the Stage 1-1 FCEUX CPU writer phase audit."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_stage1_frame_phase import audit


def fixture(root,*,mutation=None):
    anchor=root/"invented_frame_clock.tsv"
    frame_witness=root/"invented_frame_witness.txt"
    writer=root/"invented_writer_pcs.tsv"
    writer_witness=root/"invented_writer_witness.txt"
    boundary={99:100000,100:129780,101:159561,102:189340}
    anchor_rows=["frame\tcycle"]+[f"{frame}\t{cycle}"
                                 for frame,cycle in boundary.items()]
    if mutation=="missing_anchor":
        anchor_rows=[s for s in anchor_rows if not s.startswith("101\t")]
    if mutation=="bad_anchor":
        anchor_rows[2]="100\t90000"
    anchor.write_text("\n".join(anchor_rows)+"\n","ascii")
    frame_witness.write_text(
        "format=private_original_fceux_frame_anchor_v1\n"
        "first_observed_frame=1\n"
        "last_observed_frame=102\n"
        "frame_gaps=0\n"
        "rom_identity_verified=yes\n"
        "movie_readonly_verified=yes\n","ascii")
    writer_rows=["frame\tcycle\tpc"]
    for frame,early,late in ((100,1100,24285),(101,1800,24287),
                             (102,800,24286)):
        if mutation=="unstable_late" and frame==101:late=24350
        base=boundary[frame-1]
        cycle_values=(base+early,base+early+7,base+late,base+late+4)
        pcs=("E8EC","E8F1","E369","E36C")
        if mutation=="swapped_pc" and frame==101:
            pcs=("E8EC","E8F1","E36C","E369")
        if mutation=="wrong_early_gap" and frame==101:
            cycle_values=(base+early,base+early+8,base+late,base+late+4)
        for cycle,pc in zip(cycle_values,pcs):
            writer_rows.append(f"{frame}\t{cycle}\t{pc}")
    if mutation=="missing_writer":
        writer_rows.pop()
    writer.write_text("\n".join(writer_rows)+"\n","ascii")
    writer_witness.write_text(
        "format=private_ppuscroll_writer_pc_v1\n"
        "first_observed_frame=1\n"
        "last_observed_frame=102\n"
        "frame_gaps=0\n"
        "writer_pc_hits=12\n"
        "rom_identity_verified=yes\n"
        "movie_readonly_verified=yes\n","ascii")
    return anchor,frame_witness,writer,writer_witness


class OriginalFramePhaseTests(unittest.TestCase):
    def test_valid_frame_phase_and_no_scanline_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            report=audit(*fixture(Path(directory)),start=100,stop=102)
            self.assertEqual(report["window"]["frames"],3)
            self.assertEqual(report["late_e369_since_previous_frame_callback_cycles"],
                             {"min":24285,"max":24287,"spread":2})
            self.assertEqual(report["early_2005_since_previous_frame_callback_cycles"],
                             {"min":800,"max":1800,"spread":1000})
            self.assertEqual(report["early_writer_pair_cycles"],7)
            self.assertEqual(report["late_writer_pair_cycles"],4)
            self.assertTrue(report["late_writer_phase_stability_verified"])
            self.assertFalse(report["absolute_scanline_verified"])
            self.assertFalse(report["ppu_irq_execution_verified"])
            self.assertFalse(report["road_camera_velocity_verified"])

    def test_missing_anchor_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"anchor"):
                audit(*fixture(Path(directory),mutation="missing_anchor"),
                      start=100,stop=102)

    def test_decreasing_frame_clock_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"strictly increasing"):
                audit(*fixture(Path(directory),mutation="bad_anchor"),
                      start=100,stop=102)

    def test_missing_writer_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"writer callback"):
                audit(*fixture(Path(directory),mutation="missing_writer"),
                      start=100,stop=102)

    def test_misordered_writer_pc_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"misordered"):
                audit(*fixture(Path(directory),mutation="swapped_pc"),
                      start=100,stop=102)

    def test_early_pair_latency_change_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"latency changed"):
                audit(*fixture(Path(directory),mutation="wrong_early_gap"),
                      start=100,stop=102)

    def test_late_phase_instability_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"not in a stable"):
                audit(*fixture(Path(directory),mutation="unstable_late"),
                      start=100,stop=102)

    def test_wrong_clock_epoch_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=fixture(Path(directory))
            writer=paths[2]
            txt=writer.read_text("ascii")
            txt=txt.replace("100\t101100\tE8EC","100\t99100\tE8EC")
            writer.write_text(txt,"ascii")
            with self.assertRaisesRegex(ValueError,"outside frame anchors"):
                audit(*paths,start=100,stop=102)

    def test_missing_readonly_witness_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=fixture(Path(directory))
            wit=paths[1]
            wit.write_text(wit.read_text("ascii").replace(
                "movie_readonly_verified=yes","movie_readonly_verified=no"),"ascii")
            with self.assertRaisesRegex(ValueError,"provenance incomplete"):
                audit(*paths,start=100,stop=102)

    def test_private_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=fixture(Path(directory))
            link=Path(directory)/"linked.tsv"
            try:link.symlink_to(paths[0])
            except OSError:self.skipTest("symlink unavailable")
            with self.assertRaisesRegex(ValueError,"invalid private input"):
                audit(link,*paths[1:],start=100,stop=102)


if __name__=="__main__":
    unittest.main()
