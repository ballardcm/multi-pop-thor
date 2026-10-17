#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/multi_pop_thor_common.sh"

check_host
[[ -f "$STATE/active" ]] || fail 'No completed Multi Pop Thor activation was recorded.'
[[ -f "$STATE/settings.backup" && -f "$STATE/sway.backup" ]] || fail 'The original backups are incomplete and no files were changed.'
guard_launcher_mount
guard_startup_override
lock_state
stop_frontend

[[ -f "$STATE/installed.settings" && -f "$STATE/installed.sway" ]] || fail "The activation record is incomplete. Inspect backups in $STATE."
remove_startup_override

# Only the settings activation or theme selection changed are put back, so anything changed since then survives restore.
# A key is reverted only while it still holds Multi Pop's value; one changed again since is a later choice and is kept.
settings_temp=$(mktemp "$SETTINGS.multi-pop-thor.XXXXXX")
cp -p "$SETTINGS" "$settings_temp"
awk '
    BEGIN {
        set["FullScreenMenu"] = "false"; set["GameTransitionStyle"] = "fade"
        set["ThemeSet"] = "multi-pop-thor"; set["GamelistViewStyle"] = "gamecarousel"
    }
    function key_of(line,    found) {
        if (!match(line, /name[[:space:]]*=[[:space:]]*"[^"]*"/)) return ""
        found = substr(line, RSTART, RLENGTH)
        sub(/^name[[:space:]]*=[[:space:]]*"/, "", found)
        sub(/"$/, "", found)
        return (found in set) ? found : ""
    }
    function value_of(line,    found) {
        if (!match(line, /value[[:space:]]*=[[:space:]]*"[^"]*"/)) return ""
        found = substr(line, RSTART, RLENGTH)
        sub(/^value[[:space:]]*=[[:space:]]*"/, "", found)
        sub(/"$/, "", found)
        return found
    }
    FNR == NR { key = key_of($0); if (key != "") original[key] = $0; next }
    {
        key = key_of($0)
        if (key != "" && value_of($0) == set[key]) {
            # A key the original file lacked is removed, which returns it to the frontend default.
            if (key in original) print original[key]
            next
        }
        print
    }
' "$STATE/settings.backup" "$SETTINGS" > "$settings_temp" || fail "Settings were preserved. Inspect the diagnostic file $settings_temp."

# An unedited display configuration returns to the saved original; an edited one keeps its edits and loses only the include.
sway_temp=$(mktemp "$SWAY_CONFIG.multi-pop-thor.XXXXXX")
if cmp -s "$SWAY_CONFIG" "$STATE/installed.sway" || cmp -s "$SWAY_CONFIG" "$STATE/sway.backup"; then
    cp -p "$STATE/sway.backup" "$sway_temp"
    SWAY_KEPT=false
else
    cp -p "$SWAY_CONFIG" "$sway_temp"
    grep -Fxv -e "$INCLUDE_LINE" -e '# The Multi Pop Thor fragment keeps the dual-screen layout separate from the base configuration.' \
        "$SWAY_CONFIG" > "$sway_temp" || true
    SWAY_KEPT=true
fi

if owns_launcher_mount; then
    umount "$LAUNCHER_TARGET"
fi
mv "$settings_temp" "$SETTINGS"
mv "$sway_temp" "$SWAY_CONFIG"

# Retaining the generated fragment alongside its record keeps recovery inspectable without deleting data.
if [[ -e "$SWAY_FRAGMENT" ]]; then
    mv "$SWAY_FRAGMENT" "$STATE/restored.fragment"
fi
mv "$STATE/active" "$STATE/restored"
start_frontend

say 'Restored your previous theme and the ROCKNIX launcher. Settings changed since activation were kept.'
if [[ "$SWAY_KEPT" == true ]]; then
    say 'The display configuration had changed, so only the Multi Pop include was removed. Reboot to return to the ROCKNIX layout.'
fi
say "Backups and the generated fragment remain in $STATE."
