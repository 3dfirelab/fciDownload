#!/usr/bin/env python3
"""
make_sidecar.py   – create /metadata/<filename>.json for a freshly-encoded WebM

Usage
------
python make_sidecar.py /absolute/path/to/rgb.webm
python make_sidecar.py /absolute/path/to/ir38.webm
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

#######################################################################
# Helper functions
#######################################################################
def ffprobe_tags(video: Path) -> dict:
    """Return the full `format -> tags` dict from ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "format=start_time:format_tags",
        "-of", "json",
        str(video)
    ]
    data = subprocess.check_output(cmd, text=True)
    fmt = json.loads(data)["format"]
    return fmt.get("tags", {}), float(fmt.get("start_time", "0")), float(fmt.get("duration", "0"))

def start_tag_from_start_time(start_secs: float) -> str:
    """
    Convert a numeric UTC start-time (seconds) to the SILEX tag format
    YYYYDDDThhmmZ  (e.g. 2025160T1900Z).
    """
    dt = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=start_secs)
    year = dt.year
    doy = (dt - datetime(year, 1, 1, tzinfo=timezone.utc)).days + 1
    return f"{year}{doy:03d}T{dt:%H%M}Z"

#######################################################################
# Main
#######################################################################
def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python make_sidecar.py path/to/file.webm")

    video = Path(sys.argv[1]).resolve()
    if not video.exists():
        sys.exit(f"File not found: {video}")

    tags, native_start, native_dur = ffprobe_tags(video)

    # Prefer tags if they exist, otherwise derive
    real_start = tags.get("REAL_START_TIME") or start_tag_from_start_time(native_start)
    real_dur   = int(tags.get("REAL_DURATION") or round(native_dur))

    sidecar_data = {
        "REAL_START_TIME": real_start,
        "REAL_DURATION":   real_dur
    }

    # Make sure /metadata/ exists alongside the video root
    meta_dir = video.parent / "metadata"
    meta_dir.mkdir(exist_ok=True)

    out_path = meta_dir / f"{video.name}.json"
    out_path.write_text(json.dumps(sidecar_data, indent=2))
    print(f"✓ Wrote sidecar {out_path}")

if __name__ == "__main__":
    main()

