# Multi Pop for AYN Thor

Multi Pop is a ROCKNIX EmulationStation theme with a gameplay preview and game details on the upper display and a three-cover browser on the lower display. Every system in the latest live Thor audit has its own color, original hardware illustration, and matching lower card. Virtual Boy, Neo Geo Pocket, Neo Geo Pocket Color, and PlayStation Vita are also included. Missing cover art falls back to the game's image, then to a labeled card for that system.

The upper display is 1920×1080 and the lower display is 1240×1080. The theme uses a 4400×1080 virtual canvas with a hidden 1240px margin so native menus stay centered on the upper display. It is intended for the Thor's ROCKNIX frontend, rather than ES-DE on Android.

## Install

Use `multi-pop-thor-rocknix-20261001.zip` from [Releases](https://github.com/ballardcm/multi-pop-thor/releases) for AYN Thor on **ROCKNIX 20261001**. It includes the verified patched frontend, so compilation is not required. Check the download against `SHA256SUMS`, extract it, and install the `multi-pop-thor` folder. The source ZIP is a separate download for development; it includes the public frontend sources and build instructions. Other firmware versions require a separately validated frontend.

If an earlier version is already activated, run its original restore helper before installing this renamed theme. The new helpers use separate backup and configuration paths, so they cannot restore an earlier installation's activation state.

1. Copy the complete `multi-pop-thor` folder into `/roms/themes/` or `/storage/.config/emulationstation/themes/`.
2. If the previous Thor theme runs automatically at startup, turn off that startup entry first. Its helper selects its own theme again whenever it runs.
3. From a terminal on the Thor, run:

   ```sh
   bash \
     /roms/themes/multi-pop-thor/scripts/enable_multi_pop_thor.sh \
     --prepare
   ```

The helper verifies both displays, saves the original settings and Sway configuration, and adds a separate layout fragment. With `--prepare`, it restarts the frontend while preserving the current theme selection. Select `multi-pop-thor` in EmulationStation's Theme Set menu afterward. Running the helper without that flag also selects Multi Pop. If another theme's launcher is already mounted, the helper preserves it and stops; disable that theme's startup entry and reboot before activating Multi Pop.

The launcher mount lasts until reboot. Run the helper with `--prepare` again after reboot to restore the full two-screen canvas while keeping the selected theme. The optional `scripts/start_after_reboot.sh` can also be copied to the activation state's `start-after-reboot.sh` for an existing `essway` service override. It reapplies the layout only when Multi Pop is selected and uses the system frontend for other themes. The activation helper does not install a service override automatically.

## Artwork and controls

The carousel prefers `<thumbnail>` cover art and falls back to `<image>` when needed. The upper display uses `<image>` for a gameplay screenshot, with the title, genre, publisher, year, and description beside it when available. After three seconds, an available `<video>` replaces the screenshot with audio off. One media component owns both phases, so game artwork cannot overlap the system card. Media keeps its original proportions, and absent metadata stays blank.

The footer follows ROCKNIX's default button mapping: A selects a system or plays a game, and B returns from the game browser. On the system browser, B opens system navigation and START opens the menu. If you invert the A/B preference, update the two footer text entries in `layouts/system.xml` and `layouts/games.xml`.

In the game browser, L1 moves three games left and R1 moves three games right, matching the three-cover lower carousel. Paging stops at the first or last game and keeps the current system selected. This behavior requires a compatible patched frontend and applies only to Multi Pop on the Thor's 4400×1080 canvas.

Touchscreen controls work on both displays: swipe left for the next games or systems, swipe right for the previous ones, and tap any visible cover to select that game or system on the lower display. On the upper preview, swipes browse and a short tap selects the highlighted item. Activation enables the lower touchscreen, which stock ROCKNIX disables for its single-screen frontend. Small finger movement is tolerated; long presses and vertical drags do not select. Swiping, tapping all three visible covers, and savestate popup placement have been tested on AYN Thor running ROCKNIX 20261001. These controls require the touch-enabled frontend and updated activation helpers; older releases do not include them. The back arrows on the upper game-selection screen and lower Library header perform the normal B/back action when tapped. Both displays show swipe/tap hints. The existing Disable Touchscreen setting is respected.

The system artwork depicts recognizable original consoles, handhelds, controllers, and representative arcade cabinets. Software and collection entries have their own illustrations. Light platform colors use dark text; dark colors use white text. Menu and savestate selections use a solid purple fill with white labels.

Game media is installed separately from the theme. Existing covers remain available as thumbnails when gameplay screenshots are added. Source and creator credits accompany fetched screenshots, descriptions, and video excerpts in the media installation report.

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

```sh
bash \
  /roms/themes/multi-pop-thor/scripts/restore_multi_pop_thor.sh
```

Restore uses the original backups in `/storage/.config/multi-pop-thor/`. It accepts the theme and carousel choices saved when you manually select Multi Pop. It stops if other settings or configuration have changed since activation, so newer changes are preserved. Backups remain available for manual recovery.

## Validation and credits

Original Multi Pop material is offered under [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/), to the extent copyright or similar rights exist and can be licensed. Downloading, sharing, and modifying covered material for noncommercial purposes is permitted with attribution and ShareAlike terms. See [LICENSE](LICENSE) and [LICENSING.md](LICENSING.md) for the full terms, AI-generated material clarification, and GPL and third-party exceptions.

The XML, local asset references, screen bounds, distinct palettes, text contrast, and helper syntax have been checked. Hardware illustrations have been rendered and reviewed at upper-screen and lower-card sizes.

The ready-to-install download includes the patched frontend in `frontend/emulationstation`, rebuilt from the source revision used by ROCKNIX 20261001 on this Thor. Compiled frontends are excluded from Git; the matching source download includes build instructions in `frontend-build/README.md`. It restricts B navigation and the savestate manager to the upper display and calculates the save row from that display's width. These changes apply only to a 4400×1080 canvas. Selection uses purple with white labels. The frontend also handles L1/R1 paging in Multi Pop's game carousel.

The launcher uses this frontend when present and keeps the system frontend at `/usr/bin/emulationstation` available as a fallback. The build uses the Thor's existing libraries, preserves controller support and online integrations, and has no added library-path override. The tested compatibility report, public source patches, and license notices are retained in `frontend/`. For a different firmware release, verify compatibility before using this optional binary.

The design is inspired by [Colorful (Simplified)](https://github.com/anthonycaccese/colorful-simplified-es-de). The screen mapping follows the staged [DII-ESS-AYE Thor layout](https://github.com/beebono/dii-ess-aye), with original Multi Pop graphics. No DII-ESS-AYE graphics, sounds, or fonts are included.

Roboto fonts are unmodified and include their Apache 2.0 license and notice in `assets/fonts/`. The launcher retains ROCKNIX's GPL-2.0-or-later notice; the activation and restore helpers use the same license.
