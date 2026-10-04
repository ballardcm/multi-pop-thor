"""Build the theme's platform cards from original vector hardware artwork."""

from pathlib import Path
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / "multi-pop-thor"
# Configurable tools let the same artwork source build outside the original Codex runtime.
NODE = os.environ.get("MULTIPOP_NODE", "node")
SHARP = os.environ.get("MULTIPOP_SHARP", "sharp")
FONT = ROOT / "assets/fonts/RobotoCondensed-Bold.ttf"
REGULAR = ROOT / "assets/fonts/Roboto-Regular.ttf"
INK = "191A2E"

# Each installed platform has its own color, while the hardware preserves its original material colors.
SYSTEMS = {
    "fbneo": ("Final Burn Neo", "Arcade", "2002", "E9B33F"),
    "atari2600": ("Atari 2600", "Atari", "1977", "9B522B"),
    "atari5200": ("Atari 5200", "Atari", "1982", "5C6774"),
    "atari7800": ("Atari 7800", "Atari", "1986", "A9B0B7"),
    "atarilynx": ("Atari Lynx", "Atari", "1989", "F2CB57"),
    "atarijaguar": ("Atari Jaguar", "Atari", "1993", "B6283D"),
    "wonderswancolor": ("WonderSwan Color", "Bandai", "2000", "48AABD"),
    "colecovision": ("ColecoVision", "Coleco", "1982", "BD405B"),
    "intellivision": ("Intellivision", "Mattel", "1979", "947146"),
    "c64": ("Commodore 64", "Commodore", "1982", "3567A8"),
    "pico8": ("PICO-8", "Lexaloffle", "2015", "EF70A5"),
    "xbox": ("Xbox", "Microsoft", "2001", "357D28"),
    "pcengine": ("PC Engine", "NEC", "1987", "E8D8AA"),
    "pce-cd": ("PC Engine CD", "NEC", "1988", "A88872"),
    "nes": ("Nintendo Entertainment System", "Nintendo", "1985", "B83931"),
    "gb": ("Game Boy", "Nintendo", "1989", "A3AD46"),
    "snes": ("Super Nintendo", "Nintendo", "1991", "B49EE1"),
    "n64": ("Nintendo 64", "Nintendo", "1996", "156B59"),
    "gbc": ("Game Boy Color", "Nintendo", "1998", "78BE48"),
    "gc": ("GameCube", "Nintendo", "2001", "5B32DF"),
    "gba": ("Game Boy Advance", "Nintendo", "2001", "393977"),
    "nds": ("Nintendo DS", "Nintendo", "2004", "C8D5DF"),
    "3ds": ("Nintendo 3DS", "Nintendo", "2011", "EB5E52"),
    "virtualboy": ("Virtual Boy", "Nintendo", "1995", "D81F36"),
    "atomiswave": ("Atomiswave", "Sammy", "2003", "F5A53D"),
    "sg-1000": ("SG-1000", "Sega", "1983", "6AAAD8"),
    "mastersystem": ("Master System", "Sega", "1985", "D74A49"),
    "genesis": ("Genesis", "Sega", "1989", "243858"),
    "segacd": ("Sega CD", "Sega", "1992", "9AA4D9"),
    "saturn": ("Saturn", "Sega", "1994", "426B8E"),
    "gamegear": ("Game Gear", "Sega", "1990", "177D8D"),
    "sega32x": ("Sega 32X", "Sega", "1994", "993BCE"),
    "model3": ("Sega Model 3", "Sega", "1996", "0765C2"),
    "dreamcast": ("Dreamcast", "Sega", "1998", "E57731"),
    "naomi": ("Naomi", "Sega", "1998", "98C8CC"),
    "neogeo": ("Neo Geo", "SNK", "1990", "D7AD27"),
    "ngp": ("Neo Geo Pocket", "SNK", "1998", "646C78"),
    "ngpc": ("Neo Geo Pocket Color", "SNK", "1999", "4B55A4"),
    "vectrex": ("Vectrex", "GCE", "1982", "427D80"),
    "ps2": ("PlayStation 2", "Sony", "2000", "2448CC"),
    "ps3": ("PlayStation 3", "Sony", "2006", "373B45"),
    "steam": ("Steam", "PC Gaming", "", "287BB5"),
    "music": ("Music Player", "Your Collection", "", "A42883"),
    "ports": ("Ports", "PC Gaming", "", "3F7269"),
    "tools": ("Tools", "Thor Utilities", "", "B16B49"),
    "auto-favorites": ("Favorites", "Your Collection", "", "C73269"),
    "psx": ("PlayStation", "Sony", "1994", "77796F"),
    "psp": ("PSP", "Sony", "2004", "2A4D62"),
    "psvita": ("PlayStation Vita", "Sony", "2011", "1686C7"),
    "sfc": ("Super Famicom", "Nintendo", "1990", "EEEDEE"),
    "famicom": ("Famicom", "Nintendo", "1983", "8D1C32"),
    "megadrive": ("Mega Drive", "Sega", "1988", "172D3B"),
    "mame": ("MAME", "Arcade", "1997", "623C7E"),
    "arcade": ("Arcade", "Coin-Op Classics", "", "D33D23"),
    "auto-allgames": ("All Games", "Your Collection", "", "1F9C94"),
    "auto-lastplayed": ("Recently Played", "Your Collection", "", "FAAE82"),
    "default": ("Game Library", "Multi Pop", "", "6D4776"),
}


def rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def luminance(hex_color):
    values = [c / 255 for c in rgb(hex_color)]
    linear = [c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in values]
    return sum(c * weight for c, weight in zip(linear, (.2126, .7152, .0722)))


def foreground(accent):
    dark_ink = "000000"
    light = 1.05 / (luminance(accent) + .05)
    dark = (luminance(accent) + .05) / (luminance(dark_ink) + .05)
    return "FFFFFF" if light >= dark else dark_ink


def tint(accent, amount):
    return tuple(round(c * amount + 248 * (1 - amount)) for c in rgb(accent))


def draw_lines(draw, text, x, y, width, font_size, fill, max_lines=3, max_height=None):
    while font_size > 18:
        font = ImageFont.truetype(str(FONT), font_size)
        lines = []
        for word in text.split():
            if lines and draw.textlength(lines[-1] + " " + word, font=font) <= width:
                lines[-1] += " " + word
            else:
                lines.append(word)
        fits_height = max_height is None or len(lines) * font_size * 1.12 <= max_height
        if fits_height and len(lines) <= max_lines and all(draw.textlength(line, font=font) <= width for line in lines):
            break
        font_size -= 2
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font)
        y += font_size * 1.12
    return y


def make_art(key, details, hardware):
    title, maker, year, accent = details
    color, text_color = rgb(accent), rgb(foreground(accent))
    card = Image.new("RGBA", (400, 640), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle((0, 0, 399, 639), radius=28, fill="#FAFBFE", outline=tint(accent, .4), width=3)
    draw.rounded_rectangle((0, 0, 399, 190), radius=28, fill=color)
    draw.rectangle((0, 110, 399, 190), fill=color)
    draw.text((28, 22), maker.upper(), fill=text_color, font=ImageFont.truetype(str(REGULAR), 19))
    draw_lines(draw, title, 28, 61, 345, 47, text_color, max_lines=3, max_height=112)
    draw.ellipse((42, 435, 358, 475), fill=tint(accent, .12))
    small = hardware.copy()
    small.thumbnail((382, 286), Image.Resampling.LANCZOS)
    card.alpha_composite(small, ((400 - small.width) // 2, 205 + (286 - small.height) // 2))
    draw.text((28, 550), year or "YOUR LIBRARY", fill=rgb(INK), font=ImageFont.truetype(str(FONT), 34))
    draw.line((28, 527, 372, 527), fill=tint(accent, .45), width=3)
    draw.text((28, 598), "MULTI POP  /  THOR", fill="#646A80", font=ImageFont.truetype(str(REGULAR), 17))
    card.save(ROOT / "assets/cards" / (key + ".png"))

    hero = Image.new("RGBA", (1600, 900), (0, 0, 0, 0))
    draw = ImageDraw.Draw(hero)
    draw.rounded_rectangle((0, 0, 1599, 899), radius=40, fill="#FAFBFE")
    draw.ellipse((590, -260, 1800, 950), fill=tint(accent, .20))
    draw.rounded_rectangle((84, 78, 560, 146), radius=20, fill=color)
    draw.text((108, 94), maker.upper(), fill=text_color, font=ImageFont.truetype(str(REGULAR), 32))
    draw_lines(draw, title, 84, 255, 530, 104, rgb(INK), max_lines=3)
    draw.text((86, 739), year or "YOUR COLLECTION", fill=rgb(INK), font=ImageFont.truetype(str(FONT), 56))
    draw.ellipse((695, 735, 1490, 802), fill=tint(accent, .32))
    large = hardware.copy()
    large.thumbnail((990, 743), Image.Resampling.LANCZOS)
    hero.alpha_composite(large, (600 + (990 - large.width) // 2, 93 + (743 - large.height) // 2))
    # The artwork stays inside a rounded card so diagonal background shapes never leak into the sidebar.
    mask = Image.new("L", hero.size)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, 1599, 899), radius=40, fill=255)
    hero.putalpha(mask)
    hero.save(ROOT / "assets/heroes" / (key + ".png"))


def make_grid():
    # Building the overview from the same heroes keeps the README artwork in sync with the theme.
    columns, width, height, gap = 5, 400, 225, 18
    rows = (len(SYSTEMS) + columns - 1) // columns
    grid = Image.new("RGB", (columns * width + (columns + 1) * gap,
                             100 + rows * height + (rows + 1) * gap), "#ECEEF5")
    draw = ImageDraw.Draw(grid)
    draw.text((18, 18), "Multi Pop — all systems", fill=rgb(INK),
              font=ImageFont.truetype(str(REGULAR), 34))
    draw.text((18, 64), f"{len(SYSTEMS)} original hardware and collection designs · includes Virtual Boy",
              fill="#646A80", font=ImageFont.truetype(str(REGULAR), 20))
    for index, key in enumerate(SYSTEMS):
        with Image.open(ROOT / "assets/heroes" / (key + ".png")) as hero:
            preview = hero.resize((width, height), Image.Resampling.LANCZOS)
            grid.paste(preview, (gap + index % columns * (width + gap),
                                 100 + index // columns * (height + gap)), preview)
    grid.save(ROOT.parent / "docs/artwork-grid.png")


def main():
    for name in ["palettes", "assets/cards", "assets/heroes"]:
        (ROOT / name).mkdir(parents=True, exist_ok=True)
    for key, details in SYSTEMS.items():
        accent = details[3]
        (ROOT / "palettes" / (key + ".xml")).write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<theme>\n    <formatVersion>7</formatVersion>\n'
            '    <variables>\n'
            f'        <accent>{accent}FF</accent>\n'
            f'        <accentInk>{foreground(accent)}FF</accentInk>\n'
            f'        <systemIcon>${{themePath}}/assets/systems/{key}.svg</systemIcon>\n'
            f'        <systemCard>${{themePath}}/assets/cards/{key}.png</systemCard>\n'
            f'        <systemHero>${{themePath}}/assets/heroes/{key}.png</systemHero>\n'
            '    </variables>\n</theme>\n'
        )
    (ROOT / "platforms.json").write_text(json.dumps({key: dict(zip(["title", "manufacturer", "year", "accent"], value)) for key, value in SYSTEMS.items()}, indent=2) + "\n")
    if "--palettes-only" in sys.argv:
        print(f"Built {len(SYSTEMS)} distinct palettes.")
        return
    render = "const sharp=require(process.argv[1]);sharp(process.argv[2],{density:144}).resize(1200,900).png().toBuffer().then(b=>process.stdout.write(b));"
    from io import BytesIO
    for key, details in SYSTEMS.items():
        source = ROOT / "assets/systems" / (key + ".svg")
        if ET.parse(source).getroot().get("viewBox") != "0 0 800 600":
            raise SystemExit(f"Artwork not ready: {key}")
        png = subprocess.check_output([str(NODE), "-e", render, str(SHARP), str(source)])
        make_art(key, details, Image.open(BytesIO(png)).convert("RGBA"))
    make_grid()
    print(f"Built {len(SYSTEMS)} hero panels and {len(SYSTEMS)} platform cards.")


if __name__ == "__main__":
    main()
