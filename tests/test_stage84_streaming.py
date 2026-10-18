"""Stage84: large, synthetic event-log streaming and integrity regression."""
from pathlib import Path
from unittest import TestCase, mock
from tempfile import TemporaryDirectory
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_ppu_capture_session import check_log_checksums, SessionError


class StreamingEventLogTests(TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / 'mmc3_video_writes.tsv'
        self.header = b'frame\taddress\tvalue\n'

    def write_trace(self, count=24000):
        checksums = []
        rolling = zlib.adler32(self.header)
        checksums.append(f'{rolling:08X}')
        with self.path.open('wb') as file:
            file.write(self.header)
            for i in range(count):
                row = f'{i // 400}\t8002\t{i % 256:02X}\n'.encode()
                file.write(row)
                rolling = zlib.adler32(row, rolling)
                checksums.append(f'{rolling:08X}')
        return checksums

    def test_24000_events_stream_without_read_bytes(self):
        checksums = self.write_trace()
        # A whole-file read_bytes() would duplicate the growing TSV in RAM.
        with mock.patch.object(Path, 'read_bytes', side_effect=AssertionError('whole file read')):
            actual = check_log_checksums(self.path, checksums[-1], 'frame\taddress\tvalue')
        self.assertEqual(len(actual), 24001)
        for i in (0, 1, 400, 8192, 16384, 24000):
            self.assertEqual(actual[i], checksums[i])

    def test_same_length_edited_middle_row_rejected(self):
        checksums = self.write_trace(900)
        with self.path.open('r+b') as handle:
            handle.seek(1200)
            before = handle.read(1)
            handle.seek(1200)
            handle.write(b'1' if before != b'1' else b'0')
        with self.assertRaisesRegex(SessionError, 'checksum mismatch'):
            check_log_checksums(self.path, checksums[-1], 'frame\taddress\tvalue')

    def test_truncated_newline_rejected(self):
        checksums = self.write_trace(40)
        self.path.write_bytes(self.path.read_bytes()[:-1])
        with self.assertRaisesRegex(SessionError, 'Truncated event log'):
            check_log_checksums(self.path, checksums[-1], 'frame\taddress\tvalue')

    def test_bad_header_rejected(self):
        checksums = self.write_trace(10)
        with self.assertRaisesRegex(SessionError, 'Invalid event log header'):
            check_log_checksums(self.path, checksums[-1], 'frame\twrong\tvalue')

    def test_missing_tsv_rejected(self):
        with self.assertRaisesRegex(SessionError, 'Missing/unreadable event log'):
            check_log_checksums(self.path, '00000001', 'frame\taddress\tvalue')

    def test_duplicate_line_violates_manifest_checksum(self):
        checksums = self.write_trace(5)
        with self.path.open('ab') as stream:
            stream.write(b'0\t8002\t00\n')
        with self.assertRaisesRegex(SessionError, 'checksum mismatch'):
            check_log_checksums(self.path, checksums[-1], 'frame\taddress\tvalue')

    def test_cycle_log_header_still_checked(self):
        self.path.write_bytes(b'frame\tcpu_cycle\taddress\tvalue\tkind\n2\t140\t3FFA\t00\tR\n')
        expected=f'{zlib.adler32(self.path.read_bytes()):08X}'
        checksums=check_log_checksums(self.path, expected, 'frame\tcpu_cycle\taddress\tvalue\tkind')
        self.assertEqual(len(checksums), 2)
