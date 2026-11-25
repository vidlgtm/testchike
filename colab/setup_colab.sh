#!/usr/bin/env bash
# FIXED. One-time machine setup for a Colab T4 runtime (Ubuntu 22.04): Node 20, ffmpeg, Chrome's Linux libs,
# the NVIDIA *graphics* userspace (Vulkan/EGL - Colab only ships the compute half), Python deps.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
cd "$(dirname "$0")/.."

echo "== apt packages"
apt-get update -qq
apt-get install -y -qq ffmpeg build-essential curl ca-certificates gnupg libvulkan1 vulkan-tools libnss3 libdbus-1-3 \
  libatk1.0-0 libxrandr2 libxkbcommon-dev libxfixes3 libxcomposite1 libxdamage1 libcups2 libgbm-dev \
  libpangocairo-1.0-0 libatk-bridge2.0-0 > /dev/null
apt-get install -y -qq libasound2 > /dev/null 2>&1 || apt-get install -y -qq libasound2t64 > /dev/null

echo "== Node 20"
if ! node -v 2>/dev/null | grep -q '^v2[0-9]'; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null
  apt-get install -y -qq nodejs > /dev/null
fi
node -v

echo "== NVIDIA graphics userspace (must match the Colab driver exactly)"
FULL=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1 | tr -d ' ')
MAJOR=${FULL%%.*}
echo "driver $FULL"
if ! ls /usr/share/vulkan/icd.d/nvidia_icd.json > /dev/null 2>&1; then
  apt-get install -y -qq "libnvidia-gl-${MAJOR}" > /dev/null 2>&1 \
  || apt-get install -y -qq "libnvidia-gl-${MAJOR}-server" > /dev/null 2>&1 \
  || {
    echo "apt has no libnvidia-gl-${MAJOR}: installing the userspace part of the exact ${FULL} driver"
    curl -fsSL -o /tmp/nv.run "https://us.download.nvidia.com/tesla/${FULL}/NVIDIA-Linux-x86_64-${FULL}.run" \
      || curl -fsSL -o /tmp/nv.run "https://us.download.nvidia.com/XFree86/Linux-x86_64/${FULL}/NVIDIA-Linux-x86_64-${FULL}.run"
    sh /tmp/nv.run --no-kernel-module --silent --no-questions --no-backup --no-check-for-alternate-installs > /tmp/nv_install.log 2>&1 \
      || { tail -20 /tmp/nv_install.log; echo "!! userspace driver install failed"; }
  }
fi
mkdir -p /usr/share/glvnd/egl_vendor.d /usr/share/vulkan/icd.d
[ -f /usr/share/glvnd/egl_vendor.d/10_nvidia.json ] || echo '{"file_format_version":"1.0.0","ICD":{"library_path":"libEGL_nvidia.so.0"}}' > /usr/share/glvnd/egl_vendor.d/10_nvidia.json
/etc/init.d/dbus start > /dev/null 2>&1 || true
vulkaninfo --summary 2>&1 | grep -iE "deviceName|driverName" | head -4 || true

echo "== Python packages"
pip install -q numpy scipy pillow edge-tts faster-whisper

echo "== npm ci"
npm ci --no-audit --no-fund --loglevel=error

echo "== Chrome for Testing (the flavour that can use the GPU)"
npx remotion browser ensure --chrome-mode=chrome-for-testing
echo "setup done"
