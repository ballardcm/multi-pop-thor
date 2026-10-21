"""Rebuild attributed sidebar logos from pinned SVGs; keep downloads outside Git."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
from pathlib import Path
import re
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "multi-pop-thor/assets/logos"
SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
SHAPES = {"path", "polygon", "polyline", "rect", "circle", "ellipse", "line"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalize(data, transform):
    root = ET.fromstring(data)
    if transform == "master-system-wordmark":
        # Carbon's combined mark has Sega above Master System. Keep the latter
        # here because the sidebar already has a separate Sega manufacturer mark.
        def retain_wordmark(element):
            if element.get("fill") == "#FF0000":
                return copy.deepcopy(element)
            # Keep ancestor transforms: Carbon's lettering has translated groups.
            result = ET.Element(element.tag, element.attrib)
            for child in element:
                retained = retain_wordmark(child)
                if retained is not None:
                    result.append(retained)
            return result if len(result) else None
        selected = retain_wordmark(root)
        if selected is None:
            raise ValueError("The expected Master System paths are absent")
        selected.set("viewBox", "0 105 566.929 99")
        root = selected
    elif transform != "monochrome":
        raise ValueError("Unknown logo transform: " + transform)
    for parent in list(root.iter()):
        for child in list(parent):
            if child.tag.split("}")[-1] in {"metadata", "title", "desc"}:
                parent.remove(child)
    for element in root.iter():
        tag = element.tag.split("}")[-1]
        if tag in {"script", "image", "foreignObject", "text", "style"}:
            raise ValueError("Logo must contain standalone vector shapes: " + tag)
        if any(key.split("}")[-1] == "href" and not value.startswith("#")
               for key, value in element.attrib.items()):
            raise ValueError("External SVG reference")
        if tag in SHAPES or tag in {"g", "svg"}:
            style = element.get("style", "")
            fill_none = element.get("fill") == "none" or re.search(r"(?:^|;)\s*fill\s*:\s*none", style)
            element.set("fill", "none" if fill_none else "#FFFFFF")
            if element.get("stroke") not in (None, "none"):
                element.set("stroke", "#FFFFFF")
            if style:
                style = re.sub(r"(?<![-\w])fill\s*:\s*[^;]+", "fill:" + element.get("fill"), style)
                style = re.sub(r"(?<![-\w])stroke\s*:\s*(?!none)[^;]+", "stroke:#FFFFFF", style)
                element.set("style", style)
    viewbox = root.get("viewBox")
    if not viewbox:
        raise ValueError("Missing viewBox")
    _, _, width, height = map(float, viewbox.split())
    if width <= 0 or height <= 0:
        raise ValueError("Invalid logo size")
    root.set("width", str(width))
    root.set("height", str(height))
    return (ET.tostring(root, encoding="unicode", xml_declaration=True) + "\n").encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path, help="Source cache outside the repository")
    parser.add_argument("--fetch", action="store_true", help="Download missing pinned sources")
    parser.add_argument("--record-hashes", action="store_true", help="Record hashes when curating new sources")
    args = parser.parse_args()
    if args.cache.resolve().is_relative_to(ROOT.parents[2]):
        parser.error("Keep the source cache outside the repository")
    args.cache.mkdir(parents=True, exist_ok=True)
    catalog_path = ROOT / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    entries = list(catalog["platforms"].values()) + list(catalog["manufacturers"].values())

    def build(entry):
        source = catalog["sources"][entry["source"]]
        url = source["repository"].replace("github.com", "raw.githubusercontent.com") + "/" + source["revision"] + "/" + entry["source_path"]
        cache = args.cache / (sha(url.encode()) + ".svg")
        if not cache.exists():
            if not args.fetch:
                raise ValueError("Missing cached source: " + url)
            with urllib.request.urlopen(url, timeout=30) as response:
                cache.write_bytes(response.read())
        data = cache.read_bytes()
        if not args.record_hashes and sha(data) != entry.get("source_sha256"):
            raise ValueError("Source hash mismatch: " + entry["file"])
        result = normalize(data, entry["transform"])
        if not args.record_hashes and sha(result) != entry.get("sha256"):
            raise ValueError("Generated hash mismatch: " + entry["file"])
        destination = ROOT / entry["file"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(result)
        return entry, sha(data), sha(result)

    with ThreadPoolExecutor(max_workers=6) as pool:
        for entry, source_hash, result_hash in pool.map(build, entries):
            entry.update(source_sha256=source_hash, sha256=result_hash)
    if args.record_hashes:
        catalog_path.write_text(json.dumps(catalog, indent=2) + "\n")
    print(f"Built and verified {len(entries)} attributed sidebar logos.")


if __name__ == "__main__":
    main()
