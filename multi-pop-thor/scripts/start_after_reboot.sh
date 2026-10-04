#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "$0")" && pwd)
. "$SCRIPT_DIR/multi_pop_thor_common.sh"

# A fresh --prepare activation owns a live mount and needs the full canvas for theme selection.
# After reboot that mount is gone, so other themes return to the normal frontend.
if ! grep -q 'name="ThemeSet" value="multi-pop-thor"' /storage/.config/emulationstation/es_settings.cfg && ! owns_launcher_mount; then
    . /usr/bin/es_settings
    exec /usr/bin/emulationstation --log-path /var/log --no-splash
fi

# ROCKNIX regenerates this configuration at boot, so restore the Thor display and touch layout.
config=/storage/.config/sway/config
fragment=/storage/.config/sway/multi-pop-thor.conf
find_theme
launcher="$THEME/scripts/start_es_thor.sh"
[[ -f "$fragment" && -x "$launcher" ]]
export SWAYSOCK=/run/0-runtime-dir/sway-ipc.0.sock
for attempt in {1..30}; do
    [[ -S "$SWAYSOCK" ]] && swaymsg -t get_outputs >/dev/null 2>&1 && break
    sleep 1
done
swaymsg -t get_outputs >/dev/null
staged=$(mktemp "$config.multi-pop-startup.XXXXXX")
trap 'rm -f "$staged"' EXIT
awk '
    /^[[:space:]]*output DSI-1 power off[[:space:]]*$/ { next }
    /^[[:space:]]*exec_always[[:space:]]+swaymsg[[:space:]]+input[[:space:]]+"0:0:bottom_touchscreen"[[:space:]]+events[[:space:]]+disabled[[:space:]]*$/ { next }
    /^exec_always swaymsg/ {
        sub(/,[[:space:]]*output DSI-1 power off[[:space:]]*$/, "")
    }
    { print }
' "$config" > "$staged"
if ! grep -Fxq "$INCLUDE_LINE" "$staged"; then
    printf '\n# The Multi Pop Thor fragment keeps the dual-screen layout separate from the base configuration.\n%s\n' "$INCLUDE_LINE" >> "$staged"
fi
if ! cmp -s "$config" "$staged"; then
    # Preserve each generated configuration before changing its display and lower-touchscreen directives.
    cp -p "$config" "/storage/.config/multi-pop-thor/sway-before-startup-$(date -u +%Y%m%dT%H%M%SZ).conf"
    chmod 644 "$staged"
    mv "$staged" "$config"
fi
# A file bind mount disappears at reboot; recording its new identity also keeps updates and restoration usable.
guard_launcher_mount
if ! owns_launcher_mount; then
    mount --bind "$launcher" "$LAUNCHER_TARGET"
    stat -c '%d:%i' "$LAUNCHER_TARGET" > "$STATE/launcher.identity"
fi
swaymsg reload >/dev/null
swaymsg 'output * power on' >/dev/null
for panel in /sys/class/backlight/*; do
    [[ -f "$panel/bl_power" ]] && printf '0\n' > "$panel/bl_power"
done
exec "$launcher"
