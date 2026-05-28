# syntax=docker/dockerfile:1.7
#
# 1C:Enterprise 8.3.27 training (учебная) platform on Ubuntu 22.04
# with the file-mode infobase restored from a .dt dump and the
# ROCTUP MCP_Toolkit (Linux build) embedded so it can serve on port 6003.
#
# Build context is passed via named build contexts (see build.ps1):
#   distro=C:\distr\1c\platform\linux   (contains setup-training-*.run)
#   db    =C:\Work\projects\sberdevices\dev\1cbench   (contains 1Cv8full.dt)
# The MCP toolkit .epf is local under ./payload/.

ARG ONEC_VERSION=8.3.27.2130

# ---------------------------------------------------------------------------
# Stage 1: runtime-base — all Ubuntu packages 1C needs at runtime + build time
# ---------------------------------------------------------------------------
FROM ubuntu:22.04 AS runtime-base

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=ru_RU.UTF-8 \
    LC_ALL=ru_RU.UTF-8 \
    LANGUAGE=ru_RU:ru \
    TZ=Europe/Moscow

RUN echo "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" \
      | debconf-set-selections \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
        ca-certificates locales tzdata curl \
        libfontconfig1 libfreetype6 \
        libgsf-1-114 libglib2.0-0 \
        libwebkit2gtk-4.0-37 libjavascriptcoregtk-4.0-18 \
        libicu70 libenchant-2-2 libsecret-1-0 \
        libodbc1 unixodbc \
        imagemagick \
        ttf-mscorefonts-installer fonts-liberation fonts-dejavu \
        xfonts-base xfonts-utils xfonts-75dpi xfonts-100dpi \
        libxext6 libxrender1 libxtst6 libxi6 libxrandr2 libxcursor1 \
        libxfixes3 libxcomposite1 libxdamage1 libxinerama1 libxss1 libxkbcommon0 \
        libglu1-mesa libgl1 \
        libnss3 libgtk-3-0 libpangocairo-1.0-0 libatk1.0-0 libatk-bridge2.0-0 \
        libcups2 libdrm2 libgbm1 libasound2 \
        dbus-x11 xvfb xdotool x11-utils iproute2 \
 && rm -rf /var/lib/apt/lists/* \
 && sed -i '/ru_RU.UTF-8/s/^# //' /etc/locale.gen \
 && locale-gen \
 && fc-cache -fv

# ---------------------------------------------------------------------------
# Stage 2: oneconfig — run the unattended 1C installer
# ---------------------------------------------------------------------------
FROM runtime-base AS oneconfig
ARG ONEC_VERSION

RUN --mount=type=bind,from=distro,target=/distro \
    set -eux; \
    runfile="$(ls /distro/setup-training-*-x86_64.run | head -1)"; \
    cp "$runfile" /tmp/install.run; \
    chmod +x /tmp/install.run; \
    # BitRock InstallBuilder unattended invocation.
    # xvfb-run is a safety net: the bundled JavaFX wizard probes for a display.
    xvfb-run -a /tmp/install.run \
        --mode unattended \
        --unattendedmodeui none \
        --installer-language en \
        --debugtrace /tmp/install.log \
    || { echo "=== installer log ==="; cat /tmp/install.log 2>/dev/null || true; \
         echo "=== /opt contents ==="; ls -laR /opt 2>/dev/null || true; \
         exit 1; }; \
    rm -f /tmp/install.run; \
    # Training edition installs binaries with a trailing "t" (1cv8t = thick client,
    # 1cv8ct = thin client, 1cv8st = server). Regular edition uses 1cv8 / 1cv8c / 1cv8s.
    bin="$(find /opt -type f \( -name 1cv8 -o -name 1cv8t \) -executable | head -1)"; \
    test -n "$bin" || { echo "1cv8 binary not found after install"; ls -laR /opt 2>/dev/null | head -100; exit 1; }; \
    bindir="$(dirname "$bin")"; \
    echo "Installed 1cv8 at: $bin (dir=$bindir)"; \
    # Expose both training and regular names as /usr/local/bin/1cv8 so the rest
    # of the image doesn't need to care which edition got installed.
    ln -sf "$bin" /usr/local/bin/1cv8; \
    [ -x "$bindir/1cv8c" ]  && ln -sf "$bindir/1cv8c"  /usr/local/bin/1cv8c  || true; \
    [ -x "$bindir/1cv8ct" ] && ln -sf "$bindir/1cv8ct" /usr/local/bin/1cv8c  || true; \
    echo "$bindir" > /opt/1cv8.path

# ---------------------------------------------------------------------------
# Stage 3: ibrestore — create empty file IB and restore from .dt dump
# ---------------------------------------------------------------------------
FROM oneconfig AS ibrestore
ARG ONEC_VERSION

ENV HOME=/root \
    IB_PATH=/var/1c/ib

RUN mkdir -p /var/1c/ib /var/log/1c /root/.1cv8

RUN --mount=type=bind,from=db,source=1Cv8_no_users.dt,target=/tmp/dump.dt \
    set -eux; \
    cd /root; \
    # Create empty file infobase
    xvfb-run -a /usr/local/bin/1cv8 CREATEINFOBASE \
        "File=\"$IB_PATH\";Locale=\"ru_RU\";" \
        /DisableStartupMessages /DisableStartupDialogs \
        /Out /var/log/1c/create.log \
        || { echo "--- create.log ---"; cat /var/log/1c/create.log 2>/dev/null; exit 1; }; \
    # Restore from .dt dump
    xvfb-run -a /usr/local/bin/1cv8 DESIGNER \
        /F"$IB_PATH" \
        /RestoreIB"/tmp/dump.dt" \
        /DisableStartupMessages /DisableStartupDialogs \
        /Out /var/log/1c/restore.log \
        || { echo "--- restore.log ---"; cat /var/log/1c/restore.log 2>/dev/null; exit 1; }; \
    cat /var/log/1c/restore.log; \
    ls -la "$IB_PATH"

# ---------------------------------------------------------------------------
# Stage 4: final — bake the MCP toolkit and entrypoint
# ---------------------------------------------------------------------------
FROM ibrestore AS final
ARG ONEC_VERSION

# Tiny window manager (xdotool key delivery under Xvfb needs one) plus
# x11vnc so a human can connect through VNC and click "Подключиться" when
# auto-click misses (the bench MCP form is long and the button isn't where
# blind Tab*N lands).
RUN apt-get update \
 && apt-get install -y --no-install-recommends fluxbox x11vnc \
 && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/mcp
# payload/MCP_Toolkit.epf is the upstream .epf with our headless-autostart
# branch spliced into the form module by repack_form_module.py. build.ps1
# runs the repack before `docker build` so the file is fresh on each build.
COPY payload/MCP_Toolkit.epf /opt/mcp/MCP_Toolkit.epf
COPY --chmod=0755 entrypoint.sh /usr/local/bin/entrypoint.sh

# Normalize entrypoint line endings in case it was written CRLF on the host
RUN sed -i 's/\r$//' /usr/local/bin/entrypoint.sh

ENV ONEC_VERSION=${ONEC_VERSION} \
    IB_PATH=/var/1c/ib \
    MCP_EPF=/opt/mcp/MCP_Toolkit.epf \
    MCP_PORT=6003

EXPOSE 6003 5900
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
