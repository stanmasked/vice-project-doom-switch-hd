"""Only fabricated private FM2 terminal witnesses; no source ROM/movie."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_fm2_terminal_witness import audit_movie_witness

GOOD={
    "format":"private_fm2_terminal_witness_v4",
    "loaded_rom_verified":"yes","fm2_header_power_on_preflight_verified":"yes",
    "movie_readonly":"yes","movie_terminal_frame":"63","movie_frame_count":"64",
    "movie_first_observed_frame":"1","movie_last_observed_frame":"63",
    "movie_consecutive_unique_frames":"63","movie_frame_gaps":"0",
    "movie_active_before_terminal":"yes","movie_mode_at_terminal":"playback",
    "original_stage_proven":"no","game_completion_proven":"no"
}

def make(directory,data=None):
    f=Path(directory)/"terminal.witness.txt"
    obj=GOOD if data is None else data
    f.write_text("".join(k+"="+v+"\n" for k,v in obj.items()),encoding="ascii")
    return f

class MovieCallbackContinuityTests(unittest.TestCase):
    def audit(self,path,frames=64):
        return audit_movie_witness(path,expected_frame_count=frames)

    def test_good_callback_sequence_from_frame_one(self):
        with tempfile.TemporaryDirectory() as d:
            result=self.audit(make(d))
            self.assertEqual(result["consecutive_unique_frames"],63)
            self.assertEqual(result["frame_gaps"],0)
            self.assertFalse(result["game_completion_proven"])

    def test_frame_zero_is_permitted(self):
        with tempfile.TemporaryDirectory() as d:
            values=dict(GOOD,movie_first_observed_frame="0",
                        movie_consecutive_unique_frames="64")
            self.assertEqual(self.audit(make(d,values))["first_observed_frame"],0)

    def test_first_callback_after_one_refused(self):
        with tempfile.TemporaryDirectory() as d:
            values=dict(GOOD,movie_first_observed_frame="2",
                        movie_consecutive_unique_frames="62")
            with self.assertRaisesRegex(ValueError,"start near frame zero"):
                self.audit(make(d,values))

    def test_missing_intermediate_callback_refused(self):
        with tempfile.TemporaryDirectory() as d:
            values=dict(GOOD,movie_consecutive_unique_frames="62")
            with self.assertRaisesRegex(ValueError,"noncontiguous"):
                self.audit(make(d,values))

    def test_explicit_gap_refused_even_if_count_matches(self):
        with tempfile.TemporaryDirectory() as d:
            values=dict(GOOD,movie_frame_gaps="1")
            with self.assertRaisesRegex(ValueError,"noncontiguous"):
                self.audit(make(d,values))

    def test_wrong_rom_rejected_in_witness(self):
        with tempfile.TemporaryDirectory() as d:
            values=dict(GOOD,loaded_rom_verified="no")
            with self.assertRaisesRegex(ValueError,"identity"):
                self.audit(make(d,values))

    def test_savestate_movie_rejected_in_witness(self):
        with tempfile.TemporaryDirectory() as d:
            values=dict(GOOD,fm2_header_power_on_preflight_verified="no")
            with self.assertRaisesRegex(ValueError,"power-on"):
                self.audit(make(d,values))

    def test_legacy_v3_witness_refused(self):
        with tempfile.TemporaryDirectory() as d:
            values=dict(GOOD,format="private_fm2_terminal_witness_v3")
            with self.assertRaisesRegex(ValueError,"legacy"):
                self.audit(make(d,values))

    def test_legacy_v2_witness_refused(self):
        with tempfile.TemporaryDirectory() as d:
            values=dict(GOOD,format="private_fm2_terminal_witness_v2")
            with self.assertRaisesRegex(ValueError,"legacy"):
                self.audit(make(d,values))

    def test_legacy_v1_witness_refused(self):
        with tempfile.TemporaryDirectory() as d:
            values=dict(GOOD,format="private_fm2_terminal_witness_v1")
            with self.assertRaisesRegex(ValueError,"legacy"):
                self.audit(make(d,values))

    def test_extra_or_missing_field_refused(self):
        with tempfile.TemporaryDirectory() as d:
            values={k:v for k,v in GOOD.items() if k!="movie_last_observed_frame"}
            with self.assertRaisesRegex(ValueError,"missing"):
                self.audit(make(d,values))

    def test_lie_about_game_completion_refused(self):
        with tempfile.TemporaryDirectory() as d:
            values=dict(GOOD,game_completion_proven="yes")
            with self.assertRaisesRegex(ValueError,"success claim"):
                self.audit(make(d,values))

    def test_wrong_source_movie_length_refused(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"length differs"):
                self.audit(make(d),frames=65)

    def test_readonly_missing_refused(self):
        with tempfile.TemporaryDirectory() as d:
            values=dict(GOOD,movie_readonly="no")
            with self.assertRaisesRegex(ValueError,"read-only"):
                self.audit(make(d,values))

    def test_invalid_frame_notation_refused(self):
        with tempfile.TemporaryDirectory() as d:
            values=dict(GOOD,movie_terminal_frame="00063")
            with self.assertRaisesRegex(ValueError,"numeric"):
                self.audit(make(d,values))

    def test_duplicate_witness_line_refused(self):
        with tempfile.TemporaryDirectory() as d:
            file=make(d)
            with file.open("a",encoding="ascii") as f:
                f.write("movie_frame_gaps=0\n")
            with self.assertRaisesRegex(ValueError,"duplicate"):
                self.audit(file)

    def test_symlink_refused(self):
        with tempfile.TemporaryDirectory() as d:
            real=make(d);link=Path(d)/"symlink.witness"
            try:link.symlink_to(real)
            except OSError as exc:self.skipTest(str(exc))
            with self.assertRaisesRegex(ValueError,"linked"):
                self.audit(link)

    def test_truncated_witness_refused(self):
        with tempfile.TemporaryDirectory() as d:
            file=make(d)
            file.write_text("movie_terminal_frame=63\n",encoding="ascii")
            with self.assertRaisesRegex(ValueError,"missing"):
                self.audit(file)
if __name__=="__main__":
    unittest.main()
