#!/usr/bin/env bash
# Day 07 - keep an untouched copy of the supplied dataset.
#
#   bash preserve_raw.sh /path/to/supplied/dataset      copy into data/raw, fingerprint, lock
#   bash preserve_raw.sh --verify data/raw              re-check every fingerprint
#
# Behaviour (as described in DAY_07.MD s1):
#   * refuses to run if data/raw already holds files, so a second run cannot
#     quietly overwrite the first copy
#   * writes SHA256SUMS next to the files - that file, not the permission bit,
#     is the real protection (an admin can still overwrite read-only files)
#   * removes write permission from everything it copied
#
# Provenance: described on Day 07, never committed; written 2026-09-11 to do
# exactly what that description says. Run from the repository root.
set -euo pipefail

DEST="data/raw"

if [[ "${1:-}" == "--verify" ]]; then
    DIR="${2:-$DEST}"
    [[ -f "$DIR/SHA256SUMS" ]] || { echo "no SHA256SUMS in $DIR"; exit 1; }
    ( cd "$DIR" && sha256sum -c SHA256SUMS ) && echo "All files match. The raw copy is untouched."
    exit
fi

SRC="${1:?usage: preserve_raw.sh <source-folder> | --verify [dir]}"
[[ -d "$SRC" ]] || { echo "source folder not found: $SRC"; exit 1; }
if [[ -d "$DEST" ]] && [[ -n "$(ls -A "$DEST" 2>/dev/null)" ]]; then
    echo "$DEST already holds files. Refusing to overwrite the raw copy."; exit 1
fi

mkdir -p "$DEST"
cp -p "$SRC"/* "$DEST"/
( cd "$DEST" && sha256sum * > SHA256SUMS )
chmod -R a-w "$DEST"
echo "copied $(ls "$DEST" | grep -vc SHA256SUMS) file(s) to $DEST, fingerprinted, write permission removed:"
cat "$DEST/SHA256SUMS"
echo
echo "Before any run whose numbers you will report:  bash preserve_raw.sh --verify $DEST"
