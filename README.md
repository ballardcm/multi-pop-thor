# Multi Pop Thor

> **AI disclosure:** This theme was developed with the help of AI, and its original system illustrations were AI-generated. Third-party components and their credits are listed below.

A dual-screen theme for AYN Thor running ROCKNIX EmulationStation. The theme is called **Multi Pop**; its folder, runtime identifier, and source repository name are `multi-pop-thor`.

**Keeps itself up to date (optional).** Turn on Automatic updates under UI Settings → Theme Configuration, and the Thor fetches each new release in the background, installs it the next time EmulationStation starts, and rolls back if the new version fails to start. It only moves forward to a newer version number. It is off until you turn it on. See [Automatic updates](#automatic-updates).

**Pull requests welcome!** Have a fix, new artwork, or an idea to improve the theme? Please send me a [pull request](https://github.com/ballardcm/multi-pop-thor/pulls). I'd love to see what you make. See [CONTRIBUTING.md](CONTRIBUTING.md) for getting started.

The upper display shows a system's original hardware illustration while browsing systems. Select a system and it becomes a gameplay preview with the game's title, genre, publisher, year, and description. A screenshot appears first, then an available video begins after three seconds with audio off. The lower display keeps a three-cover carousel for browsing. Missing details stay blank and missing artwork uses a labeled system card.

## Demo

A one-minute recording of browsing systems and games on an AYN Thor:

https://github.com/user-attachments/assets/88bd19d1-5c25-4b5b-9317-162c409c742d

The covers, screenshots, and game details in it are the device's fetched third-party media, not part of this repository.

## Artwork

The 68 artwork entries include Neo Geo Pocket, Neo Geo Pocket Color, PSP, PlayStation Vita, Saturn, PC Engine CD, Sega CD, Virtual Boy, regional variants, arcade platforms, and collections. Each has a distinct palette and matching upper artwork and lower card. These illustrations were created specifically for this theme; the transparent PNG sources are in [`multi-pop-thor/assets/systems`](multi-pop-thor/assets/systems/), and the card and hero PNGs are generated from them. The earlier SVG illustrations remain alongside them as legacy sources. The set also includes Wii, Wii U, Switch, 3DO, Amiga, Atari ST, ZX Spectrum, MSX, WonderSwan, TurboGrafx-16, and TurboGrafx-CD.

![All 68 Multi Pop artwork entries](docs/artwork-grid.png)

## Controls and compatibility

A selects or plays, B goes back, X opens a game's options (hold A instead if ROCKNIX's "Access game options with North button" setting is off), and L1/R1 page three games left/right in the game browser. Paging stops at the ends and keeps the current system selected. The patched frontend also keeps menus and popups on the upper display, including the B navigation popup, savestate manager, game options, message boxes, and the on-screen keyboard used for Wi-Fi passwords and searches.

Touchscreen controls work on both displays: swipe left or right to browse games and systems, then tap any visible cover to open that item, including the left and right covers on the lower display. On the upper preview, swipes browse and a short tap selects the highlighted item. These controls have been tested on the Thor with the touch-enabled frontend; older releases need the updated frontend and activation helpers.

The tested setup is ROCKNIX 20261001 on AYN Thor, with a 1920×1080 upper display, a 1240×1080 lower display, and a 4400×1080 frontend canvas. It uses a hidden 1240-pixel margin to place menus correctly. This theme targets ROCKNIX EmulationStation; other firmware and ES-DE on Android need separate validation.

## Installation

Download `multi-pop-thor-rocknix-20261001.zip` from [Releases](https://github.com/ballardcm/multi-pop-thor/releases) for a ready-to-install theme and patched frontend. This package supports **AYN Thor on ROCKNIX 20261001**; other firmware versions need a separately verified frontend. Extract it, copy the `multi-pop-thor` folder to the Thor's themes directory, and follow the [activation, update, and restore instructions](multi-pop-thor/README.md). The layout helpers preserve original settings and Sway configuration for restoration.

The companion `multi-pop-thor-source.zip` contains the theme sources, public frontend source snapshot, SDL headers source, patches, and [build-your-own instructions](frontend-build/README.md). Compiled frontends remain outside Git and are included in ready-to-install downloads. The launcher falls back to the system frontend when the patched binary is absent, with reduced paging and popup behavior.

Every PR produces preview downloads under its GitHub Actions run. Each merge to `main` publishes a numbered release containing the installable ZIP, matching source ZIP, and `SHA256SUMS`. [Release maintenance](docs/releases.md) explains how the verified frontend is refreshed when its source changes.

## Automatic updates

With Automatic updates turned on, an activated Thor checks this repository's latest release at most every six hours after Multi Pop starts. A release is downloaded only when its version number is higher than the installed one, its archive matches the release's `SHA256SUMS`, and its frontend targets the installed firmware. Once nothing is running, the frontend shows a "Multi Pop update ready" message to close with OK, and the update installs at the next EmulationStation start, so it never restarts the frontend while you play. The installed version appears as "VERSION N" under MULTI POP at the lower left of the upper display; a source checkout shows "VERSION DEVELOPMENT". A version that fails to start twice is replaced by the previous one and skipped.

Automatic updates are off by default. Turn them on or off in UI Settings → Theme Configuration → Automatic updates; turning them off also drops an update that was downloaded but not yet installed. Installing an older version is always a manual step. The [theme README](multi-pop-thor/README.md#automatic-updates) has the details.

## Working on the theme

- `multi-pop-thor/layouts/` and `theme.xml` define the two-screen layout.
- `multi-pop-thor/assets/systems/` contains the transparent PNG hardware sources and legacy SVG drawings; `assets/cards/`, `assets/heroes/`, `palettes/`, and `platforms.json` contain generated artwork and metadata.
- `tools/build-multi-pop-art.py` rebuilds cards, heroes, palettes, and platform metadata. It needs Python with Pillow. Dependencies are not yet locked for distribution.
- `tools/check-multi-pop.py` checks XML/SVG parsing, complete platform artwork and palette routes, asset references, visible screen bounds, distinct palettes, contrast, and shell syntax. Run `python3 tools/check-multi-pop.py` from this repository.
- `tools/install-multi-pop-theme.py` updates an already activated Thor from a complete archive with a verified compatible frontend. Media fetch, packaging, and installation tools use separate inventories and staging data; no library or downloaded game media is included here. See [the media tooling notes](docs/media-tools.md).

## Contributing

Contributions are welcome: please send a pull request for theme improvements, artwork, fixes, or documentation. See [CONTRIBUTING.md](CONTRIBUTING.md) for checks and preview downloads. Changes to `main` require a PR, including maintainer changes; device testing can happen from a PR preview before release.

## License

Original Multi Pop theme material, artwork, tools, and documentation are offered under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), to the extent copyright or similar rights exist and can be licensed. You may download, share, and modify covered material for noncommercial purposes, with attribution, an indication of changes, and shared adaptations under the same or a compatible license.

Credit **Multi Pop by Chris (ballardcm)** and link to [this repository](https://github.com/ballardcm/multi-pop-thor) and the license. The [full license](LICENSE) and [scope and exceptions](multi-pop-thor/LICENSING.md) explain what is covered. Existing GPL helpers, frontend components, and third-party fonts retain their own licenses.

The CC license does not create copyright in purely AI-generated material or restrict uses that do not require permission under applicable law. Attribution is appreciated even where it is not legally required.

## Credits and source status

The visual direction is inspired by [Colorful (Simplified)](https://github.com/anthonycaccese/colorful-simplified-es-de). Screen mapping follows the [DII-ESS-AYE Thor layout](https://github.com/beebono/dii-ess-aye); its graphics, sounds, and fonts are not included.

Roboto and Roboto Condensed are unmodified third-party fonts, with their Apache 2.0 [license and notice](multi-pop-thor/assets/fonts/). The optional native frontend derives from [ROCKNIX EmulationStation](https://github.com/ROCKNIX/emulationstation-next) and retains [third-party notices](multi-pop-thor/frontend/licenses/). The launcher and activation helpers retain GPL-2.0-or-later headers.

Game covers, screenshots, descriptions, and videos are separate third-party media. The device's fetched media used Libretro thumbnails, LaunchBox metadata, and credited World of Longplays excerpts; it is not part of the original system illustrations or this source repository.

This repository captures the working theme for further development. Compatibility beyond the supported firmware remains unverified. Compiled frontends are release assets rather than Git source files; the generated `integration.env` service-key file, ROMs, device configuration, and game libraries are excluded from the repository and source downloads.
