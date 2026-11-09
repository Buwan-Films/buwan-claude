#!/bin/bash
# Build a separate ffmpeg with vid.stab for the Buwan engine (smooth glide on shaky Creative/Glider shots).
# Installs into ~/.buwan/ffmpeg-vidstab; the system ffmpeg is not touched. macOS + Homebrew.
set -euo pipefail
VER=7.1.1
DEST="$HOME/.buwan/ffmpeg-vidstab"
has_vidstab() { local f; f="$("$1" -hide_banner -filters 2>/dev/null || true)"; [[ "$f" == *vidstabtransform* ]]; }   # no pipe: grep -q + pipefail misfires
if [ -x "$DEST/bin/ffmpeg" ] && has_vidstab "$DEST/bin/ffmpeg"; then
  echo "ffmpeg with vid.stab already installed: $DEST/bin/ffmpeg"; exit 0
fi
command -v brew >/dev/null || { echo "Homebrew is needed (https://brew.sh)"; exit 1; }
brew install libvidstab pkgconf
B="$HOME/.buwan/build"; mkdir -p "$B"; cd "$B"
[ -f "ffmpeg-$VER.tar.xz" ] || curl -sSLO "https://ffmpeg.org/releases/ffmpeg-$VER.tar.xz"
rm -rf "ffmpeg-$VER"; tar xf "ffmpeg-$VER.tar.xz"; cd "ffmpeg-$VER"
P="$(brew --prefix)"
./configure --prefix="$DEST" --enable-gpl --enable-version3 --enable-libvidstab --enable-videotoolbox --enable-audiotoolbox \
  --disable-doc --disable-ffplay --disable-debug --extra-cflags="-I$P/include" --extra-ldflags="-L$P/lib" > ../configure.log 2>&1
make -j"$(sysctl -n hw.ncpu)" > ../make.log 2>&1
make install > ../install.log 2>&1
has_vidstab "$DEST/bin/ffmpeg" && echo "installed: $DEST/bin/ffmpeg (vid.stab, VideoToolbox HEVC)"
