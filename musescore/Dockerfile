FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8

ARG MUSESCORE_URL="https://github.com/musescore/MuseScore/releases/download/v4.7.2/MuseScore-Studio-4.7.2.260525085-x86_64.AppImage"

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        wget \
        xvfb \
        xauth \
        libasound2t64 \
        libjack-jackd2-0 \
        libnss3 \
        libpipewire-0.3-0t64 \
        libopengl0 \
        libgl1 \
        libegl1 \
        libdbus-1-3 \
        libfontconfig1 \
        libfreetype6 \
        libglib2.0-0t64 \
        libxkbcommon0 \
        libxkbcommon-x11-0 \
        libxcb1 \
        libxcb-cursor0 \
        libx11-6 \
        libxext6 \
        libxi6 \
        libxrender1 \
        libxrandr2 \
    && rm -rf /var/lib/apt/lists/*

RUN wget -O /tmp/musescore.AppImage "$MUSESCORE_URL" \
    && chmod +x /tmp/musescore.AppImage \
    && cd /opt \
    && /tmp/musescore.AppImage --appimage-extract \
    && mv squashfs-root musescore \
    && rm /tmp/musescore.AppImage

WORKDIR /repo

COPY entrypoint.sh /usr/local/bin/musescore-entrypoint
RUN chmod +x /usr/local/bin/musescore-entrypoint

ENTRYPOINT ["/usr/local/bin/musescore-entrypoint"]
