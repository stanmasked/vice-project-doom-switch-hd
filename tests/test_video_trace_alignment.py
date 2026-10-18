"""ROM-free stage39 video alignment regression suite (all anchors invented)."""
import csv
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from align_dispatch_video import correlate
from test_dispatch_execution import fixture, edit

def anchors_file(folder, rows):
    path = folder / 'anchors.csv'
    with path.open('w', encoding='utf8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['video_frame', 'trace_frame', 'label'])
        w.writerows(rows)
    return path

class VideoAlignmentTests(unittest.TestCase):
    def test_anchor_window_and_physical_bank_provenance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace, meta = fixture(root)
            anchors = anchors_file(root, [(120, 100, 'video start'), (130, 101, 'camera test')])
            out = correlate(trace, meta, anchors, radius=0)
            self.assertEqual(len(out['anchors']), 2)
            self.assertEqual(out['anchors'][0]['events'], 12)
            self.assertEqual(out['anchors'][1]['events'], 2)
            self.assertEqual(out['trace_recorded_frame_span'], [100, 101])
            self.assertTrue(out['anchors'][0]['trace_frame_within_recorded_span'])
            self.assertTrue(out['anchors'][0]['anchor_has_instrumented_events'])
            self.assertEqual(out['anchors'][0]['dispatcher_executions']['$E479'], 1)
            self.assertEqual(out['anchors'][0]['timeline'][0]['physical_prg_bank'], None)
            self.assertEqual(out['anchors'][1]['timeline'][0]['physical_prg_bank'], 14)
            self.assertEqual(out['first_level_identity'], 'not verified by alignment alone')

    def test_radius_and_no_interpolation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace, meta = fixture(root)
            anchors = anchors_file(root, [(999, 102, 'later frame')])
            no_hits = correlate(trace, meta, anchors, radius=0)['anchors'][0]
            self.assertEqual(no_hits['events'], 0)
            self.assertFalse(no_hits['trace_frame_within_recorded_span'])
            self.assertFalse(no_hits['anchor_has_instrumented_events'])
            self.assertEqual(correlate(trace, meta, anchors, radius=1)['anchors'][0]['events'], 2)

    def test_reject_out_of_order_or_duplicate_anchors(self):
        for pairs in (
            [(10, 100, 'first'), (10, 101, 'duplicate video')],
            [(10, 100, 'first'), (11, 100, 'duplicate trace')],
            [(10, 100, 'first'), (11, 99, 'reversed trace')],
            [(10, 100, 'first'), (9, 101, 'reversed video')],
        ):
            with self.subTest(pairs=pairs), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                trace, meta = fixture(root)
                with self.assertRaisesRegex(ValueError, 'increase strictly'):
                    correlate(trace, meta, anchors_file(root, pairs))

    def test_invalid_anchors_and_radius_fail_closed(self):
        for rows, error in (
            ([], 'At least one'),
            ([('oops', 100, 'bad')], 'Invalid video frame'),
            ([(10, 100, '')], 'Anchor label'),
        ):
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                trace, meta = fixture(root)
                with self.assertRaisesRegex(ValueError, error):
                    correlate(trace, meta, anchors_file(root, rows))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace, meta = fixture(root)
            anchor = anchors_file(root, [(10, 100, 'start')])
            for radius in (-1, 121):
                with self.assertRaisesRegex(ValueError, 'radius'):
                    correlate(trace, meta, anchor, radius=radius)

    def test_incomplete_or_forged_mapping_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace, meta = fixture(root, drop=1)
            anchor = anchors_file(root, [(10, 100, 'start')])
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                correlate(trace, meta, anchor)
            trace, meta = fixture(root)
            edit(trace, lambda rows: rows[4].update(mapped_bank='14'))
            with self.assertRaisesRegex(ValueError, 'Physical PRG mapping'):
                correlate(trace, meta, anchor)

    def test_malformed_csv_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trace, meta = fixture(root)
            path = anchors_file(root, [(10, 100, 'first')])
            path.write_text('video_frame,trace_frame,label\n10,100,ok,extra\n', encoding='utf8')
            with self.assertRaisesRegex(ValueError, 'Malformed'):
                correlate(trace, meta, path)
            path.write_text('trace_frame,video_frame,label\n100,10,first\n', encoding='utf8')
            with self.assertRaisesRegex(ValueError, 'Expected'):
                correlate(trace, meta, path)

if __name__ == '__main__':
    unittest.main()
