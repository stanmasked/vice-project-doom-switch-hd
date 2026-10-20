"""Synthetic, ROM-free tests for FCEUX TSV evidence corroboration."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_fceux_capture import audit_directory
from test_audit_private_fceux_capture import capture, replace_meta

EVENTS=[
    (120,"8000","80"),(120,"8001","03"),
    (240,"2002","00"),(240,"2000","10")
]


def prepared(root,clock=False):
    first=capture(root,120,screen=False)
    second=capture(root,240,screen=False)
    replace_meta(first,"logged_register_writes=153","logged_register_writes=2")
    replace_meta(second,"logged_register_writes=273","logged_register_writes=4")
    if clock:
        for file in (first,second):
            replace_meta(file,"cycle_trace_available=no","cycle_trace_available=yes")
    write_video(root,EVENTS)
    if clock:
        write_cycles(root,EVENTS)


def write_video(root,events):
    content="frame\taddress\tvalue\n"
    content+="".join(f"{frame}\t{addr}\t{value}\n" for frame,addr,value in events)
    (root/"mmc3_video_writes.tsv").write_text(content,encoding="ascii")


def write_cycles(root,events):
    content="frame\tcpu_cycle\taddress\tvalue\tkind\n"
    content+="".join(
        f"{frame}\t{100+i*2}\t{addr}\t{value}\t{'R' if addr=='2002' else 'W'}\n"
        for i,(frame,addr,value) in enumerate(events)
    )
    (root/"mmc3_ppu_cycles.tsv").write_text(content,encoding="ascii")


class PrivateLogAlignmentTests(unittest.TestCase):
    def test_valid_register_log_counters(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root)
            result=audit_directory(root,require_logs=True)
            self.assertTrue(result["register_trace_verified"])
            self.assertFalse(result["cpu_cycle_trace_verified"])
            self.assertEqual(result["verified_register_events"],4)

    def test_valid_cpu_cycle_log_corroboration(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root,clock=True)
            result=audit_directory(root,require_logs=True)
            self.assertTrue(result["register_trace_verified"])
            self.assertTrue(result["cpu_cycle_trace_verified"])
            self.assertEqual(result["verified_register_events"],4)

    def test_default_metadata_only_explicitly_unverified(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120,screen=False)
            result=audit_directory(root)
            self.assertFalse(result["register_trace_verified"])
            self.assertFalse(result["cpu_cycle_trace_verified"])

    def test_require_logs_rejects_missing_tsv(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            capture(root,120,screen=False)
            with self.assertRaisesRegex(ValueError,"required register trace"):
                audit_directory(root,require_logs=True)

    def test_reject_mismatched_cumulative_counts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root)
            p=root/"frame_000120.meta.txt"
            replace_meta(p,"logged_register_writes=2","logged_register_writes=3")
            with self.assertRaisesRegex(ValueError,"event count differs"):
                audit_directory(root,require_logs=True)

    def test_reject_truncated_register_trace(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root)
            write_video(root,EVENTS[:3])
            with self.assertRaisesRegex(ValueError,"event count differs"):
                audit_directory(root,require_logs=True)

    def test_reject_unexpected_register_address(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root)
            altered=list(EVENTS)
            altered[1]=(120,"8888","03")
            write_video(root,altered)
            with self.assertRaisesRegex(ValueError,"unexpected register address"):
                audit_directory(root,require_logs=True)

    def test_reject_out_of_order_trace_frames(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root)
            write_video(root,list(reversed(EVENTS)))
            with self.assertRaisesRegex(ValueError,"ordering regressed"):
                audit_directory(root,require_logs=True)

    def test_reject_missing_cycle_trace_when_clock_declared(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root,clock=True)
            (root/"mmc3_ppu_cycles.tsv").unlink()
            with self.assertRaisesRegex(ValueError,"required register trace"):
                audit_directory(root,require_logs=True)

    def test_reject_cycle_trace_event_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root,clock=True)
            p=root/"mmc3_ppu_cycles.tsv"
            replace_meta(p,"120\t102\t8001\t03\tW",
                            "120\t102\t8001\t04\tW")
            with self.assertRaisesRegex(ValueError,"event mismatch"):
                audit_directory(root,require_logs=True)

    def test_reject_stale_cycle_file_when_clock_disabled(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root)
            write_cycles(root,EVENTS)
            with self.assertRaisesRegex(ValueError,"unexpected CPU-cycle"):
                audit_directory(root,require_logs=True)

    def test_reject_cycle_regression_within_frame(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root,clock=True)
            p=root/"mmc3_ppu_cycles.tsv"
            replace_meta(p,"120\t102\t8001\t03\tW",
                            "120\t99\t8001\t03\tW")
            with self.assertRaisesRegex(ValueError,"order regressed"):
                audit_directory(root,require_logs=True)


    def test_reject_per_frame_event_overflow(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root)
            write_video(root,[(120,"2000","10")]*12001)
            with self.assertRaisesRegex(ValueError,"per-frame event cap"):
                audit_directory(root,require_logs=True)

    def test_accept_trailing_events_after_last_capture(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root,clock=True)
            trailing=EVENTS+[(241,"2001","02")]
            write_video(root,trailing)
            write_cycles(root,trailing)
            report=audit_directory(root,require_logs=True)
            self.assertTrue(report["cpu_cycle_trace_verified"])
            self.assertEqual(report["verified_register_events"],5)

    def test_reject_invalid_trailing_event(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root)
            write_video(root,EVENTS+[(241,"FFFF","02")])
            with self.assertRaisesRegex(ValueError,"unexpected register address"):
                audit_directory(root,require_logs=True)

    def test_reject_wrong_read_marker_kind(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root,clock=True)
            p=root/"mmc3_ppu_cycles.tsv"
            replace_meta(p,"240\t104\t2002\t00\tR",
                            "240\t104\t2002\t00\tW")
            with self.assertRaisesRegex(ValueError,"read/write kind"):
                audit_directory(root,require_logs=True)

    def test_reject_nonzero_ppustatus_read_marker(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            prepared(root,clock=True)
            altered=list(EVENTS)
            altered[2]=(240,"2002","FF")
            write_video(root,altered)
            write_cycles(root,altered)
            with self.assertRaisesRegex(ValueError,"PPUSTATUS synthetic read marker"):
                audit_directory(root,require_logs=True)

    def test_reject_impossible_v4_cumulative_logged_count(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            p=capture(root,120,screen=False)
            replace_meta(p,"logged_register_writes=153",
                         "logged_register_writes=250001")
            with self.assertRaisesRegex(ValueError,"native FCEUX session cap"):
                audit_directory(root)


if __name__=="__main__":
    unittest.main()
