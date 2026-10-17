#!/usr/bin/env python3
"""Package verified frontend and source downloads for a Multi Pop release."""

import argparse
import hashlib
import json
from pathlib import Path
import re
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


# These match the shapes of ScreenScraper, RetroAchievements and TheGamesDB keys as string literals in a binary.
SERVICE_KEY_PATTERNS = (
    rb"devid=[^&\x00]+&devpassword=[^&\x00]+",
    rb"\x00z=[^&\x00]+&y=[^&\x00]+\x00",
    rb"\x00[0-9a-f]{64}\x00",
)


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
    # Service keys come from each Thor at runtime; a binary with compiled-in keys must never be packaged for download.
    if any(re.search(pattern, frontend.read_bytes()) for pattern in SERVICE_KEY_PATTERNS):
        raise ValueError("Frontend contains compiled-in service keys; build it without them before packaging")
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


def release_version(root):
    # Main only changes through merges, so its first-parent commit count rises with every release and never repeats.
    # A PR build checks out the merge it would make, so its preview carries the number that merge will publish.
    return int(subprocess.check_output(["git", "rev-list", "--count", "--first-parent", "HEAD"], cwd=root))


def add_file(archive, name, data, executable=False):
    # Fixed metadata makes the same files produce the same download regardless of checkout times.
    entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    entry.create_system = 3
    entry.external_attr = (stat.S_IFREG | (0o755 if executable else 0o644)) << 16
    entry.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(entry, data)


def package(root, output, frontend, upstream_source, sdl_source, version):
    if not isinstance(version, int) or version < 1:
        raise ValueError("Release version must be a positive integer")
    config = json.loads((root / "frontend-build/release.json").read_text())
    verify_inputs(root, config, frontend, upstream_source, sdl_source)
    files = repository_files(root)
    theme_files = {name[len(THEME) + 1:]: path.read_bytes() for name, path in files.items()
                   if name.startswith(THEME + "/")}
    if not {"theme.xml", "README.md", "LICENSE", "LICENSING.md", "scripts/start_es_thor.sh", "version.xml"}.issubset(theme_files):
        raise ValueError("Installable theme is missing required files")
    theme_files["frontend/emulationstation"] = frontend.read_bytes()
    theme_files["scripts/update_theme.py"] = (root / "tools/install-multi-pop-theme.py").read_bytes()
    # The automatic updater compares this number so it never replaces an installation with an older release.
    theme_files["version.json"] = (json.dumps({"version": version}) + "\n").encode()
    # The theme shows the same number under its name.
    theme_files["version.xml"] = re.sub(rb"<multiPopVersion>[^<]*</multiPopVersion>",
                                        b"<multiPopVersion>%d</multiPopVersion>" % version,
                                        theme_files["version.xml"])
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
    parser.add_argument("--version", type=int, help="release number; defaults to the first-parent commit count")
    args = parser.parse_args()
    version = args.version if args.version is not None else release_version(ROOT)
    for path in package(ROOT, args.output, args.frontend, args.upstream_source, args.sdl_source, version):
        print(path)


if __name__ == "__main__":
    main()
