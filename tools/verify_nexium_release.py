#!/usr/bin/env python3
"""Fail-closed verification of an official mutable NeXium GitHub release asset.

The GitHub release asset's API SHA-256, size, URL and publisher are checked
independently against the bytes fetched from the public release URL. This is
not an immutable commit pin: provenance is recorded on every run.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

OWNER="nexium-emu"
REPO="nexium-nightly"
TAG="nightly"
ASSET="nexium-linux-x86_64.tar.gz"
EXPECTED_HTML=f"https://github.com/{OWNER}/{REPO}/releases/tag/{TAG}"
EXPECTED_URL=f"https://github.com/{OWNER}/{REPO}/releases/download/{TAG}/{ASSET}"

def verify(release,archive):
    if not isinstance(release,dict):
        raise ValueError("GitHub release metadata is not an object")
    if (release.get("tag_name")!=TAG or release.get("draft") is not False
        or release.get("prerelease") is not True or
        release.get("html_url")!=EXPECTED_HTML):
        raise ValueError("not the expected official GitHub nightly release")
    assets=release.get("assets")
    if not isinstance(assets,list):
        raise ValueError("GitHub release assets not provided")
    matched=[x for x in assets if isinstance(x,dict) and x.get("name")==ASSET]
    if len(matched)!=1:
        raise ValueError("expected exactly one official Linux asset")
    asset=matched[0]
    digest=asset.get("digest")
    if (asset.get("browser_download_url")!=EXPECTED_URL or
        asset.get("state")!="uploaded" or
        not isinstance(digest,str) or
        not re.fullmatch(r"sha256:[0-9a-f]{64}",digest)):
        raise ValueError("GitHub did not publish valid asset URL/SHA-256")
    size=asset.get("size")
    if not isinstance(size,int) or not 40000000<=size<=350000000:
        raise ValueError("implausible NeXium Linux archive size")
    archive=Path(archive)
    if archive.stat().st_size!=size:
        raise ValueError("download length differs from GitHub release asset")
    h=hashlib.sha256()
    with archive.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    observed=h.hexdigest()
    if observed!=digest[7:]:
        raise ValueError("download SHA-256 differs from official GitHub digest")
    release_id=release.get("id")
    asset_id=asset.get("id")
    if not isinstance(release_id,int) or not isinstance(asset_id,int):
        raise ValueError("GitHub release/asset ID not provided")
    return dict(
        release_id=release_id,
        asset_id=asset_id,
        tag=TAG,
        published_at=str(release.get("published_at","unknown")),
        archive_sha256=observed,
        asset_size_bytes=size,
        digest_source="github_release_api",
        mutable_tag="yes",
    )

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--release-json",required=True,type=Path)
    parser.add_argument("--archive",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args()
    try:
        record=verify(json.loads(args.release_json.read_text("utf-8")),
                      args.archive)
    except (OSError,ValueError,TypeError,UnicodeError) as e:
        parser.exit(1,"NeXium release verification blocked: "+str(e)+"\n")
    args.out.write_text(
        "".join(f"nexium_{key}={value}\n" for key,value in record.items()),
        encoding="ascii")
    print("VERIFIED: official GitHub NeXium release asset SHA-256",
          record["archive_sha256"],"asset_id",record["asset_id"])

if __name__=="__main__":
    main()
