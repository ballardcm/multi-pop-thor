# Multi Pop for AYN Thor

Multi Pop is a ROCKNIX EmulationStation theme with a gameplay preview and game details on the upper display and a three-cover browser on the lower display. Every system in the latest live Thor audit has its own color, original hardware illustration, and matching lower card. Virtual Boy, Neo Geo Pocket, Neo Geo Pocket Color, and PlayStation Vita are also included. Missing cover art falls back to the game's image, then to a labeled card for that system.

**Logo artwork credits:** Our sidebar marks come from [HVR88's Monochrome Gaming Logos](https://github.com/HVR88/Monochrome-Gaming-Logos) and [Rookervik and the RetroPie Carbon contributors](https://github.com/RetroPie/es-theme-carbon), building on Nils Bonenberger's Simple theme. The FinalBurn Neo phoenix comes from [Fabrice Caruso’s expanded Carbon collection](https://github.com/fabricecaruso/es-theme-carbon). Please explore their work and the [Pegasus](https://pegasus-frontend.org/) and [GameOS](https://github.com/PlayingKarrde/gameOS) projects that inspired HVR88's collection. The logos are third-party artwork, not AI-generated Multi Pop illustrations. Full acknowledgments, modifications, source records, and original notices ship in [assets/logos/README.md](assets/logos/README.md).

The upper display is 1920×1080 and the lower display is 1240×1080. The theme uses a 4400×1080 virtual canvas with a hidden 1240px margin so native menus stay centered on the upper display. It is intended for the Thor's ROCKNIX frontend, rather than ES-DE on Android.

Once activated, Multi Pop can keep itself up to date; see [Automatic updates](#automatic-updates). It is off until you turn it on in UI Settings → Theme Configuration, which also shows the installed version.

Battery status and connected Wi-Fi appear at the upper display's top right. They respect the frontend's battery and network indicator settings; the default battery setting includes its percentage.

## Install

Step-by-step installation, removal and rollback instructions are in the project README: [Install](https://github.com/ballardcm/multi-pop-thor#install) and [Remove or roll back](https://github.com/ballardcm/multi-pop-thor#remove-or-roll-back). In short, copy this `multi-pop-thor` folder to `/roms/themes/` on an AYN Thor running **ROCKNIX 20261001**, then run this from an SSH session and select `multi-pop-thor` under UI Settings → Theme Set:

```sh
bash \
  /roms/themes/multi-pop-thor/scripts/enable_multi_pop_thor.sh \
  --prepare
```

The helper verifies both displays, saves the original settings and Sway configuration, and adds a separate layout fragment. With `--prepare`, it restarts the frontend while preserving the current theme selection. Select `multi-pop-thor` in EmulationStation's Theme Set menu afterward. Running the helper without that flag also selects Multi Pop. If another theme's launcher is already mounted, the helper preserves it and stops; disable that theme's startup entry and reboot before activating Multi Pop.

Activation installs an `essway` service override automatically. After reboot, it restores the two-screen layout and touchscreen controls whenever Multi Pop is selected; other themes use the system frontend. Both supported theme directories work, though automatic updates and the updater need `/roms/themes/`. Existing installations can enable automatic startup by rerunning the activation helper with `--prepare`. An unrelated or manually installed service override must be removed before activation; the helper preserves it and explains the conflict.

## Artwork and controls

The carousel prefers `<thumbnail>` cover art and falls back to `<image>` when needed. The upper display uses `<image>` for a gameplay screenshot, with the title, genre, publisher, year, and description beside it when available. After three seconds, an available `<video>` replaces the screenshot with audio off. One media component owns both phases, so game artwork cannot overlap the system card. Media keeps its original proportions, and absent metadata stays blank.

The footer follows ROCKNIX's default button mapping: A selects a system or plays a game, and B returns from the game browser. On the system browser, B opens system navigation and START opens the menu. In the game browser, X opens the highlighted game's options when User Interface Settings has "Access game options with North button" on; otherwise hold A. With a single game view, Multi Pop also hides the Gamelist View Style setting, which would offer no real choice. If you invert the A/B preference, update the two footer text entries in `layouts/system.xml` and `layouts/games.xml`.

In the game browser, L1 moves three games left and R1 moves three games right, matching the three-cover lower carousel. Paging stops at the first or last game and keeps the current system selected. This behavior requires a compatible patched frontend and applies only to Multi Pop on the Thor's 4400×1080 canvas.

Touchscreen controls work on both displays: swipe left for the next games or systems, swipe right for the previous ones, and tap any visible cover to select that game or system on the lower display. On the upper preview, swipes browse and a short tap selects the highlighted item. Activation enables the lower touchscreen, which stock ROCKNIX disables for its single-screen frontend. Small finger movement is tolerated; long presses and vertical drags do not select. Swiping, tapping all three visible covers, and savestate popup placement have been tested on AYN Thor running ROCKNIX 20261001. These controls require the touch-enabled frontend and updated activation helpers; older releases do not include them. The back arrows on the upper game-selection screen and lower Library header perform the normal B/back action when tapped. Both displays show swipe/tap hints. The existing Disable Touchscreen setting is respected. While the frontend loads or reloads, `splash.xml` shows a Multi Pop loading screen on the upper display instead of the frontend's default Batocera graphic.

The system artwork depicts recognizable original consoles, handhelds, controllers, and representative arcade cabinets. Software and collection entries have their own illustrations. Light platform colors use dark text; dark colors use white text. Menu and savestate selections use a solid purple fill with white labels.

Game media is installed separately from the theme. Existing covers remain available as thumbnails when gameplay screenshots are added. Source and creator credits accompany fetched screenshots, descriptions, and video excerpts in the media installation report.

## Automatic updates

Automatic updates are optional and **off by default**. Nothing is downloaded until you turn them on.

### Turn them on or off

Open the main menu, then UI Settings → Theme Configuration. Under Theme Options:

- **Installed version** shows the release you are running, such as `20`. A copy installed from a source checkout shows `DEVELOPMENT`.
- **Automatic updates** is Off or On. Off is the default and is used whenever nothing has been chosen. The choice is saved as `subset.autoupdate` in `/storage/.config/emulationstation/es_settings.cfg`.

Turning updates off also discards an update that was downloaded but not yet installed.

### Check for updates now

Under Tools on the same screen, **Check for updates** looks for a newer release straight away, whether or not Automatic updates is on and however recently the last check ran. A message then says either that a version is ready, which installs the next time EmulationStation starts, or that Multi Pop is up to date. An update you asked for this way installs even while Automatic updates is off. The button needs the Multi Pop frontend and appears only while Multi Pop is the selected theme.

### Which version you are running

Every release has a version number that goes up with each release. Besides Theme Configuration, it appears as "VERSION N" under MULTI POP in the top bar of the lower display. The release's GitHub title carries the same number, and the installed theme records it in `version.json`.

### How an update happens

1. After each Multi Pop start, a background check looks at this repository's latest release. It checks at most every six hours, so restarting sooner does not check again.
2. A release is downloaded only when its version number is higher than the installed one, so an automatic update never moves you to an older version. The download must match the release's `SHA256SUMS` and the archive manifest, and its frontend must target the installed firmware.
3. Once nothing is running (no game, scrape or install), a "Multi Pop update ready" message appears; close it with OK.
4. The update installs the next time EmulationStation starts, after a reboot or Quit → Restart EmulationStation, so it never restarts the frontend while you are using it. A "Multi Pop updated to version N" message confirms it.

If the new version does not reach a running frontend within two further starts, the previous theme is put back and that release is skipped. One previous theme stays in `/roms/themes/.multi-pop-backup-*` for manual recovery. Installing an older release is a manual step with the updater below. The log is `/storage/.config/multi-pop-thor/update/auto-update.log`.

## Update an activated installation

Upload the new ready-to-install ZIP to the Thor and use the bundled `scripts/update_theme.py` with the archive path and its SHA-256 from `SHA256SUMS`. Run it as root while EmulationStation is idle. It verifies the archive, backs up the current theme, restarts the frontend, and rolls back if verification fails. It preserves settings and Sway configuration and refuses archives that change the active launcher. For a launcher change, use the restore and fresh installation procedure instead.

```sh
python3 \
  /roms/themes/multi-pop-thor/scripts/update_theme.py \
  /storage/downloads/multi-pop-thor-rocknix-20261001.zip \
  SHA256_FROM_SHA256SUMS
```

The updater expects the active theme at `/roms/themes/multi-pop-thor`. Installations in the alternative EmulationStation theme directory should use restore and fresh installation instead.

## Restore

Never delete this folder while Multi Pop is activated: the Thor's frontend starts through `scripts/start_after_reboot.sh`, and without it the Thor boots to a black screen. Run the restore helper first:

```sh
bash \
  /roms/themes/multi-pop-thor/scripts/restore_multi_pop_thor.sh
```

Restore removes the automatic startup override and the launcher mount, and moves the layout fragment into `/storage/.config/multi-pop-thor/`. It reverts only the settings Multi Pop changes (`ThemeSet`, `GamelistViewStyle`, `FullScreenMenu` and `GameTransitionStyle`) to their values in the original backup, and only while each still holds Multi Pop's value; every other setting changed since activation is kept. An unedited Sway configuration returns to the original backup; an edited one keeps its edits and loses only the Multi Pop include. Restore still stops without changing anything if another launcher or service override has taken over startup; the project README's [Remove Multi Pop](https://github.com/ballardcm/multi-pop-thor#remove-multi-pop) gives hand-removal steps for that case and for a Thor that already shows a black screen. Activating again after a restore takes fresh backups and moves the earlier record into a `restored-*` folder.

## Validation and credits

Original Multi Pop material is offered under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), to the extent copyright or similar rights exist and can be licensed. Downloading, sharing, and modifying covered material for noncommercial purposes is permitted with attribution and ShareAlike terms. See [LICENSE](LICENSE) and [LICENSING.md](LICENSING.md) for the full terms, AI-generated material clarification, and GPL and third-party exceptions.

The XML, local asset references, screen bounds, distinct palettes, text contrast, and helper syntax have been checked. Hardware illustrations have been rendered and reviewed at upper-screen and lower-card sizes.

The ready-to-install download includes the patched frontend in `frontend/emulationstation`, rebuilt from the source revision used by ROCKNIX 20261001 on this Thor. Compiled frontends are excluded from Git; the matching source download includes build instructions in `frontend-build/README.md`. It restricts B navigation and the savestate manager to the upper display and calculates the save row from that display's width. These changes apply only to a 4400×1080 canvas. Selection uses purple with white labels. The frontend also handles L1/R1 paging in Multi Pop's game carousel.

The launcher uses this frontend when present and keeps the system frontend at `/usr/bin/emulationstation` available as a fallback. The build uses the Thor's existing libraries, preserves controller support, and has no added library-path override. It contains no online-service keys: activation copies the stock frontend's ScreenScraper, TheGamesDB and RetroAchievements keys into the root-only `/storage/.config/multi-pop-thor/integration.env` on your Thor, and refreshes it at each Multi Pop boot, so scraping and achievements keep working without the theme ever shipping a key. The tested compatibility report, public source patches, and license notices are retained in `frontend/`. For a different firmware release, verify compatibility before using this optional binary.

The design is inspired by [Colorful (Simplified)](https://github.com/anthonycaccese/colorful-simplified-es-de). The screen mapping follows the staged [DII-ESS-AYE Thor layout](https://github.com/beebono/dii-ess-aye), with original Multi Pop graphics. No DII-ESS-AYE graphics, sounds, or fonts are included.

Roboto fonts are unmodified and include their Apache 2.0 license and notice in `assets/fonts/`. The launcher retains ROCKNIX's GPL-2.0-or-later notice; the activation and restore helpers use the same license.


## Date-based releases

Releases use labels such as **10.21.26.1**, aligned with RG DS: month, day, year, and the release revision for that day. Existing installations update normally. The displayed date label is separate from the updater’s internal ordering value.
