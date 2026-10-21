"""Synthetic-only regression tests for exact original $E8DE CPU provenance."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from audit_private_e8de_exec import audit


def fixture(root,*,bad=None):
    execution=root/"invented_exec.tsv"
    counts=root/"invented_counts.tsv"
    events=root/"invented_events.tsv"
    witness=root/"invented_complete.txt"
    exec_rows=["frame\tcycle\tram_0b\tram_0c\tram_0d"]
    count_rows=["frame\texec_hits"]
    event_rows=["frame\tcycles\taddress\tvalue\tkind"]
    for i,frame in enumerate(range(10,13)):
        cycle=1000+1000*i
        ram=(50+i) if bad!="wrong_ram" or frame!=11 else 70
        exec_rows.append(f"{frame}\t{cycle}\t00\t00\t{ram:02X}")
        count_rows.append(f"{frame}\t{2 if bad=='duplicate' and frame==11 else 1}")
        scroll=(50+i)
        if bad=="wrong_value" and frame==11:scroll=72
        late=1 if bad=="late_nonzero" and frame==12 else 0
        rows=[(9,"2000","88"),(20,"2005","00"),
              (27,"2005",f"{scroll:02X}"),
              (150,"2005",f"{late:02X}"),(154,"2005","00")]
        if bad=="wrong_delay" and frame==11:
            rows[2]=(28,"2005",f"{scroll:02X}")
        if bad=="missing_scroll" and frame==11:rows=rows[:-1]
        for offset,addr,value in rows:
            event_rows.append(f"{frame}\t{cycle+offset}\t{addr}\t{value}\tW")
    execution.write_text("\n".join(exec_rows)+"\n",encoding="ascii")
    counts.write_text("\n".join(count_rows)+"\n",encoding="ascii")
    events.write_text("\n".join(event_rows)+"\n",encoding="ascii")
    witness.write_text(
        "format=private_e8de_emitter_exec_v1\n"
        "first_observed_frame=1\n"
        "last_observed_frame=12\n"
        "frame_gaps=0\n"
        "exec_callback_count=3\n"
        "rom_identity_verified=yes\n"
        "movie_readonly_verified=yes\n",encoding="ascii")
    return execution,counts,events,witness


def instruction_fixture(root):
    paths=fixture(root)
    observed=root/"invented_pc_events.tsv"
    finished=root/"invented_pc_complete.txt"
    lines=["frame\tcycle\tpc"]
    for i,frame in enumerate(range(10,13)):
        cycle=1000+i*1000
        for pc,offset in (("E8DE",0),("E8E4",9),("E8E7",13),
                          ("E8EC",20),("E8F1",27)):
            lines.append(f"{frame}\t{cycle+offset}\t{pc}")
    observed.write_text("\n".join(lines)+"\n",encoding="ascii")
    finished.write_text(
        "format=private_e8de_instruction_trace_v1\n"
        "first_observed_frame=1\n"
        "last_observed_frame=12\n"
        "frame_gaps=0\n"
        "total_instruction_callbacks=15\n"
        "rom_identity_verified=yes\n"
        "movie_readonly_verified=yes\n",encoding="ascii")
    return (*paths,observed,finished)


def writer_fixture(root):
    paths=fixture(root)
    writer=root/"invented_writer_pcs.tsv"
    witness=root/"invented_writer_complete.txt"
    rows=["frame\tcycle\tpc"]
    for i,frame in enumerate(range(10,13)):
        cycle=1000+i*1000
        for pc,delta in (("E8EC",20),("E8F1",27),
                         ("E369",150),("E36C",154)):
            rows.append(f"{frame}\t{cycle+delta}\t{pc}")
    writer.write_text("\n".join(rows)+"\n",encoding="ascii")
    witness.write_text(
        "format=private_ppuscroll_writer_pc_v1\n"
        "first_observed_frame=1\n"
        "last_observed_frame=12\n"
        "frame_gaps=0\n"
        "writer_pc_hits=12\n"
        "rom_identity_verified=yes\n"
        "movie_readonly_verified=yes\n",encoding="ascii")
    return (*paths,writer,witness)


class E8DEExecutionTests(unittest.TestCase):
    def test_exact_cycle_offsets_and_ram_correspondence(self):
        with tempfile.TemporaryDirectory() as directory:
            report=audit(*fixture(Path(directory)),start=10,stop=12)
            self.assertEqual(report["checked_frames"],3)
            self.assertEqual(report["observed_emitter_executions"],3)
            self.assertEqual(report["ppu_control_write_latency_cpu_cycles"],9)
            self.assertEqual(report["first_ppuscroll_write_latency_cpu_cycles"],20)
            self.assertEqual(report["second_ppuscroll_write_latency_cpu_cycles"],27)
            self.assertEqual(report["observed_later_zero_scroll_write_frames"],3)
            self.assertFalse(report["display_effective_scroll_verified"])
            self.assertFalse(report["car_camera_speed_verified"])

    def test_verified_2002_read_opcode_instruction_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=instruction_fixture(Path(directory))
            report=audit(*paths[:4],start=10,stop=12,
                         instruction_trace=paths[4],
                         instruction_witness=paths[5])
            self.assertTrue(report["runtime_executed_opcode_at_e8e7"])
            self.assertEqual(report["instruction_callbacks_verified"],15)
            self.assertEqual(
                report["relative_instruction_execution_cpu_cycles"],
                [0,9,13,20,27])
            self.assertFalse(report["direct_lua_2002_read_callback_claimed"])
            self.assertFalse(report["display_effective_scroll_verified"])

    def test_reject_missing_2002_read_instruction_callback(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=instruction_fixture(Path(directory))
            trace=paths[4]
            lines=trace.read_text("ascii").splitlines()
            trace.write_text("\n".join(s for s in lines
                 if s!="11\t2013\tE8E7")+"\n",encoding="ascii")
            with self.assertRaisesRegex(ValueError,"incomplete"):
                audit(*paths[:4],start=10,stop=12,
                      instruction_trace=trace,instruction_witness=paths[5])

    def test_reject_swapped_instruction_order(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=instruction_fixture(Path(directory))
            trace=paths[4]
            data=trace.read_text("ascii").replace("11\t2013\tE8E7",
                                                   "11\t2013\tE8EC")
            trace.write_text(data,encoding="ascii")
            with self.assertRaisesRegex(ValueError,"PC chain"):
                audit(*paths[:4],start=10,stop=12,
                      instruction_trace=trace,instruction_witness=paths[5])

    def test_reject_trace_without_witness(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=instruction_fixture(Path(directory))
            with self.assertRaisesRegex(ValueError,"together"):
                audit(*paths[:4],start=10,stop=12,
                      instruction_trace=paths[4])

    def test_all_four_writer_pc_cycle_matches(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=writer_fixture(Path(directory))
            report=audit(*paths[:4],start=10,stop=12,
                         writer_trace=paths[4],writer_witness=paths[5])
            self.assertEqual(report["writer_callbacks_verified"],12)
            self.assertEqual(report["frames_with_four_matched_writers"],3)
            self.assertEqual(report["verified_2005_instruction_addresses"],
                             ["$E8EC","$E8F1","$E369","$E36C"])
            self.assertTrue(report["all_four_write_pc_cycles_matched"])
            self.assertFalse(report["later_raster_effect_verified"])

    def test_reject_modified_late_writer_pc(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=writer_fixture(Path(directory))
            writer=paths[4]
            writer.write_text(writer.read_text("ascii").replace(
                "11\t2150\tE369","11\t2150\tE36C"),encoding="ascii")
            with self.assertRaisesRegex(ValueError,"did not match"):
                audit(*paths[:4],start=10,stop=12,
                      writer_trace=writer,writer_witness=paths[5])

    def test_reject_modified_late_writer_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=writer_fixture(Path(directory))
            writer=paths[4]
            writer.write_text(writer.read_text("ascii").replace(
                "12\t2154\tE36C","12\t2155\tE36C"),encoding="ascii")
            # Mutate the real frame-12 row instead of a non-matching string.
            writer.write_text(writer.read_text("ascii").replace(
                "12\t3154\tE36C","12\t3155\tE36C"),encoding="ascii")
            with self.assertRaisesRegex(ValueError,"did not match"):
                audit(*paths[:4],start=10,stop=12,
                      writer_trace=writer,writer_witness=paths[5])

    def test_reject_missing_writer_witness(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=writer_fixture(Path(directory))
            with self.assertRaisesRegex(ValueError,"together"):
                audit(*paths[:4],start=10,stop=12,
                      writer_trace=paths[4])

    def test_reject_duplicate_execution_callback(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"duplicated"):
                audit(*fixture(Path(directory),bad="duplicate"),start=10,stop=12)

    def test_reject_changed_ram_source(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"RAM input"):
                audit(*fixture(Path(directory),bad="wrong_ram"),start=10,stop=12)

    def test_reject_mismatched_ppuscroll_value(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"RAM input"):
                audit(*fixture(Path(directory),bad="wrong_value"),start=10,stop=12)

    def test_reject_cpu_latency_change(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"RAM input"):
                audit(*fixture(Path(directory),bad="wrong_delay"),start=10,stop=12)

    def test_reject_incomplete_frame_scroll_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"four observed"):
                audit(*fixture(Path(directory),bad="missing_scroll"),start=10,stop=12)

    def test_reject_edited_late_scroll_reset(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"zero reset"):
                audit(*fixture(Path(directory),bad="late_nonzero"),start=10,stop=12)

    def test_reject_unverified_rom_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=fixture(Path(directory))
            witness=paths[-1]
            witness.write_text(witness.read_text("ascii").replace(
                "rom_identity_verified=yes","rom_identity_verified=no"),"ascii")
            with self.assertRaisesRegex(ValueError,"identity unverified"):
                audit(*paths,start=10,stop=12)

    def test_reject_symlink_private_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=fixture(Path(directory))
            symlink=Path(directory)/"alias.tsv"
            try: symlink.symlink_to(paths[0])
            except OSError: self.skipTest("symlinks unsupported")
            with self.assertRaisesRegex(ValueError,"symlinked"):
                audit(symlink,*paths[1:],start=10,stop=12)

    def test_reject_off_by_one_stop_frame(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError,"stop frame"):
                audit(*fixture(Path(directory)),start=10,stop=11)


if __name__=="__main__":
    unittest.main()
