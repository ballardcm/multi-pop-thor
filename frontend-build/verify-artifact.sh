#!/bin/sh
set -eu

# These inventories contain only public ELF metadata, so they can be retained after private compiler files are removed.
readelf --dyn-syms --wide /work/artifacts/emulationstation > /work/artifacts/dynamic-symbols.txt
readelf --version-info /work/artifacts/emulationstation > /work/artifacts/symbol-versions.txt
readelf -d /work/artifacts/emulationstation > /work/artifacts/dynamic-dependencies.txt
readelf -l /work/artifacts/emulationstation > /work/artifacts/program-headers.txt
/work/private/target-libs/ld-linux-aarch64.so.1 \
    --library-path /work/private/target-libs \
    --list /work/artifacts/emulationstation > /work/artifacts/loader-check.txt
/work/private/target-libs/ld-linux-aarch64.so.1 \
    --library-path /work/private/target-libs \
    /work/artifacts/emulationstation --help > /work/artifacts/help-check.txt
