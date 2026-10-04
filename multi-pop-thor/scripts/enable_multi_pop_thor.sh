#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/multi_pop_thor_common.sh"

PREPARE_ONLY=false
case "${1-}" in
    '') [[ $# -eq 0 ]] || fail 'Usage: enable_multi_pop_thor.sh [--prepare]' ;;
    --prepare)
        [[ $# -eq 1 ]] || fail 'Usage: enable_multi_pop_thor.sh [--prepare]'
        PREPARE_ONLY=true
        ;;
    *) fail 'Usage: enable_multi_pop_thor.sh [--prepare]' ;;
esac

check_host
find_theme
verify_outputs
guard_launcher_mount
lock_state
stop_frontend

if [[ -f "$STATE/active" ]]; then
    guard_active_files
elif [[ -f "$STATE/restored" ]]; then
    # Reusing the original backups is safe only while the restored originals remain unchanged.
    cmp -s "$SETTINGS" "$STATE/settings.backup" || fail 'Settings changed after restoration; the original backup was preserved.'
    cmp -s "$SWAY_CONFIG" "$STATE/sway.backup" || fail 'Sway configuration changed after restoration; the original backup was preserved.'
    [[ ! -e "$SWAY_FRAGMENT" ]] || fail 'A supplemental configuration already exists and was preserved.'
else
    [[ ! -e "$STATE/settings.backup" && ! -e "$STATE/sway.backup" ]] || fail "Existing backups have no completed activation record. Inspect $STATE before proceeding."
    [[ ! -e "$SWAY_FRAGMENT" ]] || fail 'A supplemental configuration already exists and was preserved.'
    [[ $(awk -v fragment="$SWAY_FRAGMENT" 'index($0, fragment) { count++ } END { print count+0 }' "$SWAY_CONFIG") == 0 ]] || fail 'The Sway configuration already references the supplemental file and was preserved.'
    # These backups are created once so repeated activation cannot replace the original configuration.
    cp -p "$SETTINGS" "$STATE/settings.backup"
    cp -p "$SWAY_CONFIG" "$STATE/sway.backup"
fi

settings_temp=$(mktemp "$SETTINGS.multi-pop-thor.XXXXXX")
cp -p "$SETTINGS" "$settings_temp"
awk -v prepare="$PREPARE_ONLY" '
    BEGIN {
        keys[1] = "FullScreenMenu"; values["FullScreenMenu"] = "false"
        keys[2] = "GameTransitionStyle"; values["GameTransitionStyle"] = "fade"
        count = 2
        if (prepare != "true") {
            keys[++count] = "ThemeSet"; values["ThemeSet"] = "multi-pop-thor"
        }
    }
    {
        for (i = 1; i <= count; i++) {
            key = keys[i]
            expression = "name[[:space:]]*=[[:space:]]*\"" key "\""
            if ($0 ~ expression) {
                if ($0 !~ /^[[:space:]]*<(string|bool)[[:space:]][^>]*\/>[[:space:]]*$/ || seen[key]++) {
                    print "The settings layout or duplicate keys require inspection." > "/dev/stderr"
                    invalid = 1
                    exit 1
                }
                printf "\t<string name=\"%s\" value=\"%s\" />\n", key, values[key]
                next
            }
        }
        if ($0 ~ /^[[:space:]]*<\/config>[[:space:]]*$/) {
            for (i = 1; i <= count; i++) {
                key = keys[i]
                if (!seen[key]) printf "\t<string name=\"%s\" value=\"%s\" />\n", key, values[key]
            }
        }
        print
    }
    END { if (invalid) exit 1 }
' "$SETTINGS" > "$settings_temp" || fail "Settings were preserved. Inspect the diagnostic file $settings_temp."

fragment_temp=$(mktemp "$SWAY_FRAGMENT.XXXXXX")
cat > "$fragment_temp" <<'SWAY'
# Multi Pop Thor owns this supplemental configuration so the base configuration can be preserved.
output DSI-2 transform 90
output DSI-2 position 0 0
output DSI-1 transform 90
output DSI-1 position 1920 0
output DSI-1 power on
# ROCKNIX disables this device for its single-screen frontend, but Multi Pop browses on the lower panel.
input "0:0:bottom_touchscreen" map_to_output DSI-1
input "0:0:bottom_touchscreen" events enabled
# The virtual surface includes a hidden margin that centers native menus on the upper screen.
floating_maximum_size 4400 x 1080
for_window [app_id="^emulationstation$"] floating enable
for_window [app_id="^emulationstation$"] fullscreen disable
for_window [app_id="^emulationstation$"] resize set width 4400 px height 1080 px
for_window [app_id="^emulationstation$"] move absolute position -1240 0
SWAY

sway_temp=$(mktemp "$SWAY_CONFIG.multi-pop-thor.XXXXXX")
cp -p "$SWAY_CONFIG" "$sway_temp"
awk -v stock_exec="exec_always swaymsg '[app_id=\"emulationstation\"]' focus output DSI-2, output DSI-1 power off" '
    {
        normalized = $0
        gsub(/[[:space:]]+/, " ", normalized)
        sub(/^ /, "", normalized)
        sub(/ $/, "", normalized)
        if (normalized == "output DSI-1 power off") next
        # Remove the stock asynchronous override so it cannot disable the fragment input after reload.
        if (normalized == "exec_always swaymsg input \"0:0:bottom_touchscreen\" events disabled") next
        if (normalized == stock_exec) {
            # The stock focus command remains useful once its lower-screen power-off clause is removed.
            sub(/,[[:space:]]*output[[:space:]]+DSI-1[[:space:]]+power[[:space:]]+off[[:space:]]*$/, "")
            print
            next
        }
        if ($0 !~ /^[[:space:]]*#/ && $0 ~ /output[[:space:]]+DSI-1[[:space:]]+power[[:space:]]+off/) {
            print "An unfamiliar lower-screen power-off command requires inspection." > "/dev/stderr"
            invalid = 1
            exit 1
        }
        print
    }
    END { if (invalid) exit 1 }
' "$SWAY_CONFIG" > "$sway_temp" || fail "Sway configuration was preserved. Inspect the diagnostic file $sway_temp."
if ! awk -v include="$INCLUDE_LINE" '$0 == include { found=1 } END { exit !found }' "$sway_temp"; then
    printf '\n# The Multi Pop Thor fragment keeps the dual-screen layout separate from the base configuration.\n%s\n' "$INCLUDE_LINE" >> "$sway_temp"
fi

# The staged files are recorded before installation so a partial update remains inspectable.
cp -p "$settings_temp" "$STATE/installed.settings"
cp -p "$sway_temp" "$STATE/installed.sway"
cp -p "$fragment_temp" "$STATE/installed.fragment"
chmod 644 "$fragment_temp"
mv "$fragment_temp" "$SWAY_FRAGMENT"
mv "$settings_temp" "$SETTINGS"
mv "$sway_temp" "$SWAY_CONFIG"

chmod +x "$THEME/scripts/start_es_thor.sh"
if owns_launcher_mount; then
    umount "$LAUNCHER_TARGET"
fi
mount --bind "$THEME/scripts/start_es_thor.sh" "$LAUNCHER_TARGET"
stat -c '%d:%i' "$LAUNCHER_TARGET" > "$STATE/launcher.identity"
printf '%s\n' "$THEME" > "$STATE/theme.path"
printf 'active\n' > "$STATE/active"
start_frontend

if [[ "$PREPARE_ONLY" == true ]]; then
    say 'The dual-screen viewport is prepared. Your selected theme was preserved; choose Multi Pop Thor in the theme menu when ready.'
else
    say 'Enabled: artwork above, browsing below, and native menus on the upper screen.'
fi
say "Original settings and Sway configuration are backed up in $STATE."
if [[ "$PREPARE_ONLY" == true ]]; then
    say 'The launcher mount lasts until reboot. Run this helper with --prepare after reboot to retain your selected theme.'
else
    say 'The launcher mount lasts until reboot. Run this helper again after reboot to reactivate the full virtual surface.'
fi
