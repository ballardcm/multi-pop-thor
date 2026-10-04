#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later

set -euo pipefail

SETTINGS=/storage/.config/emulationstation/es_settings.cfg
SWAY_CONFIG=/storage/.config/sway/config
SWAY_FRAGMENT=/storage/.config/sway/color-pop-thor.conf
STATE=/storage/.config/color-pop-thor
LAUNCHER_TARGET=/usr/bin/start_es.sh
INCLUDE_LINE='include "/storage/.config/sway/color-pop-thor.conf"'
SERVICE_STOPPED=false

fail() {
    printf 'Color Pop Thor: %s\n' "$*" >&2
    exit 1
}

say() {
    printf 'Color Pop Thor: %s\n' "$*"
}

check_host() {
    [[ $EUID -eq 0 ]] || fail 'Run this helper as root on the Thor.'
    local command
    for command in awk cat chmod cmp cp grep mkdir mktemp mount mountpoint mv rmdir sed sort stat swaymsg systemctl umount; do
        command -v "$command" >/dev/null 2>&1 || fail "Required command is missing: $command."
    done
    [[ -f "$SETTINGS" ]] || fail "Settings were not found at $SETTINGS."
    [[ -f "$SWAY_CONFIG" ]] || fail "Sway configuration was not found at $SWAY_CONFIG."
    [[ -f /usr/bin/es_settings ]] || fail 'The ROCKNIX launcher setup file is missing.'
    [[ -f "$LAUNCHER_TARGET" && ! -L "$LAUNCHER_TARGET" ]] || fail 'The ROCKNIX launcher must be an existing regular file.'
    awk '
        /^[[:space:]]*<config>[[:space:]]*$/ { opening++ }
        /^[[:space:]]*<\/config>[[:space:]]*$/ { closing++ }
        END { exit !(opening == 1 && closing == 1) }
    ' "$SETTINGS" || fail 'The settings file does not have the expected single config root.'
}

find_theme() {
    local candidate
    for candidate in /roms/themes/color-pop-thor /storage/.config/emulationstation/themes/color-pop-thor; do
        if [[ -f "$candidate/theme.xml" && -f "$candidate/scripts/start_es_thor.sh" ]]; then
            THEME=$candidate
            return
        fi
    done
    fail 'Copy the complete color-pop-thor folder into /roms/themes or /storage/.config/emulationstation/themes first.'
}

verify_outputs() {
    local outputs socket
    if outputs=$(swaymsg -t get_outputs -r 2>/dev/null) && has_thor_outputs "$outputs"; then
        return
    fi
    # SSH sessions lack the compositor environment, so only a reachable Thor socket is selected.
    for socket in /run/sway-ipc.*.sock /run/user/*/sway-ipc.*.sock /var/run/*-runtime-dir/sway-ipc.*.sock /tmp/sway-ipc.*.sock; do
        [[ -S "$socket" ]] || continue
        if outputs=$(SWAYSOCK="$socket" swaymsg -t get_outputs -r 2>/dev/null) && has_thor_outputs "$outputs"; then
            export SWAYSOCK="$socket"
            return
        fi
    done
    fail 'A running Sway session with both Thor displays, DSI-2 and DSI-1, could not be reached.'
}

has_thor_outputs() {
    printf '%s\n' "$1" | awk '
        /"name"[[:space:]]*:[[:space:]]*"DSI-2"/ { upper = 1 }
        /"name"[[:space:]]*:[[:space:]]*"DSI-1"/ { lower = 1 }
        END { exit !(upper && lower) }
    '
}

owns_launcher_mount() {
    [[ -f "$STATE/launcher.identity" ]] || return 1
    mountpoint -q "$LAUNCHER_TARGET" || return 1
    [[ $(stat -c '%d:%i' "$LAUNCHER_TARGET") == "$(cat "$STATE/launcher.identity")" ]]
}

guard_launcher_mount() {
    if mountpoint -q "$LAUNCHER_TARGET" && ! owns_launcher_mount; then
        fail 'Another launcher is already mounted. Its mount has been preserved.'
    fi
}

lock_state() {
    mkdir -p "$STATE"
    mkdir "$STATE/lock" 2>/dev/null || fail 'Another activation or restore is running, or its lock needs inspection.'
    trap finish EXIT
}

finish() {
    local status=$?
    trap - EXIT
    if [[ "$SERVICE_STOPPED" == true ]]; then
        # Restarting after an error returns control to the device while preserving the diagnostic.
        systemctl start essway || printf 'Color Pop Thor: Start essway manually; the service could not be started.\n' >&2
    fi
    rmdir "$STATE/lock" 2>/dev/null || true
    exit "$status"
}

stop_frontend() {
    # Stopping first lets EmulationStation save its settings before any backup or update is made.
    systemctl stop essway
    SERVICE_STOPPED=true
}

start_frontend() {
    # A running compositor can reload immediately; a stopped one loads the fragment when its service starts.
    swaymsg reload >/dev/null 2>&1 || true
    systemctl start essway
    SERVICE_STOPPED=false
}

guard_active_files() {
    [[ -f "$STATE/installed.settings" && -f "$STATE/installed.sway" && -f "$STATE/installed.fragment" ]] || fail "The activation record is incomplete. Inspect backups in $STATE."
    if ! cmp -s "$SETTINGS" "$STATE/installed.settings"; then
        # Selecting Color Pop saves these two theme-owned choices and can reorder settings, so those changes must not block later activation or restore.
        grep -q '<string name="ThemeSet" value="color-pop-thor"' "$SETTINGS" &&
        grep -Eq '<string name="GamelistViewStyle" value="(gamecarousel)?"' "$SETTINGS" &&
        cmp -s \
            <(sed '/<string name="ThemeSet" /d; /<string name="GamelistViewStyle" /d' "$SETTINGS" | LC_ALL=C sort) \
            <(sed '/<string name="ThemeSet" /d; /<string name="GamelistViewStyle" /d' "$STATE/installed.settings" | LC_ALL=C sort) ||
            fail "Settings changed after activation. They were preserved; inspect $STATE/settings.backup before restoring."
    fi
    cmp -s "$SWAY_CONFIG" "$STATE/installed.sway" || fail "Sway configuration changed after activation. It was preserved; inspect $STATE/sway.backup before restoring."
    cmp -s "$SWAY_FRAGMENT" "$STATE/installed.fragment" || fail 'The supplemental configuration changed after activation and was preserved.'
}
