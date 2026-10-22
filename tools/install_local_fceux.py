#!/usr/bin/env python3
"""Offline FCEUX 2.6.x executable bootstrap from a verified Actions ZIP.

The ZIP must contain official Ubuntu FCEUX/liblua DEB packages and
SHA256SUMS, as exported by the existing ROM-free FCEUX workflow.
Never include or install a ROM, FM2 movie or captured source image.
No network is required. This uses the OS's preinstalled Qt/SDL libs.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import zipfile

HEX64=re.compile(r"[0-9a-f]{64}\Z")
PKG=re.compile(r"(fceux|liblua5\.1-0)_[^/]+_amd64\.deb\Z")

def unpack_verified(archive:Path,destination:Path)->dict:
    if archive.is_symlink() or not archive.is_file():
        raise ValueError("FCEUX offline ZIP unavailable or symlinked")
    if archive.stat().st_size>60_000_000:
        raise ValueError("unexpectedly large executable ZIP")
    with zipfile.ZipFile(archive) as source:
        names=source.namelist()
        if len(names)!=len(set(names)) or any(
            "/" in n or "\\" in n or n.startswith(".") for n in names
        ):
            raise ValueError("unsafe ZIP path or repeated member")
        packages=[n for n in names if PKG.fullmatch(n)]
        if (len(packages)!=2 or
            not any(x.startswith("fceux_") for x in packages) or
            not any(x.startswith("liblua5.1-0_") for x in packages) or
            set(names)!={*packages,"SHA256SUMS","package-info.txt"}):
            raise ValueError("incomplete or unsafe FCEUX runtime archive")
        lines=source.read("SHA256SUMS").decode("ascii").splitlines()
        digests={}
        for line in lines:
            match=re.fullmatch(r"([0-9a-f]{64})\s+\*?\./([^/ ]+)",line)
            if not match or match[2] in digests:
                raise ValueError("invalid or repeated package SHA256 record")
            digests[match[2]]=match[1]
        if set(digests)!=set(packages):
            raise ValueError("checksums do not cover precisely both packages")
        for name in packages:
            content=source.read(name)
            if hashlib.sha256(content).hexdigest()!=digests[name]:
                raise ValueError("FCEUX runtime package SHA256 mismatch")
            target=destination/name
            target.write_bytes(content)
    return {"packages":packages,"checksums_verified":True}

def install(archive:Path,prefix:Path,bin_dir:Path)->Path:
    if shutil.which("dpkg-deb") is None:
        raise ValueError("dpkg-deb is required on the target Linux")
    if os.uname().machine!="x86_64":
        raise ValueError("this Actions archive contains amd64 packages")
    prefix=prefix.expanduser().resolve()
    bin_dir=bin_dir.expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix="fceux-verified-") as tmp:
        content=unpack_verified(archive,Path(tmp))
        dest=prefix/"runtime"
        dest.mkdir(parents=True,exist_ok=True)
        for name in content["packages"]:
            src=Path(tmp)/name
            architecture=subprocess.run(
                ["dpkg-deb","-f",str(src),"Architecture"],
                capture_output=True,text=True,check=True).stdout.strip()
            if architecture!="amd64":
                raise ValueError("unexpected FCEUX dependency architecture")
            subprocess.run(["dpkg-deb","-x",str(src),str(dest)],check=True)
    executable=dest/"usr/games/fceux"
    lua=dest/"usr/lib/x86_64-linux-gnu/liblua5.1.so.0"
    if not executable.is_file() or not os.access(executable,os.X_OK) or not lua.is_file():
        raise ValueError("executable FCEUX or Lua library missing after extraction")
    if shutil.which("ldd") is None:
        raise ValueError("ldd required to check runtime linkage")
    env={**os.environ,
         "LD_LIBRARY_PATH":str(lua.parent)+
         (":"+os.environ["LD_LIBRARY_PATH"] if os.environ.get("LD_LIBRARY_PATH") else "")}
    result=subprocess.run(["ldd",str(executable)],
                          env=env,capture_output=True,text=True,check=True)
    if "not found" in result.stdout:
        raise ValueError("FCEUX has missing SDL/Qt system libraries")
    bin_dir.mkdir(parents=True,exist_ok=True)
    wrapper=bin_dir/"fceux"
    if wrapper.is_symlink():
        raise ValueError("refuse to replace a symlink as FCEUX executable")
    data=(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        "runtime="+shlex.quote(str(dest))+"\n"
        'export LD_LIBRARY_PATH="$runtime/usr/lib/x86_64-linux-gnu'
        '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"\n'
        'exec "$runtime/usr/games/fceux" "$@"\n'
    )
    wrapper.write_text(data,encoding="utf8")
    wrapper.chmod(0o755)
    check=subprocess.run([str(wrapper),"--help"],capture_output=True,
                         text=True,timeout=20)
    if "FCEUX" not in check.stdout+check.stderr:
        raise ValueError("installed executable failed to launch")
    return wrapper

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--artifact-zip",required=True,type=Path)
    p.add_argument("--prefix",default=Path.home()/".local/share/vice-fceux",type=Path)
    p.add_argument("--bin-dir",default=Path.home()/".local/bin",type=Path)
    args=p.parse_args()
    install(args.artifact_zip,args.prefix,args.bin_dir)
    print("VPD_FCEUX_OFFLINE_EXECUTABLE_PASS"
          " version=2.6.x installed=yes"
          " sha256_packages_verified=yes original_assets=no")
if __name__=="__main__":
    main()
