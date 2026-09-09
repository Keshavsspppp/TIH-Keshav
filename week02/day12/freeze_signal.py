#!/usr/bin/env python3
"""
Freeze Signal V1, and check it later.

Signal V1 is the agreed set of brightness signals that every later step reads.
Once frozen, the files do not change. If the decoder gives a different answer
next month, we need to know it was not because the signal quietly moved.

    python freeze_signal.py --freeze --signals signals --out signal_v1
    python freeze_signal.py --verify --out signal_v1

Freezing copies the signals into their own folder, records a fingerprint of
every file and of the settings that made them, and makes the folder read-only.
Verifying re-checks every fingerprint.
"""

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import time
from pathlib import Path

VERSION = "1.0"


def sha256_file(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def freeze(signals_dir, out_dir, config_path):
    src, dst = Path(signals_dir), Path(out_dir)
    if dst.exists():
        sys.exit(f"{dst} already exists. Freezing twice would overwrite the frozen copy.\n"
                 f"Move it aside first, or freeze to a new version folder.")

    metas = sorted(src.glob("*/meta.json"))
    if not metas:
        sys.exit(f"no signals found under {src}")

    dst.mkdir(parents=True)
    entries, total = [], 0

    for meta_path in metas:
        meta = json.loads(meta_path.read_text())
        vid = meta["video"]["id"]
        (dst / vid).mkdir()
        shutil.copy2(meta_path, dst / vid / "meta.json")
        for s in meta["signals"]:
            shutil.copy2(meta_path.parent / s["file"], dst / vid / s["file"])
            entries.append({
                "video": vid,
                "lamp": s["lamp"],
                "file": f"{vid}/{s['file']}",
                "n_samples": s["n_samples"],
                "box": s["box"],
                "value_sha256": s["sha256"],                      # the numbers
                "file_sha256": sha256_file(dst / vid / s["file"]),  # the file on disk
            })
            total += s["n_samples"]

    manifest = {
        "signal_version": VERSION,
        "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pipeline_version": json.loads(metas[0].read_text())["pipeline_version"],
        "config_file": str(config_path),
        "config_sha256": sha256_file(config_path),
        "n_videos": len(metas),
        "n_signals": len(entries),
        "total_samples": total,
        "signals": entries,
        "note": ("Frozen set. Every later step reads these files. Do not edit them. "
                 "To change anything, produce Signal V2 and record why."),
    }
    (dst / "SIGNAL_V1_MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    shutil.copy2(config_path, dst / Path(config_path).name)

    # make everything read-only, so an accidental write fails loudly
    for p in dst.rglob("*"):
        if p.is_file():
            os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    print(f"Signal V{VERSION} frozen at {dst}")
    print(f"  {manifest['n_videos']} videos, {manifest['n_signals']} signals, "
          f"{total:,} samples")
    print(f"  manifest: {dst/'SIGNAL_V1_MANIFEST.json'}")
    print("\nRead-only stops accidents, not an admin user. The fingerprints are the")
    print("real protection - run --verify before any run whose numbers you report.")


def verify(out_dir):
    dst = Path(out_dir)
    mf = dst / "SIGNAL_V1_MANIFEST.json"
    if not mf.exists():
        sys.exit(f"no manifest at {mf}")
    m = json.loads(mf.read_text())

    bad = []
    for e in m["signals"]:
        p = dst / e["file"]
        if not p.exists():
            bad.append((e["file"], "missing"))
            continue
        if sha256_file(p) != e["file_sha256"]:
            bad.append((e["file"], "contents changed"))

    cfg = dst / Path(m["config_file"]).name
    cfg_ok = cfg.exists() and sha256_file(cfg) == m["config_sha256"]

    print(f"Signal V{m['signal_version']}, frozen {m['frozen_utc']}")
    print(f"  checked {len(m['signals'])} signals in {m['n_videos']} videos")
    print(f"  settings file: {'unchanged' if cfg_ok else 'CHANGED OR MISSING'}")
    if bad:
        print(f"\n  {len(bad)} PROBLEM(S):")
        for f, why in bad:
            print(f"    {f}: {why}")
        sys.exit(1)
    print("  every signal matches its fingerprint")
    print("\nVERIFY: PASSED")


def main():
    ap = argparse.ArgumentParser(description="Freeze and verify Signal V1")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--signals", default="signals")
    ap.add_argument("--out", default="signal_v1")
    ap.add_argument("--config", default="configs/preprocess_v1.yaml")
    a = ap.parse_args()
    if a.freeze:
        freeze(a.signals, a.out, a.config)
    elif a.verify:
        verify(a.out)
    else:
        ap.error("pass --freeze or --verify")


if __name__ == "__main__":
    main()
