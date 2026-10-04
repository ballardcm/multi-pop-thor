FROM ubuntu:22.04

# The older ARM64 userspace keeps the resulting binary's libc and C++ requirements below the Thor's installed runtime.
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential cmake ninja-build pkg-config gettext \
        libsdl2-dev libsdl2-mixer-dev libfreeimage-dev libfreetype6-dev \
        libcurl4-openssl-dev rapidjson-dev libasound2-dev \
        libgles2-mesa-dev libudev-dev libpulse-dev libvlc-dev \
        libvlccore-dev binutils ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /work
