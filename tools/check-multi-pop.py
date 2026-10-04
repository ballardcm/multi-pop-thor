"""Check the shipped theme's references and the Thor's visible screen boundaries."""

from pathlib import Path
import json
import re
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1] / "multi-pop-thor"
WIDTH, HEIGHT = 4400, 1080
PANELS = ((1240, 0, 3160, 1080), (3160, 0, 4400, 1080))
errors = []
checked = 0


def vector(element, name, default=(0, 0)):
    raw = element.findtext(name)
    return tuple(float(v) for v in raw.split()) if raw else default


for path in sorted(ROOT.rglob("*.xml")):
    tree = ET.parse(path)
    for node in tree.iter():
        if node.tag == "include":
            target = (path.parent / node.text.strip()).resolve()
            if not target.is_file():
                errors.append(f"Missing include: {target}")
        if node.tag in ("path", "default", "fontPath", "systemIcon", "systemCard", "systemHero") and node.text:
            value = node.text.strip().replace("${themePath}", str(ROOT))
            if value.startswith(str(ROOT)) and "${" not in value and not Path(value).is_file():
                errors.append(f"Missing asset: {value}")
    for view in tree.findall("view"):
        if view.attrib.get("name") not in ("system", "gamecarousel", "system, gamecarousel"):
            continue
        for element in view:
            if element.tag not in ("image", "text", "video", "carousel", "gamecarousel"):
                continue
            if element.findtext("visible") == "false" or element.find("pos") is None:
                continue
            pos = vector(element, "pos")
            size = vector(element, "size", vector(element, "maxSize"))
            if size == (0, 0):
                continue
            origin = vector(element, "origin")
            x, y = (pos[0] - origin[0] * size[0]) * WIDTH, (pos[1] - origin[1] * size[1]) * HEIGHT
            w, h = size[0] * WIDTH, size[1] * HEIGHT
            box = (x, y, x + w, y + h)
            if element.attrib.get("name") == "canvas":
                assert all(abs(a-b) < .01 for a, b in zip(box, (0, 0, WIDTH, HEIGHT)))
                continue
            if not any(box[0] >= p[0]-.01 and box[1] >= p[1]-.01 and box[2] <= p[2]+.01 and box[3] <= p[3]+.01 for p in PANELS):
                errors.append(f"Outside visible panel: {path.name}/{element.attrib.get('name')}: {box}")
            checked += 1

for path in sorted(ROOT.rglob("*.svg")):
    ET.parse(path)

# A registered platform needs its own route and complete artwork so it cannot silently use the library fallback.
platforms = json.loads((ROOT / "platforms.json").read_text())
routes = {node.get("if"): node.text.strip() for node in ET.parse(ROOT / "theme.xml").getroot().findall("include")}
for key in platforms:
    for folder, extension in (("palettes", "xml"), ("assets/systems", "svg"),
                              ("assets/cards", "png"), ("assets/heroes", "png")):
        target = ROOT / folder / f"{key}.{extension}"
        if not target.is_file():
            errors.append(f"Missing platform artwork: {target.relative_to(ROOT)}")
    if key != "default" and routes.get(f"${{system.theme}} == '{key}'") != f"./palettes/{key}.xml":
        errors.append(f"Missing platform palette route: {key}")

for path in sorted((ROOT / "scripts").glob("*.sh")):
    result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
    if result.returncode:
        errors.append(result.stderr.strip())

def luminance(color):
    channels = [int(color[i:i+2], 16)/255 for i in (0, 2, 4)]
    linear = [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in channels]
    return sum(c*w for c, w in zip(linear, (.2126, .7152, .0722)))


palette_colors = set()
for path in sorted((ROOT / "palettes").glob("*.xml")):
    tree = ET.parse(path)
    color = tree.findtext("variables/accent")[:6]
    foreground = tree.findtext("variables/accentInk")[:6]
    light, dark = sorted([luminance(color), luminance(foreground)], reverse=True)
    if (light+.05)/(dark+.05) < 4.5:
        errors.append(f"Insufficient accent text contrast: {path.name}")
    if color in palette_colors:
        errors.append(f"Reused palette color: {path.name}")
    palette_colors.add(color)

if errors:
    raise SystemExit("\n".join(errors))
print(f"PASS: XML and SVG parse; local references resolve; {checked} placements fit visible panels; palette contrast and shell syntax pass.")
