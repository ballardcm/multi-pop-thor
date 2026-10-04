#!/bin/sh
set -eu

# Unversioned aliases make the compiler resolve every runtime library from the Thor collection instead of the builder's older system libraries.
for library in /work/private/target-libs/*.so.*; do
    name=${library##*/}
    ln -sfn "$name" "/work/private/target-libs/${name%%.so.*}.so"
done

# The matching public headers retain the stock joystick identity branch, while the installed platform configuration keeps the native Linux ABI.
cp -p /usr/include/aarch64-linux-gnu/SDL2/_real_SDL_config.h /work/private/SDL2-headers/SDL_config.h
cp -p /usr/include/SDL2/SDL_mixer.h /work/private/SDL2-headers/SDL_mixer.h

# Keeping generated compiler files private prevents the preserved stock constants from entering the reviewable source patch.
DEVICE=SM8550 cmake \
    -S /work/emulationstation-next-cada856d86e3115fbbf0bce09dd761b0ee8fa9fd \
    -B /work/private/cmake-build \
    -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DROCKNIX=1 \
    -DDISABLE_KODI=1 \
    -DENABLE_FILEMANAGER=0 \
    -DCEC=0 \
    -DENABLE_PULSE=1 \
    -DUSE_SYSTEM_PUGIXML=0 \
    -DGLES3=1 \
    -DBUILD_SHARED_LIBS=OFF \
    -DCMAKE_SKIP_RPATH=ON \
    '-DCMAKE_CXX_STANDARD_LIBRARIES=/usr/lib/aarch64-linux-gnu/libc_nonshared.a /work/private/target-libs/ld-linux-aarch64.so.1' \
    '-DCMAKE_EXE_LINKER_FLAGS=-L/work/private/target-libs -Wl,-rpath-link,/work/private/target-libs' \
    -DALSA_LIBRARY=/work/private/target-libs/libasound.so.2 \
    -DCURL_LIBRARY_RELEASE=/work/private/target-libs/libcurl.so.4 \
    -DFREETYPE_LIBRARY_RELEASE=/work/private/target-libs/libfreetype.so.6 \
    -DFreeImage_LIBRARY_REL=/work/private/target-libs/libfreeimage.so.3 \
    -DFreeImage_LIBRARY_DBG=/work/private/target-libs/libfreeimage.so.3 \
    -DOPENGLES3_gl_LIBRARY=/work/private/target-libs/libGLESv2.so.2 \
    -DPULSEAUDIO_LIBRARY=/work/private/target-libs/libpulse.so.0 \
    -DSDL2_INCLUDE_DIR=/work/private/SDL2-headers \
    -DSDLMIXER_INCLUDE_DIR=/work/private/SDL2-headers \
    -DSDL2_LIBRARY=/work/private/target-libs/libSDL2-2.0.so.0 \
    -DSDLMIXER_LIBRARY=/work/private/target-libs/libSDL2_mixer-2.0.so.0 \
    -DUDEV_LIBRARY=/work/private/target-libs/libudev.so.1
cmake --build /work/private/cmake-build --target emulationstation --parallel 4
mkdir -p /work/artifacts
cp /work/emulationstation-next-cada856d86e3115fbbf0bce09dd761b0ee8fa9fd/emulationstation /work/artifacts/emulationstation
strip --strip-unneeded /work/artifacts/emulationstation
readelf -h /work/artifacts/emulationstation
readelf -d /work/artifacts/emulationstation
