"""Isolated anti-false-positive tests for NeXium guest text witness."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "vice_nexium", ROOT / "tools/audit_nexium_vice_witness.py")
auditor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(auditor)

def line(cycle=1):
    return (
        "VPD_ROMFREE_DEMO_WITNESS_V1 "
        f"cycle={cycle} frames=200 shots=11 hits=3 health=0 "
        "fnv=5947277116621119566 state_match=yes "
        "frame_submitted=yes original_game_proven=no\n"
    ).encode("ascii")


class NeXiumWitnessAuditTests(unittest.TestCase):
    def test_realistic_valid_cycles(self):
        for count in (1, 2, 4):
            with self.subTest(count=count):
                self.assertEqual(auditor.audit_lines(
                    b"".join(line(n) for n in range(1, count+1))), count)

    def test_reject_fabricated_wrong_or_corrupted_guest_logs(self):
        valid = line()
        mutations = (
            b"",
            valid[:-1],
            valid.replace(b"state_match=yes", b"state_match=no"),
            valid.replace(b"frames=200", b"frames=199"),
            valid.replace(b"shots=11", b"shots=12"),
            valid.replace(b"hits=3", b"hits=2"),
            valid.replace(b"fnv=5947277116621119566", b"fnv=0"),
            valid.replace(b"frame_submitted=yes", b"frame_submitted=no"),
            valid.replace(b"original_game_proven=no", b"original_game_proven=yes"),
            valid.replace(b"cycle=1", b"cycle=2"),
            valid.replace(b"cycle=1", b"cycle=01"),
            valid.replace(b" cycle=1", b" cycle=1 cycle=1"),
            valid.replace(b" state_match=yes", b""),
            valid.replace(b"frames=200 shots=11", b"shots=11 frames=200"),
            valid.replace(b"\n", b"\r\n"),
            valid.replace(b"\n", b"\x00\n"),
            valid + valid,  # second cycle is not sequenced
            b"".join(line(n) for n in range(1, 6))
        )
        for idx, mutated in enumerate(mutations):
            with self.subTest(index=idx), self.assertRaises(
                (ValueError, UnicodeError)
            ):
                auditor.audit_lines(mutated)

    def test_missing_guest_file_cannot_pass_even_if_host_has_logs(self):
        checksum = "a" * 64
        proof = (
            "nexium_release_id=127800\n"
            "nexium_asset_id=334455\n"
            "nexium_tag=nightly\n"
            "nexium_published_at=2026-10-20T08:00:00Z\n"
            f"nexium_archive_sha256={checksum}\n"
            "nexium_asset_size_bytes=98765432\n"
            "nexium_digest_source=github_release_api\n"
            "nexium_mutable_tag=yes\n"
        )
        log = ("VERIFIED: official GitHub NeXium release asset SHA-256 "
               f"{checksum} asset_id 334455\n")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for name in ("emulator-stdout.txt", "vulkan.txt"):
                (p/name).write_text("OK\n")
            (p/"metadata.txt").write_text("runner=x86_64\n" + proof)
            (p/"emulator-release-attestation.txt").write_text(proof)
            (p/"emulator-sha256.txt").write_text(log)
            with self.assertRaisesRegex(ValueError, "no actual NeXium guest"):
                auditor.audit_evidence(p)
            (p/"guest-demo-witness.txt").write_bytes(line())
            self.assertEqual(auditor.audit_evidence(p), 1)
            self.assertEqual(auditor.audit_release_evidence(p), checksum)
            bad_log=log.replace("asset_id 334455", "asset_id 334456")
            (p/"emulator-sha256.txt").write_text(bad_log)
            with self.assertRaisesRegex(ValueError, "log mismatch"):
                auditor.audit_evidence(p)
            (p/"emulator-sha256.txt").write_text(log)
            (p/"emulator-release-attestation.txt").write_text(
                proof.replace("nexium_archive_sha256="+checksum,
                              "nexium_archive_sha256="+"b"*64))
            with self.assertRaisesRegex(ValueError, "metadata does not match"):
                auditor.audit_evidence(p)
            (p/"emulator-release-attestation.txt").write_text(proof)
            (p/"metadata.txt").write_text("runner=x86_64\n")
            with self.assertRaisesRegex(ValueError, "metadata does not match"):
                auditor.audit_evidence(p)
            (p/"metadata.txt").write_text("runner=x86_64\n"+proof)
            (p/"emulator-release-attestation.txt").write_text(
                proof.replace("nexium_digest_source=github_release_api",
                              "nexium_digest_source=unknown"))
            with self.assertRaisesRegex(ValueError, "metadata does not match"):
                auditor.audit_evidence(p)
            (p/"emulator-release-attestation.txt").unlink()
            with self.assertRaisesRegex(ValueError, "attestation absent"):
                auditor.audit_evidence(p)


if __name__ == "__main__":
    unittest.main()
