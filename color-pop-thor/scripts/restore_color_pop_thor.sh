#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/color_pop_thor_common.sh"

check_host
[[ -f "$STATE/active" ]] || fail 'No completed Color Pop Thor activation was recorded.'
[[ -f "$STATE/settings.backup" && -f "$STATE/sway.backup" ]] || fail 'The original backups are incomplete and no files were changed.'
guard_launcher_mount
lock_state
stop_frontend

# Exact comparisons prevent restoration from overwriting settings or configuration edited later.
guard_active_files

settings_temp=$(mktemp "$SETTINGS.color-pop-thor.XXXXXX")
sway_temp=$(mktemp "$SWAY_CONFIG.color-pop-thor.XXXXXX")
cp -p "$STATE/settings.backup" "$settings_temp"
cp -p "$STATE/sway.backup" "$sway_temp"

if owns_launcher_mount; then
    umount "$LAUNCHER_TARGET"
fi
mv "$settings_temp" "$SETTINGS"
mv "$sway_temp" "$SWAY_CONFIG"

# Retaining the generated fragment alongside its record keeps recovery inspectable without deleting data.
mv "$SWAY_FRAGMENT" "$STATE/restored.fragment"
mv "$STATE/active" "$STATE/restored"
start_frontend

say 'Restored the original theme settings, Sway configuration, and ROCKNIX launcher.'
say "Backups and the generated fragment remain in $STATE."
