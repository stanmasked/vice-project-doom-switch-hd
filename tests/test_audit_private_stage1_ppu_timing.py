"""Purely invented FCEUX-style CPU/RAM/roadway fixtures, never original data."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_stage1_ppu_timing import audit


def fixture(root,*,malformed=None,cycle_reset=False,pattern_ok=True,add_status=False):
    events=root/'invented_events.tsv'
    ram=root/'invented_ram.tsv'
    road=root/'invented_road.json'
    rows=['frame\tcycles\taddress\tvalue\tkind']
    cycle=100
    for frame in range(10,13):
        value=12+frame
        if add_status:
            rows.append(f'{frame}\t{cycle-1}\t2002\t00\tR')
        values=[0,value,0,0] if pattern_ok else [value,0,0,0]
        for index,v in enumerate(values):
            seq=[cycle,cycle+7,cycle+200,cycle+204]
            if cycle_reset and frame==11:seq=[0,7,200,204]
            rows.append(f'{frame}\t{seq[index]}\t2005\t{v:02X}\tW')
        cycle+=1000
    if malformed=='missing':rows.pop()
    if malformed=='bad_hex':rows[-1]=rows[-1].replace('2005','0W05')
    events.write_text('\n'.join(rows)+'\n',encoding='ascii')
    ram.write_text('frame\tram_0b\tram_0c\tram_0d\tvideo_event_count\n'+
                   '10\t00\t00\t16\t4\n12\t00\t00\t18\t12\n',encoding='ascii')
    road.write_text(json.dumps({'schema':'vice-stage1-private-road-mask-scan-v1',
            'frames':[{'frame':10,'roi_valid':True,'observed_width':87,
                       'observed_center_x':126.0},
                      {'frame':12,'roi_valid':False}]})+'\n')
    return events,ram,road


class PrivateStage1PpuTests(unittest.TestCase):
    def test_candidate_sequence_and_road_join(self):
        with tempfile.TemporaryDirectory() as directory:
            events,ram,road=fixture(Path(directory))
            report=audit(events,ram,start=10,stop=12,road_path=road,
                         selected_frames=(10,11,12))
            self.assertEqual(report['scroll_2005_write_count'],12)
            self.assertEqual(report['frames_with_four_zero_value_pattern'],3)
            self.assertEqual(report['first_2005_gap_cycles_unique'],[7])
            self.assertEqual(report['ram_postframe_sample_count'],2)
            self.assertEqual(report['road_rgb_valid_sample_count'],1)
            self.assertEqual(report['representative_observations'][0]
                             ['observed_road_width_pixels'],87)
            self.assertFalse(report['display_effective_scroll_proven'])
            self.assertFalse(report['camera_speed_proven'])
            self.assertFalse(report['ppu_latch_origin_verified'])

    def test_read_marker_is_not_rendered_scroll_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            events,ram,road=fixture(Path(directory),add_status=True)
            report=audit(events,ram,start=10,stop=12)
            self.assertTrue(report['status_read_markers_present'])
            self.assertFalse(report['ppu_latch_origin_verified'])
            self.assertFalse(report['display_effective_scroll_proven'])

    def test_reject_missing_scroll_write(self):
        with tempfile.TemporaryDirectory() as directory:
            events,ram,road=fixture(Path(directory),malformed='missing')
            with self.assertRaisesRegex(ValueError,'write count'):
                audit(events,ram,start=10,stop=12)

    def test_reject_different_write_pattern(self):
        with tempfile.TemporaryDirectory() as directory:
            events,ram,road=fixture(Path(directory),pattern_ok=False)
            with self.assertRaisesRegex(ValueError,'sequence differs'):
                audit(events,ram,start=10,stop=12)

    def test_reject_cpu_cycle_epoch_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            events,ram,road=fixture(Path(directory),cycle_reset=True)
            with self.assertRaisesRegex(ValueError,'went backwards'):
                audit(events,ram,start=10,stop=12)

    def test_reject_malformed_hex_address(self):
        with tempfile.TemporaryDirectory() as directory:
            events,ram,road=fixture(Path(directory),malformed='bad_hex')
            with self.assertRaisesRegex(ValueError,'invalid address'):
                audit(events,ram,start=10,stop=12)

    def test_reject_reversed_window(self):
        with tempfile.TemporaryDirectory() as directory:
            events,ram,road=fixture(Path(directory))
            with self.assertRaisesRegex(ValueError,'invalid private sampling window'):
                audit(events,ram,start=12,stop=10)

    def test_reject_bad_road_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            events,ram,road=fixture(Path(directory))
            road.write_text('{"schema":"wrong","frames":[]}',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'schema'):
                audit(events,ram,start=10,stop=12,road_path=road)

    def test_reject_symlink_private_log(self):
        with tempfile.TemporaryDirectory() as directory:
            events,ram,road=fixture(Path(directory))
            link=Path(directory)/'events_link.tsv'
            try:link.symlink_to(events)
            except OSError:self.skipTest('symlinks unsupported')
            with self.assertRaisesRegex(ValueError,'linked'):
                audit(link,ram,start=10,stop=12)


if __name__=='__main__':
    unittest.main()
