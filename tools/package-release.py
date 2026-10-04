#!/usr/bin/env python3
"""Package verified frontend and source downloads for a Multi Pop release."""

import argparse
import hashlib
import json
from pathlib import Path
import stat
import struct
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
THEME = "multi-pop-thor"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repository_files(root):
    # Git's inventory excludes local firmware inputs, credentials, media, and compiler output.
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
    )
    names = sorted(set(name.decode() for name in output.split(b"\0") if name))
    files = {}
    for name in names:
        path = root / name
        if path.is_symlink():
            raise ValueError("Release sources cannot contain symlinks: " + name)
        if path.is_file():
            files[name] = path
    return files


def verify_inputs(root, config, frontend, upstream_source, sdl_source):
    report = json.loads((root / THEME / "frontend/compatibility.json").read_text())
    expected = config["frontend"]["sha256"]
    if expected != report["artifact_sha256"] or sha256(frontend) != expected:
        raise ValueError("Frontend checksum does not match the verified release and compatibility report")
    if config["frontend_revision"] != report["frontend_revision"] or config["firmware_revision"] != report["firmware_revision"]:
        raise ValueError("Release source or firmware revision differs from the compatibility report")
    with frontend.open("rb") as source:
        header = source.read(20)
    if len(header) != 20 or header[:6] != b"\x7fELF\x02\x01" or struct.unpack("<H", header[18:20])[0] != 183:
        raise ValueError("Frontend must be a little-endian ARM64 ELF binary")
    for name, digest in config["build_inputs"].items():
        if sha256(root / name) != digest:
            raise ValueError("Frontend build input changed; verify a new frontend before packaging: " + name)
    for name, path in (("upstream_source", upstream_source), ("sdl_source", sdl_source)):
        if sha256(path) != config[name]["sha256"]:
            raise ValueError("Source archive checksum mismatch: " + name)
    if "pugixml_source" in config:
        path = upstream_source.parent / config["pugixml_source"]["asset"]
        if sha256(path) != config["pugixml_source"]["sha256"]:
            raise ValueError("Source archive checksum mismatch: pugixml_source")
    return report


def add_file(archive, name, data, executable=False):
    # Fixed metadata makes the same files produce the same download regardless of checkout times.
    entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    entry.create_system = 3
    entry.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
    entry.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(entry, data)


def package(root, output, frontend, upstream_source, sdl_source):
    config = json.loads((root / "frontend-build/release.json").read_text())
    verify_inputs(root, config, frontend, upstream_source, sdl_source)
    files = repository_files(root)
    theme_files = {name[len(THEME) + 1:]: path.read_bytes() for name, path in files.items()
                   if name.startswith(THEME + "/")}
    if not {"theme.xml", "README.md", "LICENSE", "LICENSING.md", "scripts/start_es_thor.sh"}.issubset(theme_files):
        raise ValueError("Installable theme is missing required files")
    theme_files["frontend/emulationstation"] = frontend.read_bytes()
    theme_files["scripts/update_theme.py"] = (root / "tools/install-multi-pop-theme.py").read_bytes()
    manifest = {name: hashlib.sha256(data).hexdigest() for name, data in sorted(theme_files.items())}
    output.mkdir(parents=True, exist_ok=True)
    ready = output / (THEME + "-rocknix-" + config["firmware_version"] + ".zip")
    source = output / (THEME + "-source.zip")
    with zipfile.ZipFile(ready, "w") as archive:
        for name, data in sorted(theme_files.items()):
            add_file(archive, THEME + "/" + name, data, name.endswith(".sh") or name == "frontend/emulationstation")
        add_file(archive, "install-manifest.json", (json.dumps(manifest, indent=2) + "\n").encode())
    with zipfile.ZipFile(source, "w") as archive:
        for name, path in files.items():
            add_file(archive, THEME + "-source/" + name, path.read_bytes(), name.endswith(".sh"))
        for name, path in (("upstream-source.tar.gz", upstream_source), ("SDL2-source.tar.gz", sdl_source)):
            add_file(archive, THEME + "-source/frontend-build/" + name, path.read_bytes())
        if "pugixml_source" in config:
            path = upstream_source.parent / config["pugixml_source"]["asset"]
            add_file(archive, THEME + "-source/frontend-build/pugixml-source.tar.gz", path.read_bytes())
    sums = output / "SHA256SUMS"
    sums.write_text("".join(sha256(path) + "  " + path.name + "\n" for path in (ready, source)))
    return ready, source, sums


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend", required=True, type=Path)
    parser.add_argument("--upstream-source", required=True, type=Path)
    parser.add_argument("--sdl-source", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    for path in package(ROOT, args.output, args.frontend, args.upstream_source, args.sdl_source):
        print(path)


if __name__ == "__main__":
    main()
