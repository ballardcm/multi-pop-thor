#!/usr/bin/env python3
"""Stage public Libretro gameplay screenshots without changing device metadata."""

import argparse
import hashlib
import html
import io
import json
import re
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOT = "https://thumbnails.libretro.com/"
PLATFORMS = {
    "fbn": "FBNeo - Arcade Games",
    "atari2600": "Atari - 2600",
    "atari5200": "Atari - 5200",
    "atari7800": "Atari - 7800",
    "atarilynx": "Atari - Lynx",
    "atarijaguar": "Atari - Jaguar",
    "wonderswancolor": "Bandai - WonderSwan Color",
    "colecovision": "Coleco - ColecoVision",
    "c64": "Commodore - 64",
    "intellivision": "Mattel - Intellivision",
    "xbox": "Microsoft - Xbox",
    "pcengine": "NEC - PC Engine - TurboGrafx 16",
    "pcenginecd": "NEC - PC Engine CD - TurboGrafx-CD",
    "nes": "Nintendo - Nintendo Entertainment System",
    "gb": "Nintendo - Game Boy",
    "snes": "Nintendo - Super Nintendo Entertainment System",
    "n64": "Nintendo - Nintendo 64",
    "gbc": "Nintendo - Game Boy Color",
    "gamecube": "Nintendo - GameCube",
    "gba": "Nintendo - Game Boy Advance",
    "nds": "Nintendo - Nintendo DS",
    "3ds": "Nintendo - Nintendo 3DS",
    "virtualboy": "Nintendo - Virtual Boy",
    "atomiswave": "Atomiswave",
    "sg-1000": "Sega - SG-1000",
    "mastersystem": "Sega - Master System - Mark III",
    "genesis": "Sega - Mega Drive - Genesis",
    "gamegear": "Sega - Game Gear",
    "segacd": "Sega - Mega-CD - Sega CD",
    "saturn": "Sega - Saturn",
    "sega32x": "Sega - 32X",
    "segamodel3": "MAME",
    "dreamcast": "Sega - Dreamcast",
    "naomi": "Sega - Naomi",
    "vectrex": "GCE - Vectrex",
    "neogeo": "SNK - Neo Geo",
    "ngpc": "SNK - Neo Geo Pocket Color",
    "ps2": "Sony - PlayStation 2",
    "ps3": "Sony - PlayStation 3",
}
REGIONS = {
    "u": "usa", "usa": "usa", "us": "usa",
    "e": "europe", "europe": "europe", "eu": "europe",
    "j": "japan", "japan": "japan", "jp": "japan", "jap": "japan", "jpn": "japan",
    "eur": "europe", "euro": "europe", "aus": "australia", "asi": "asia",
    "kor": "korea", "exp": "world", "export": "world",
    "world": "world", "australia": "australia", "brazil": "brazil",
    "korea": "korea", "korean": "korea", "china": "china",
    "taiwan": "taiwan", "asia": "asia", "canada": "canada",
    "france": "france", "germany": "germany", "spain": "spain",
    "italy": "italy", "sweden": "sweden", "uk": "uk",
}
ROM_EXTENSIONS = re.compile(
    r"\.(?:zip|7z|a26|a52|a78|lnx|rom|pce|chd|cue|iso|nes|gb|gbc|sfc|smc|n64|z64|v64|"
    r"gcz|rvz|gba|nds|cci|3ds|vb|sg|sms|md|bin|gg|32x|cdi|ps3|png)$", re.I)
# These aliases use verified filenames from the relevant public platform index.
EXPLICIT_RELEASES = {
    "pcengine": {"Bonk III - Bonk's Big Adventure": "Bonk 3 - Bonk's Big Adventure (USA).png"},
    "ngpc": {
        "Baseball Stars Color": "Baseball Stars Color - Pocket Sports Series (World) (En,Ja).png",
        "Fatal Fury F-Contact": "Fatal Fury F-Contact - Pocket Fighting Series (World) (En,Ja).png",
        "King of Fighters R-2": "King of Fighters R-2 - Pocket Fighting Series (World) (En,Ja).png",
    },
    "saturn": {
        "Shining Force III - Scenario 1": "Shining Force III (USA).png",
        "Saturn Bomberman": "Saturn Bomberman (USA) (1S).png",
    },
    "gba": {
        "WarioWare Inc.": "WarioWare, Inc. - Mega Microgame$! (USA).png",
        "Mario Tennis Advance - Power Tour": "Mario Tennis - Power Tour (USA, Australia) (En,Fr,De,Es,It).png",
    },
    "3ds": {
        "Fire_Emblem_Echoes US Decrypted": "Fire Emblem Echoes - Shadows of Valentia (USA) (En,Fr,Es).png",
        "Puzzle.and.Dragons.Z.plus.Puzzle.and.Dragons.Super.Mario.Bros.Edition":
            "Puzzle _ Dragons Z + Puzzle _ Dragons Super Mario Bros. Edition (Europe).png",
        "Shovel.Knight.USA.3DS-BigBlueBox": "Shovel Knight (USA).png",
        "Pokemon Sun Multi 3DS Descrypted_Ziperto.com": "Pokemon Sun (USA) (En,Ja,Fr,De,Es,It,Zh,Ko).png",
    },
    "n64": {
        "007 - GoldenEye": "GoldenEye 007 (USA).png",
        "Wave Race 64": "Wave Race 64 - Kawasaki Jet Ski (USA) (Rev 1).png",
    },
    "neogeo": {
        "Metal Slug": "Metal Slug - Super Vehicle-001.png",
        "Super Sidekicks 3 - The Next Glory / Tokuten Ou 3 - Eikou e no Chousen":
            "Super Sidekicks 3 - The Next Glory _ Tokuten Ou 3 - eikou e no michi.png",
    },
    "xbox": {
        "Forza Motorsport-1": "Forza Motorsport (USA).png",
        "Jet Set Radio Future-1": "Jet Set Radio Future (USA).png",
    },
    "segacd": {
        "Flashback-The_Quest_For_Identity(US-Genesis)": "Flashback - The Quest for Identity (USA).png",
        "Keio_Flying_Squadron(US-Genesis)": "Keio Flying Squadron (USA).png",
        "Panic! (1994)(Data East)(NTSC)(US)[SEGAT13015RE R1J]": "Panic! (USA).png",
        "Shining Force CD (USA) (Alt)": "Shining Force CD (USA).png",
    },
    "naomi": {
        "Gun Spike (JPN) / Cannon Spike (USA, EXP, KOR, AUS)": "Cannon Spike _ Gun Spike.png",
        "Marvel vs. Capcom 2": "Marvel Vs. Capcom 2_ New Age of Heroes (Export, Korea, Rev A).png",
        "Moero Justice Gakuen (JPN) / Project Justice (USA, EXP, KOR, AUS)":
            "Project Justice _ Moero! Justice Gakuen (Rev A).png",
        "House of the Dead 2": "The House of the Dead 2 (USA).png",
    },
}


def json_save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def request_bytes(url, attempts=3):
    if not url.startswith(PUBLIC_ROOT):
        raise ValueError("Only public Libretro thumbnail URLs are permitted")
    last = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "ColorPopThor-media/0.4"})
            with urlopen(request, timeout=30) as response:
                return response.read(16 * 1024 * 1024)
        except (HTTPError, URLError, TimeoutError, OSError) as error:
            last = error
            if isinstance(error, HTTPError) and error.code in (403, 404):
                break
            time.sleep(0.6 * (attempt + 1))
    raise RuntimeError(str(last))


def fetch_index(platform, cache_root):
    cache = cache_root / (hashlib.sha256(platform.encode()).hexdigest()[:20] + ".json")
    if cache.exists():
        saved = json.loads(cache.read_text())
        return saved["names"]
    url = PUBLIC_ROOT + quote(platform, safe="") + "/Named_Snaps/"
    document = request_bytes(url).decode("utf-8")
    names = sorted(set(unquote(html.unescape(name)) for name in
                       re.findall(r'href="([^"?]+\.png)"', document, re.I)))
    names = [name for name in names if "/" not in name and name.lower().endswith(".png")]
    json_save(cache, {"platform": platform, "url": url, "names": names})
    print(f"Index ready: {platform} ({len(names)} gameplay images)", flush=True)
    return names


def punctuation_key(value):
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(character for character in value if not unicodedata.combining(character))
    # Libretro replaces filename punctuation such as ampersands with underscores.
    value = value.replace("&", " ").replace("’", "'").replace("'", "")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def stem(value):
    if value.startswith(("/", "./", "../")):
        value = Path(value).name
    return ROM_EXTENSIONS.sub("", value)


def groups(value):
    return re.findall(r"\(([^)]*)\)", value)


def game_regions(value):
    result = set()
    for group in groups(value):
        if group.casefold() in {"ue", "uj", "ju", "je", "ej", "jue"}:
            result.update(REGIONS[letter] for letter in group.casefold())
        for part in group.casefold().split(","):
            if part.strip() in REGIONS:
                result.add(REGIONS[part.strip()])
    return result


def removable_group(group):
    lower = group.casefold().strip()
    tokens = [token.strip() for token in lower.split(",")]
    if tokens and all(token in REGIONS for token in tokens):
        return True
    if lower in {"ue", "uj", "ju", "je", "ej", "jue"}:
        return True
    if re.fullmatch(r"(?:[a-z]{2})(?:,[a-z]{2})*", lower):
        return True
    if re.fullmatch(r"(?:rev(?:ision)?|ver(?:sion)?|v)\s*[a-z0-9.]+", lower):
        return True
    if re.fullmatch(r"m\d+|\d+[msr]|set\s+\d+", lower):
        return True
    if re.fullmatch(r"(?:en|fr|de|es|it|nl|ja|ko|zh|pt|sv|no|da|fi|pl){2,}", lower):
        return True
    if lower in {"english", "en", "translated", "sgb enhanced", "gb compatible", "bigbluebox", "powerup", "unl", "rumble version", "eshop"}:
        return True
    # Disc identifiers and serial numbers describe a release, not a different game.
    if re.fullmatch(r"(?:disc|disk|cd)\s*\d+(?:\s*of\s*\d+)?", lower):
        return True
    if re.fullmatch(r"[a-z]{2,6}[- ]?\d{3,6}", lower):
        return True
    return False


def title_key(value):
    value = stem(value)
    value = re.sub(r"\(([^)]*)\)", lambda m: "" if removable_group(m[1]) else m[0], value)
    value = re.sub(r"\[(?:!|[cubofahpt]\d*|t\+[^\]]*)\]", "", value, flags=re.I)
    value = re.sub(r"\s+Decrypted$", "", value, flags=re.I).strip()
    value = re.sub(r"\s+(?:EUR|EU|US|Multi)$", "", value, flags=re.I).strip()
    # No-Intro moves articles after commas, while display names usually put them first.
    value = re.sub(r"^(.+?),\s*(The|A|An)(\s*-\s*.+)?$", r"\2 \1\3", value, flags=re.I)
    return punctuation_key(value)


def build_aliases():
    result = defaultdict(dict)
    for system, entries in EXPLICIT_RELEASES.items():
        result[system].update({title_key(title): source for title, source in entries.items()})
    files = [ROOT / "wider-additions/artwork.json", ROOT / "wider-additions/homebrew-artwork.json"]
    for path in files:
        if not path.exists():
            continue
        for entry in json.loads(path.read_text()):
            source = entry.get("source", "")
            parsed = urlparse(source)
            if parsed.netloc != "raw.githubusercontent.com" or "/Named_Boxarts/" not in parsed.path:
                continue
            pieces = parsed.path.split("/")
            if len(pieces) < 6 or pieces[1] != "libretro-thumbnails":
                continue
            repository = pieces[2]
            # This explicit provenance links a translated display title to its original release.
            for system, platform in PLATFORMS.items():
                if platform.replace(" ", "_") == repository:
                    result[system][title_key(entry["title"])] = unquote(pieces[-1])
    return result


class MatchingIndex:
    def __init__(self, names):
        self.exact = {name.casefold(): name for name in names}
        self.titles = defaultdict(list)
        self.compact = defaultdict(list)
        for name in names:
            self.titles[title_key(name)].append(name)
            self.compact[title_key(name).replace(" ", "")].append(name)

    def match(self, game, aliases):
        candidates = [stem(game["path"]) + ".png", stem(game.get("name", "")) + ".png"]
        for candidate in candidates:
            if candidate.casefold() in self.exact:
                return self.exact[candidate.casefold()], "exact_release"
        for value in [game.get("name", ""), game["path"]]:
            alias = aliases.get(title_key(value))
            if alias and alias.casefold() in self.exact:
                return self.exact[alias.casefold()], "explicit_original_release_alias"
        requested_regions = game_regions(game["path"]) | game_regions(game.get("name", ""))
        for value in [game["path"], game.get("name", "")]:
            matches = self.titles.get(title_key(value), [])
            compact = False
            if not matches:
                matches = self.compact.get(title_key(value).replace(" ", ""), [])
                compact = True
            if not matches:
                continue
            # We never use edit-distance or substring matches, which can confuse sequels.
            regional = [name for name in matches if requested_regions & game_regions(name)]
            if regional:
                regional.sort(key=lambda n: (-len(requested_regions & game_regions(n)), n))
                return regional[0], "same_title_region_compact" if compact else "same_title_region"
            if len(matches) == 1:
                return matches[0], "same_title_unique_release"
            world = [name for name in matches if "world" in game_regions(name)]
            if len(world) == 1:
                return world[0], "same_title_world_release"
            # An alternate region is still the same exact title, and its provenance is recorded.
            preferences = ["usa", "europe", "japan", "australia"]
            matches.sort(key=lambda n: (min([preferences.index(r) for r in game_regions(n) if r in preferences] or [99]), n))
            return matches[0], "same_title_alternate_region" if requested_regions else "same_title_default_region"
        return None, "no_same_title_snapshot"


def validate_png(path):
    with Image.open(path) as picture:
        if picture.format != "PNG":
            raise ValueError("Downloaded file is not PNG")
        width, height = picture.size
        if not (16 <= width <= 4096 and 16 <= height <= 4096):
            raise ValueError("Unexpected screenshot dimensions")
        picture.verify()
    return width, height


def download(record):
    destination = Path(record["localFile"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not destination.exists():
            payload = request_bytes(record["source"])
            temporary = destination.with_suffix(".part")
            temporary.write_bytes(payload)
            with Image.open(io.BytesIO(payload)) as picture:
                source_format = picture.format
                picture.load()
                if source_format != "PNG":
                    if source_format not in {"JPEG", "WEBP", "GIF"}:
                        raise ValueError("Unexpected source image format")
                    # A few Libretro .png filenames contain JPEG pixels, so their encoding is corrected without changing the composition.
                    picture.convert("RGB").save(temporary, format="PNG")
                    record["encodingCorrection"] = source_format + " to PNG"
                    record["sourceSha256"] = hashlib.sha256(payload).hexdigest()
            validate_png(temporary)
            temporary.replace(destination)
        width, height = validate_png(destination)
        record.update(status="ready", width=width, height=height,
                      bytes=destination.stat().st_size,
                      sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
    except Exception as error:
        record.update(status="download_failed", error=str(error))
        destination.with_suffix(".part").unlink(missing_ok=True)
    return record


def report(records, completed, total):
    status = Counter(row["status"] for row in records)
    sources = Counter(row.get("sourceType", "libretro_named_snaps") for row in records if row["status"] == "ready")
    coverage = defaultdict(Counter)
    for row in records:
        coverage[row["system"]][row["status"]] += 1
    return {
        "sourceType": "mixed_gameplay_sources" if len(sources) > 1 else "libretro_named_snaps",
        "sourceTypes": dict(sources),
        "sourceDocumentation": "https://github.com/libretro-thumbnails/libretro-thumbnails#readme",
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "completed": completed,
        "totalGames": total,
        "counts": dict(status),
        "systems": {name: dict(counts) for name, counts in sorted(coverage.items())},
        "records": sorted(records, key=lambda row: (row["system"], row["path"])),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=ROOT / "color-pop-media-inventory.json")
    parser.add_argument("--destination", type=Path, default=ROOT / "color-pop-media-staging/screenshots")
    parser.add_argument("--report", type=Path, default=ROOT / "color-pop-media-staging/screenshots-report.json")
    parser.add_argument("--workers", type=int, default=8)
    arguments = parser.parse_args()
    inventory = json.loads(arguments.inventory.read_text())
    if not inventory:
        raise SystemExit("Inventory contains no systems")
    cache = arguments.destination / "_indexes"
    cache.mkdir(parents=True, exist_ok=True)
    aliases = build_aliases()
    prior_frames = {}
    if arguments.report.exists():
        for row in json.loads(arguments.report.read_text()).get("records", []):
            if row.get("sourceType") == "existing_video_frame" and row.get("status") == "ready":
                prior_frames[(row["system"], row["path"])] = row
    index_errors = {}
    indexes = {}
    platforms = sorted({PLATFORMS[system["system"]] for system in inventory if system["system"] in PLATFORMS})
    with ThreadPoolExecutor(max_workers=arguments.workers) as pool:
        pending = {pool.submit(fetch_index, platform, cache): platform for platform in platforms}
        for future in as_completed(pending):
            platform = pending[future]
            try:
                indexes[platform] = MatchingIndex(future.result())
            except Exception as error:
                index_errors[platform] = str(error)
                print(f"Index unavailable: {platform}: {error}", flush=True)
    records = []
    for system in inventory:
        name = system["system"]
        platform = PLATFORMS.get(name)
        for game in system["games"]:
            digest = hashlib.sha256((name + "|" + game["romPath"]).encode()).hexdigest()[:20]
            record = {
                "system": name, "path": game["path"], "romPath": game["romPath"],
                "name": game.get("name", ""), "existingImage": game.get("image", ""),
                "existingThumbnail": game.get("thumbnail", ""), "existingVideo": game.get("video", ""),
                "platform": platform, "status": "unmatched",
                "localFile": str(arguments.destination / name / (digest + ".png")),
            }
            if platform in indexes:
                filename, match = indexes[platform].match(game, aliases[name])
                record["match"] = match
                if filename:
                    record.update(status="queued", sourceName=filename,
                                  source=PUBLIC_ROOT + quote(platform, safe="") + "/Named_Snaps/" + quote(filename, safe=""))
            else:
                record["match"] = "index_unavailable" if platform else "unsupported_platform"
                record["error"] = index_errors.get(platform, "No platform mapping")
            prior = prior_frames.get((name, game["path"]))
            if record["status"] == "unmatched" and prior and prior.get("existingVideo") == record["existingVideo"]:
                picture = Path(prior["localFile"])
                # Reviewed frames remain reusable only while their exact ROM, video reference, and pixels still match.
                if picture.exists() and hashlib.sha256(picture.read_bytes()).hexdigest() == prior["sha256"]:
                    validate_png(picture)
                    record.update(prior)
            records.append(record)
    queued = [record for record in records if record["status"] == "queued"]
    print(f"Matched {len(queued)} of {len(records)} games; downloading gameplay PNGs", flush=True)
    json_save(arguments.report, report(records, False, len(records)))
    done = 0
    with ThreadPoolExecutor(max_workers=arguments.workers) as pool:
        pending = [pool.submit(download, record) for record in queued]
        for future in as_completed(pending):
            future.result()
            done += 1
            if done % 25 == 0 or done == len(queued):
                print(f"Downloaded {done}/{len(queued)}; ready {sum(row['status'] == 'ready' for row in records)}", flush=True)
                json_save(arguments.report, report(records, False, len(records)))
    final = report(records, True, len(records))
    json_save(arguments.report, final)
    print(json.dumps({"report": str(arguments.report), "counts": final["counts"]}), flush=True)


if __name__ == "__main__":
    main()
