# Color Pop for AYN Thor

Color Pop is a ROCKNIX EmulationStation theme with a gameplay preview and game details on the upper display and a three-cover browser on the lower display. Every system in the latest live Thor audit has its own color, original hardware illustration, and matching lower card. Virtual Boy is also included. Missing cover art falls back to the game's image, then to a labeled card for that system.

The upper display is 1920×1080 and the lower display is 1240×1080. The theme uses a 4400×1080 virtual canvas with a hidden 1240px margin so native menus stay centered on the upper display. It is intended for the Thor's ROCKNIX frontend, rather than ES-DE on Android.

## Install

1. Copy the complete `color-pop-thor` folder into `/roms/themes/` or `/storage/.config/emulationstation/themes/`.
2. If the previous Thor theme runs automatically at startup, turn off that startup entry first. Its helper selects its own theme again whenever it runs.
3. From a terminal on the Thor, run:

   ```sh
   bash \
     /roms/themes/color-pop-thor/scripts/enable_color_pop_thor.sh \
     --prepare
   ```

The helper verifies both displays, saves the original settings and Sway configuration, and adds a separate layout fragment. With `--prepare`, it restarts the frontend while preserving the current theme selection. Select `color-pop-thor` in EmulationStation's Theme Set menu afterward. Running the helper without that flag also selects Color Pop. If another theme's launcher is already mounted, the helper preserves it and stops; disable that theme's startup entry and reboot before activating Color Pop.

The launcher mount lasts until reboot. Run the helper with `--prepare` again after reboot to restore the full two-screen canvas while keeping the selected theme. Automatic startup has not been configured.

## Artwork and controls

The carousel prefers `<thumbnail>` cover art and falls back to `<image>` when needed. The upper display uses `<image>` for a gameplay screenshot, with the title, genre, publisher, year, and description beside it when available. After three seconds, an available `<video>` replaces the screenshot with audio off. One media component owns both phases, so game artwork cannot overlap the system card. Media keeps its original proportions, and absent metadata stays blank.

The footer follows ROCKNIX's default button mapping: A selects a system or plays a game, and B returns from the game browser. On the system browser, B opens system navigation and START opens the menu. If you invert the A/B preference, update the two footer text entries in `layouts/system.xml` and `layouts/games.xml`.

In the game browser, L1 moves three games left and R1 moves three games right, matching the three-cover lower carousel. Paging stops at the first or last game and keeps the current system selected. This behavior requires a compatible patched frontend and applies only to Color Pop on the Thor's 4400×1080 canvas.

The system artwork depicts recognizable original consoles, handhelds, controllers, and representative arcade cabinets. Software and collection entries have their own illustrations. Light platform colors use dark text; dark colors use white text. Menu and savestate selections use a solid purple fill with white labels.

Game media is installed separately from the theme. Existing covers remain available as thumbnails when gameplay screenshots are added. Source and creator credits accompany fetched screenshots, descriptions, and video excerpts in the media installation report.

## Restore

```sh
bash \
  /roms/themes/color-pop-thor/scripts/restore_color_pop_thor.sh
```

Restore uses the original backups in `/storage/.config/color-pop-thor/`. It accepts the theme and carousel choices saved when you manually select Color Pop. It stops if other settings or configuration have changed since activation, so newer changes are preserved. Backups remain available for manual recovery.

## Validation and credits

The XML, local asset references, screen bounds, distinct palettes, text contrast, and helper syntax have been checked. Hardware illustrations have been rendered and reviewed at upper-screen and lower-card sizes.

The tested device uses an optional frontend in `frontend/emulationstation`, rebuilt from the source revision used by ROCKNIX 20261001 on this Thor. Compiled frontends are excluded from this source repository; see [the native build notes](../frontend-build/README.md). It restricts B navigation and the savestate manager to the upper display and calculates the save row from that display's width. These changes apply only to a 4400×1080 canvas. Selection uses purple with white labels. The frontend also handles L1/R1 paging in Color Pop's game carousel.

The launcher uses this frontend when present and keeps the system frontend at `/usr/bin/emulationstation` available as a fallback. The build uses the Thor's existing libraries, preserves controller support and online integrations, and has no added library-path override. The tested compatibility report, public source patches, and license notices are retained in `frontend/`. For a different firmware release, verify compatibility before using this optional binary.

The design is inspired by [Colorful (Simplified)](https://github.com/anthonycaccese/colorful-simplified-es-de). The screen mapping follows the staged [DII-ESS-AYE Thor layout](https://github.com/beebono/dii-ess-aye), with original Color Pop graphics. No DII-ESS-AYE graphics, sounds, or fonts are included.

Roboto fonts are unmodified and include their Apache 2.0 license and notice in `assets/fonts/`. The launcher retains ROCKNIX's GPL-2.0-or-later notice; the activation and restore helpers use the same license.
