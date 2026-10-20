#!/usr/bin/env python3
"""Offline adversarial tests; NEVER fetch mutable binaries for fixtures."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from verify_nexium_release import verify,ASSET,EXPECTED_HTML,EXPECTED_URL

class ReleaseDigestTests(unittest.TestCase):
    def test_asset_digest_and_strict_provenance(self):
        data=b"x"*(42*1024*1024)
        sha=hashlib.sha256(data).hexdigest()
        release=dict(
            id=800,tag_name="nightly",draft=False,prerelease=True,
            html_url=EXPECTED_HTML,published_at="2026-10-20T07:00:00Z",
            assets=[dict(id=801,name=ASSET, state="uploaded",
                         size=len(data),digest="sha256:"+sha,
                         browser_download_url=EXPECTED_URL)],
        )
        with tempfile.TemporaryDirectory() as temp:
            archive=Path(temp)/ASSET
            archive.write_bytes(data)
            self.assertEqual(verify(release,archive)["archive_sha256"],sha)
            scenarios=[
                ("wrong tag",lambda r:r.update(tag_name="surprise")),
                ("draft",lambda r:r.update(draft=True)),
                ("wrong publisher",lambda r:r.update(
                    html_url="https://github.com/attacker/repo/releases/tag/nightly")),
                ("missing digest",lambda r:r["assets"][0].pop("digest")),
                ("wrong digest",lambda r:r["assets"][0].update(
                    digest="sha256:"+"a"*64)),
                ("wrong URL",lambda r:r["assets"][0].update(
                    browser_download_url="https://attacker.example/a.tar.gz")),
                ("not uploaded",lambda r:r["assets"][0].update(state="new")),
                ("incorrect size",lambda r:r["assets"][0].update(size=5)),
                ("duplicate asset",lambda r:r["assets"].append(
                    r["assets"][0].copy())),
                ("no asset id",lambda r:r["assets"][0].pop("id")),
            ]
            for title,mutate in scenarios:
                with self.subTest(title=title):
                    modified=json.loads(json.dumps(release))
                    mutate(modified)
                    with self.assertRaises((ValueError,KeyError)):
                        verify(modified,archive)

if __name__=="__main__":
    unittest.main()
