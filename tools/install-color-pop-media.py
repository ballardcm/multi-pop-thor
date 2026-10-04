#!/usr/bin/env python3
"""Review or install staged Color Pop game media while preserving current user data."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from urllib.parse import quote, urlparse


METADATA_KEYS = {"desc", "genre", "developer", "publisher", "releasedate"}
MEDIA_EXTENSIONS = {"screenshot": {".png"}, "video": {".mp4", ".webm", ".mkv", ".avi"}}


class ConcurrentChange(RuntimeError):
    pass


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def below(path, root):
    return path == root or root in path.parents


def canonical_rom(value, folder):
    path = Path(value)
    path = (path if path.is_absolute() else folder / path).resolve()
    if not below(path, folder) or path == folder:
        raise ValueError("ROM path escapes its declared system folder")
    return str(path)


def relative_file(stage, value):
    relative = PurePosixPath(value)
    if relative.is_absolute() or not relative.parts or any(part in {".", ".."} for part in relative.parts):
        raise ValueError("Staged file must have a safe relative path")
    result = (stage / str(relative)).resolve(strict=True)
    if not below(result, stage) or not result.is_file():
        raise ValueError("Staged file escapes its staging directory")
    return result


def load_manifest(stage, filename, rom_roots):
    manifest_path = relative_file(stage, filename)
    data = json.loads(manifest_path.read_text())
    files, games = data.get("files"), data.get("games")
    if not isinstance(files, dict) or not isinstance(games, list):
        raise ValueError("Manifest requires files and games")
    for relative, expected in files.items():
        if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise ValueError("Invalid staged SHA-256")
        if sha_file(relative_file(stage, relative)) != expected:
            raise ValueError("Staged checksum mismatch: " + relative)
    result, seen = [], set()
    for source in games:
        row = dict(source)
        folder = Path(row["folder"]).resolve(strict=True)
        gamelist = Path(row["gamelist"]).resolve(strict=True)
        if not any(below(folder, root) and folder != root for root in rom_roots):
            raise ValueError("System folder is outside the permitted ROM roots")
        if gamelist.parent != folder or gamelist.name != "gamelist.xml":
            raise ValueError("Game list is outside its declared system folder")
        row.update(folder=folder, gamelist=gamelist, romPath=canonical_rom(row["romPath"], folder))
        key = (str(gamelist), row["romPath"])
        if key in seen:
            raise ValueError("Manifest contains a duplicate ROM record")
        seen.add(key)
        metadata = row.get("metadata", {})
        if not isinstance(metadata, dict) or set(metadata) - METADATA_KEYS:
            raise ValueError("Only approved metadata fields may be installed")
        if any(not isinstance(value, str) for value in metadata.values()):
            raise ValueError("Metadata values must be strings")
        for kind in MEDIA_EXTENSIONS:
            if not row.get(kind):
                continue
            if row[kind] not in files:
                raise ValueError("Game media is absent from the file checksum manifest")
            source_path = relative_file(stage, row[kind])
            if source_path.suffix.lower() not in MEDIA_EXTENSIONS[kind]:
                raise ValueError("Unexpected media extension")
        result.append(row)
    return files, result


def text(element, key):
    return (element.findtext(key) or "").strip()


def blank_metadata(value):
    normalized = value.strip().casefold()
    if normalized in {"", "unknown", "none", "n/a", "not-a-date-time"}:
        return True
    return bool(normalized) and set(normalized) <= set("0.t :-/") and "0" in normalized


def media_path(value, folder):
    if not value:
        return None
    path = Path(value)
    return (path if path.is_absolute() else folder / path).resolve()


def owned_reference(kind, source, expected):
    directory = "screenshots" if kind == "screenshot" else "videos"
    return "./media/color-pop/" + directory + "/" + expected[:20] + source.suffix.lower()


def set_text(element, key, value, changes):
    old = element.find(key)
    if old is not None and (old.text or "") == value:
        return
    if old is None:
        old = ET.SubElement(element, key)
    old.text = value
    changes.append(key)


def parse_xml(payload):
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True, insert_pis=True))
    return ET.fromstring(payload, parser=parser)


def merge_xml(payload, rows, stage, files):
    root = parse_xml(payload)
    if root.tag != "gameList":
        raise ValueError("Unexpected game list root")
    folder = rows[0]["folder"]
    games = {}
    for game in root.findall("game"):
        path = text(game, "path")
        if not path:
            continue
        try:
            canonical = canonical_rom(path, folder)
        except ValueError:
            # An unrelated legacy game may refer outside the folder, and its XML must remain untouched.
            continue
        if canonical in games:
            raise ValueError("Current game list contains duplicate ROM paths")
        games[canonical] = game
    changes, copies, skipped = [], {}, Counter()
    for row in rows:
        game = games.get(row["romPath"])
        if game is None:
            skipped["rom_not_in_current_gamelist"] += 1
            continue
        keys = []
        image, thumbnail = text(game, "image"), text(game, "thumbnail")
        image_path, thumbnail_path = media_path(image, folder), media_path(thumbnail, folder)
        # A distinct existing cover and valid image indicate that the user already has separate preview media.
        separate_preview = image_path and thumbnail_path and image_path != thumbnail_path and image_path.is_file()
        if row.get("screenshot") and not separate_preview:
            source = relative_file(stage, row["screenshot"])
            reference = owned_reference("screenshot", source, files[row["screenshot"]])
            if not thumbnail and image and image_path != media_path(reference, folder):
                set_text(game, "thumbnail", image, keys)
            set_text(game, "image", reference, keys)
            copies[reference] = (source, files[row["screenshot"]])
        elif row.get("screenshot"):
            skipped["existing_separate_preview_preserved"] += 1
        if row.get("video") and not text(game, "video"):
            source = relative_file(stage, row["video"])
            reference = owned_reference("video", source, files[row["video"]])
            set_text(game, "video", reference, keys)
            copies[reference] = (source, files[row["video"]])
        elif row.get("video"):
            skipped["existing_video_preserved"] += 1
        for key, value in row.get("metadata", {}).items():
            if value.strip() and not blank_metadata(value) and blank_metadata(text(game, key)):
                set_text(game, key, value, keys)
        if keys:
            changes.append({"system": row["system"], "romPath": row["romPath"], "changedKeys": keys})
    output = ET.tostring(root, encoding="utf-8", xml_declaration=True) if changes else payload
    return output, changes, copies, skipped


def atomic_checked(path, payload, expected_hash):
    mode = path.stat().st_mode & 0o777
    descriptor, name = tempfile.mkstemp(prefix=".color-pop-media-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        # The frontend is stopped, but another worker may still have edited metadata since the snapshot was read.
        if sha_file(path) != expected_hash:
            raise ConcurrentChange("Game list changed before the atomic write")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def copy_owned(folder, reference, source, expected):
    destination = (folder / reference).resolve()
    if not below(destination, folder):
        raise ValueError("Owned media destination escapes its system folder")
    if destination.exists():
        if sha_file(destination) != expected:
            raise ValueError("Existing owned media has different pixels or bytes")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not below(destination.parent.resolve(), folder):
        raise ValueError("Owned media directory escaped through a symlink")
    descriptor, name = tempfile.mkstemp(prefix=".color-pop-copy-", dir=destination.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as output, source.open("rb") as input_stream:
            shutil.copyfileobj(input_stream, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        if sha_file(temporary) != expected:
            raise ValueError("Staged media changed while it was copied")
        os.chmod(temporary, 0o644)
        # Linking a completed temporary file refuses to overwrite any concurrently created user file.
        try:
            os.link(temporary, destination)
        except FileExistsError:
            if sha_file(destination) != expected:
                raise ConcurrentChange("Media destination appeared during installation")
    finally:
        temporary.unlink(missing_ok=True)


def backup_once(path, payload, state):
    backups = state / "media-v04-backups"
    backups.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha256(str(path).encode()).hexdigest()[:20]
    backup = backups / (key + ".gamelist.xml")
    try:
        with backup.open("xb") as stream:
            stream.write(payload)
        (backups / (key + ".source.json")).write_text(json.dumps({"gamelist": str(path), "sha256": hashlib.sha256(payload).hexdigest()}))
    except FileExistsError:
        pass
    return str(backup)


def http_json(base, route):
    with urllib.request.urlopen(base + route, timeout=8) as response:
        return response.status, json.loads(response.read(8 * 1024 * 1024))


def walk_apps(node):
    result = []
    app = node.get("app_id") or node.get("window_properties", {}).get("class")
    if app:
        result.append(str(app))
    for key in ("nodes", "floating_nodes"):
        for child in node.get(key, []):
            result.extend(walk_apps(child))
    return result


def idle_frontend(base, socket):
    status, current = http_json(base, "/runningGame")
    if status != 201 or current != {"msg": "NO GAME RUNNING"}:
        raise RuntimeError("An active game is present, so the frontend will stay running")
    status, idle = http_json(base, "/isIdle")
    if status != 200 or idle != [True]:
        raise RuntimeError("The frontend has another active background operation")
    process = subprocess.run(["swaymsg", "-s", socket, "-t", "get_tree", "-r"], check=True, capture_output=True, text=True, timeout=8)
    apps = walk_apps(json.loads(process.stdout))
    if not apps or any(app.casefold() != "emulationstation" for app in apps):
        raise RuntimeError("The display contains another application, so the frontend will stay running")
    subprocess.run(["systemctl", "is-active", "--quiet", "essway"], check=True, timeout=8)


def bulk_install(stage, files, rows, state, apply, base, socket):
    result = {"mode": "bulk", "applied": apply, "changes": [], "backups": {}, "skipped": {}, "retries": 0}
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["gamelist"]].append(row)
    stopped = False
    try:
        if apply:
            idle_frontend(base, socket)
            stopped = True
            subprocess.run(["systemctl", "stop", "essway"], check=True, timeout=30)
        skipped = Counter()
        for path, games in grouped.items():
            for attempt in range(3):
                # Reading after the service exits captures the user's latest favorites and play history.
                original = path.read_bytes()
                expected = hashlib.sha256(original).hexdigest()
                merged, changes, copies, omissions = merge_xml(original, games, stage, files)
                if not changes:
                    skipped.update(omissions)
                    break
                if apply:
                    result["backups"][str(path)] = backup_once(path, original, state)
                    for reference, (source, digest) in copies.items():
                        copy_owned(games[0]["folder"], reference, source, digest)
                    try:
                        atomic_checked(path, merged, expected)
                    except ConcurrentChange:
                        result["retries"] += 1
                        if attempt == 2:
                            raise
                        continue
                result["changes"].extend(changes)
                skipped.update(omissions)
                break
        result["skipped"] = dict(skipped)
    except Exception as error:
        result["error"] = str(error)
    finally:
        if stopped:
            try:
                subprocess.run(["systemctl", "start", "essway"], check=True, timeout=30)
                subprocess.run(["systemctl", "is-active", "--quiet", "essway"], check=True, timeout=8)
                result["frontendRestarted"] = True
            except Exception as error:
                result["frontendRestarted"] = False
                result["restartError"] = str(error)
    return result


def video_install(stage, files, rows, state, apply, base):
    result = {"mode": "videos", "applied": apply, "changes": [], "backups": {}, "skipped": {}}
    skipped, system_games = Counter(), {}
    for row in rows:
        if not row.get("video"):
            continue
        system = row["system"]
        if system not in system_games:
            status, games = http_json(base, "/systems/" + quote(system, safe="") + "/games")
            if status != 200 or not isinstance(games, list):
                raise RuntimeError("Cannot read the native game list")
            system_games[system] = {str(Path(game["path"]).resolve()): game["id"] for game in games}
        identifier = system_games[system].get(row["romPath"])
        if not identifier:
            skipped["rom_not_in_native_gamelist"] += 1
            continue
        route = "/systems/" + quote(system, safe="") + "/games/" + quote(identifier, safe="")
        status, current = http_json(base, route + "?localpaths=true")
        if status != 200 or str(Path(current["path"]).resolve()) != row["romPath"]:
            raise RuntimeError("Native game identity changed")
        if current.get("video"):
            skipped["existing_video_preserved"] += 1
            continue
        source = relative_file(stage, row["video"])
        target = row["folder"] / "videos" / (Path(current["path"]).stem + "-video" + source.suffix.lower())
        # ImportMedia chooses the standard video filename, so an unreferenced existing clip must also be protected.
        if not below(target.resolve(), row["folder"]):
            raise ValueError("Native video destination escapes its system folder")
        if target.exists():
            skipped["existing_unreferenced_video_preserved"] += 1
            continue
        if apply:
            result["backups"][str(row["gamelist"])] = backup_once(row["gamelist"], row["gamelist"].read_bytes(), state)
            status, fresh = http_json(base, route + "?localpaths=true")
            if fresh.get("video") or target.exists():
                skipped["video_changed_before_import"] += 1
                continue
            content_type = "video/" + source.suffix.lower().lstrip(".")
            request = urllib.request.Request(base + route + "/media/video", data=source.read_bytes(), headers={"Content-Type": content_type}, method="POST")
            with urllib.request.urlopen(request, timeout=60) as response:
                if response.status != 200:
                    raise RuntimeError("Native media import failed")
            status, updated = http_json(base, route + "?localpaths=true")
            if status != 200 or not updated.get("video") or sha_file(target) != files[row["video"]]:
                raise RuntimeError("Imported video verification failed")
        result["changes"].append({"system": system, "romPath": row["romPath"], "changedKeys": ["video"], "nativeDestination": str(target)})
    result["skipped"] = dict(skipped)
    return result


def metadata_install(rows, state, apply, base):
    result = {"mode": "metadata", "applied": apply, "changes": [], "backups": {}, "skipped": {}}
    skipped, system_games = Counter(), {}
    try:
        for row in rows:
            desired = {key: value for key, value in row.get("metadata", {}).items()
                       if key in METADATA_KEYS and value.strip() and not blank_metadata(value)}
            if not desired:
                continue
            system = row["system"]
            if system not in system_games:
                status, games = http_json(base, "/systems/" + quote(system, safe="") + "/games")
                if status != 200 or not isinstance(games, list):
                    raise RuntimeError("Cannot read the native game list")
                identifiers = {}
                for game in games:
                    path = str(Path(game["path"]).resolve())
                    if path in identifiers:
                        raise RuntimeError("Native game list contains duplicate ROM paths")
                    identifiers[path] = game["id"]
                system_games[system] = identifiers
            identifier = system_games[system].get(row["romPath"])
            if not identifier:
                skipped["rom_not_in_native_gamelist"] += 1
                continue
            route = "/systems/" + quote(system, safe="") + "/games/" + quote(identifier, safe="")
            status, current = http_json(base, route + "?localpaths=true")
            if status != 200 or str(Path(current["path"]).resolve()) != row["romPath"]:
                raise RuntimeError("Native game identity changed")
            pending = {key: value for key, value in desired.items() if blank_metadata(current.get(key, ""))}
            if not pending:
                skipped["existing_metadata_preserved"] += 1
                continue
            if apply:
                result["backups"][str(row["gamelist"])] = backup_once(row["gamelist"], row["gamelist"].read_bytes(), state)
                status, fresh = http_json(base, route + "?localpaths=true")
                if status != 200 or str(Path(fresh["path"]).resolve()) != row["romPath"]:
                    raise RuntimeError("Native game identity changed before metadata import")
                # The user may have filled a field during the backup, so only the freshly empty fields are sent.
                pending = {key: value for key, value in pending.items() if blank_metadata(fresh.get(key, ""))}
                if not pending:
                    skipped["metadata_changed_before_import"] += 1
                    continue
                payload = json.dumps(pending, ensure_ascii=False).encode("utf-8")
                request = urllib.request.Request(base + route, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(request, timeout=15) as response:
                    if response.status != 200:
                        raise RuntimeError("Native metadata import failed")
                status, updated = http_json(base, route + "?localpaths=true")
                if status != 200 or str(Path(updated["path"]).resolve()) != row["romPath"]:
                    raise RuntimeError("Native game identity changed after metadata import")
                if any(updated.get(key) != value for key, value in pending.items()):
                    raise RuntimeError("Imported metadata verification failed")
                for key in METADATA_KEYS - pending.keys():
                    if not blank_metadata(fresh.get(key, "")) and updated.get(key) != fresh.get(key):
                        raise RuntimeError("Existing metadata changed during import")
            result["changes"].append({"system": system, "romPath": row["romPath"], "changedKeys": list(pending)})
    except Exception as error:
        result["error"] = str(error)
    result["skipped"] = dict(skipped)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    parser.add_argument("--manifest", default="manifest.json")
    parser.add_argument("--apply", action="store_true", help="Apply the reviewed manifest; the default only reports proposed changes")
    parser.add_argument("--mode", choices=["bulk", "videos", "metadata"], default="bulk")
    parser.add_argument("--state", type=Path, default=Path("/storage/.config/color-pop-thor"))
    parser.add_argument("--http-base", default="http://127.0.0.1:1234")
    parser.add_argument("--sway-socket", default="/var/run/0-runtime-dir/sway-ipc.0.sock")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    parsed = urlparse(args.http_base)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("Native media calls must use the local frontend")
    if args.apply and os.geteuid() != 0:
        raise SystemExit("Device installation requires root")
    stage = args.stage.resolve(strict=True)
    roots = {Path("/roms").resolve(), Path("/storage/roms").resolve()}
    files, rows = load_manifest(stage, args.manifest, roots)
    if args.mode == "videos":
        result = video_install(stage, files, rows, args.state, args.apply, args.http_base)
    elif args.mode == "metadata":
        result = metadata_install(rows, args.state, args.apply, args.http_base)
    else:
        result = bulk_install(stage, files, rows, args.state, args.apply, args.http_base, args.sway_socket)
    result["stats"] = {"gamesChanged": len(result["changes"]), "fieldsChanged": dict(Counter(key for row in result["changes"] for key in row["changedKeys"]))}
    if args.report:
        args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in {"changes", "backups"}}, ensure_ascii=False))
    if result.get("error") or result.get("restartError"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
