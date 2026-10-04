#!/usr/bin/env python3
"""Prepare and build the pinned Multi Pop frontend against a Thor's runtime."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_archive(spec, bundled, destination):
    if not destination.exists():
        if bundled.is_file():
            shutil.copyfile(bundled, destination)
        else:
            request = urllib.request.Request(spec["url"], headers={"User-Agent": "MultiPopThor-builder"})
            with urllib.request.urlopen(request, timeout=60) as source, destination.open("wb") as target:
                shutil.copyfileobj(source, target)
    if digest(destination) != spec["sha256"]:
        raise ValueError("Pinned source checksum mismatch: " + destination.name)
    return destination


def extract_sources(archive_path, destination, only_directory=None):
    # Reject special members before extraction so source archives cannot escape private build storage.
    with tarfile.open(archive_path) as archive:
        members = archive.getmembers()
        for member in members:
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Unsafe source archive member: " + member.name)
        roots = {Path(member.name).parts[0] for member in members}
        if len(roots) != 1:
            raise ValueError("Source archive must contain one top-level directory")
        root = roots.pop()
        if only_directory:
            prefix = root + "/" + only_directory
            members = [member for member in members if member.name == prefix or member.name.startswith(prefix + "/")]
        for member in members:
            if not (member.isfile() or member.isdir()):
                raise ValueError("Unsafe source archive member: " + member.name)
        archive.extractall(destination, members=members)
    return destination / root


def run(command, **kwargs):
    subprocess.run(command, check=True, **kwargs)


def build(args):
    for command in ("docker", "ssh", "patch"):
        if shutil.which(command) is None:
            raise ValueError("Required tool is missing: " + command)
    config = json.loads((ROOT / "frontend-build/release.json").read_text())
    work = args.work.resolve()
    if work.exists():
        raise ValueError("Use a new work directory so stale sources cannot enter the build: " + str(work))
    if args.integration_env and not args.integration_env.is_file():
        raise ValueError("Integration environment file does not exist")
    private = work / "private"
    private.mkdir(parents=True)
    downloads = private / "downloads"
    downloads.mkdir()
    upstream = source_archive(config["upstream_source"], ROOT / "frontend-build/upstream-source.tar.gz", downloads / "upstream.tar.gz")
    sdl = source_archive(config["sdl_source"], ROOT / "frontend-build/SDL2-source.tar.gz", downloads / "sdl.tar.gz")
    source = extract_sources(upstream, work)
    expected_source = work / ("emulationstation-next-" + config["frontend_revision"])
    if source != expected_source:
        source.rename(expected_source)
    for name in ("thor-popup-placement.patch", "thor-game-paging.patch"):
        run(["patch", "-p1", "--batch", "--forward", "-i", str(ROOT / "multi-pop-thor/frontend" / name)], cwd=expected_source)
    # SDL's unrelated platform projects contain symlinks; the compiler needs only the public headers.
    sdl_root = extract_sources(sdl, private, only_directory="include")
    headers = private / "SDL2-headers"
    headers.mkdir()
    for header in (sdl_root / "include").glob("*.h"):
        shutil.copy2(header, headers / header.name)
    pugixml = source_archive(config["pugixml_source"], ROOT / "frontend-build/pugixml-source.tar.gz", downloads / "pugixml.tar.gz")
    pugixml_root = extract_sources(pugixml, private)
    shutil.copytree(pugixml_root, expected_source / "external/pugixml", dirs_exist_ok=True)
    ssh = ["ssh", "-o", "BatchMode=yes"]
    for option in args.ssh_option:
        ssh.extend(["-o", option])
    ssh.append(args.target)
    # A firmware-specific build must collect its libraries from the actual supported device.
    with (ROOT / "frontend-build/read-target-libs.py").open("rb") as script, (private / "target-libs.tar.gz").open("wb") as archive:
        run(ssh + ["python3 -"], stdin=script, stdout=archive)
    with tarfile.open(private / "target-libs.tar.gz") as archive:
        for member in archive.getmembers():
            if not member.isfile() or "/" in member.name or member.name in (".", ".."):
                raise ValueError("Unsafe target-library archive member")
        (private / "target-libs").mkdir()
        archive.extractall(private / "target-libs")
    for name in ("build-frontend.sh", "verify-artifact.sh"):
        shutil.copy2(ROOT / "frontend-build" / name, work / name)
    image = "multi-pop-frontend-builder:" + config["firmware_version"]
    run(["docker", "build", "--platform", "linux/arm64", "--tag", image, str(ROOT / "frontend-build")])
    command = ["docker", "run", "--rm", "--network", "none", "--platform", "linux/arm64"]
    if args.integration_env:
        command.extend(["--env-file", str(args.integration_env.resolve())])
    command.extend(["--volume", str(work) + ":/work", image, "sh", "-c", "sh /work/build-frontend.sh && sh /work/verify-artifact.sh"])
    log = args.log.expanduser().resolve()
    with log.open("wb") as output:
        run(command, stdout=output, stderr=subprocess.STDOUT)
    binary = work / "artifacts/emulationstation"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, args.output)
    args.output.chmod(0o755)
    report = {
        "artifact_sha256": digest(args.output), "artifact_bytes": args.output.stat().st_size,
        "frontend_revision": config["frontend_revision"], "firmware_revision": config["firmware_revision"],
        "target": args.target, "integration_configuration_supplied": bool(args.integration_env),
        "target_loader_and_help_checks_passed": True, "device_validation_pending": True,
    }
    args.output.with_suffix(".build.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Built frontend:", args.output)
    print("Build log:", log)
    print("Validate on the matching firmware before distributing a new frontend.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", required=True, help="SSH destination for a Thor running the supported firmware")
    parser.add_argument("--ssh-option", action="append", default=[], help="SSH -o setting, for example ControlPath=/path/to/socket")
    parser.add_argument("--integration-env", type=Path, help="Optional locally held, authorized upstream integration settings")
    parser.add_argument("--work", type=Path, default=ROOT / "frontend-build/private/build-your-own")
    parser.add_argument("--output", type=Path, default=ROOT / "multi-pop-thor/frontend/emulationstation")
    parser.add_argument("--log", type=Path, default=Path.home() / "multi-pop-frontend-build.log")
    args = parser.parse_args()
    try:
        build(args)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + "\n")


if __name__ == "__main__":
    main()
