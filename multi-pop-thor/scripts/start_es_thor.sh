#!/bin/bash
# SPDX-License-Identifier: GPL-2.0-or-later
# Copyright (C) 2024 ROCKNIX (https://github.com/ROCKNIX)

# The explicit path keeps ROCKNIX setup available when this file is bind-mounted onto its launcher.
. /usr/bin/es_settings

# A compatible optional frontend supplies the Thor popup fixes while the system frontend remains available.
multi_pop_binary=/usr/bin/emulationstation
for multi_pop_root in /roms/themes/multi-pop-thor /storage/.config/emulationstation/themes/multi-pop-thor; do
    if [ -x "$multi_pop_root/frontend/emulationstation" ]; then
        multi_pop_binary="$multi_pop_root/frontend/emulationstation"
        break
    fi
done

# The hidden 1240-pixel margin centers native menus on the Thor's upper display.
exec "$multi_pop_binary" --log-path /var/log --no-splash --resolution 4400 1080
