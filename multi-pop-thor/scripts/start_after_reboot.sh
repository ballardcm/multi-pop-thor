#!/bin/bash
set -euo pipefail

# Other themes keep the normal frontend so choosing a theme does not require removing this hook.
if ! grep -q 'name="ThemeSet" value="multi-pop-thor"' /storage/.config/emulationstation/es_settings.cfg; then
    . /usr/bin/es_settings
    exec /usr/bin/emulationstation --log-path /var/log --no-splash
fi

# ROCKNIX regenerates this configuration at boot, so restore the Thor display and touch layout.
config=/storage/.config/sway/config
fragment=/storage/.config/sway/multi-pop-thor.conf
launcher=/roms/themes/multi-pop-thor/scripts/start_es_thor.sh
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
if ! grep -Fxq 'include "/storage/.config/sway/multi-pop-thor.conf"' "$staged"; then
    printf '\n# The separate Thor fragment restores the theme viewport after ROCKNIX startup.\ninclude "/storage/.config/sway/multi-pop-thor.conf"\n' >> "$staged"
fi
if ! cmp -s "$config" "$staged"; then
    # Preserve each generated configuration before changing its display and lower-touchscreen directives.
    cp -p "$config" "/storage/.config/multi-pop-thor/sway-before-startup-$(date -u +%Y%m%dT%H%M%SZ).conf"
    chmod 644 "$staged"
    mv "$staged" "$config"
fi
swaymsg reload >/dev/null
swaymsg 'output * power on' >/dev/null
for panel in /sys/class/backlight/*; do
    [[ -f "$panel/bl_power" ]] && printf '0\n' > "$panel/bl_power"
done
exec "$launcher"
