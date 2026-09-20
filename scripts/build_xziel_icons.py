#!/usr/bin/env python3
"""Fetch and rasterize the CC0 HUD icon set used by Xziel mobile.

Upstream: Nieobie/Game-Icon-Pack
License: CC0 1.0 Universal
Pinned revision: b1a5fec8b68c99e7b46484db707610ab2414ad4c
"""
from pathlib import Path
from urllib.request import Request, urlopen
import sys
import cairosvg

REV = "b1a5fec8b68c99e7b46484db707610ab2414ad4c"
BASE = f"https://raw.githubusercontent.com/Nieobie/Game-Icon-Pack/{REV}/svg/no-padding"
ICONS = {
    "fire": "6-buildings/target.svg",
    "ads": "6-buildings/target-02.svg",
    "reload": "8-ui/refresh.svg",
    "use": "6-buildings/open-the-door.svg",
    "jump": "8-ui/arrow-up.svg",
    "knife": "5-food/knife.svg",
    "grenade": "3-gear/bomb.svg",
    "pause": "9-media/pause.svg",
    "sprint": "3-gear/shoe.svg",
    "pistol": "3-gear/pistol.svg",
    "weapon": "3-gear/bullet.svg",
    "threat": "1-game/skull.svg",
}

def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Xziel-build/0.18"})
    with urlopen(req, timeout=30) as response:
        return response.read()

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: build_xziel_icons.py <output-dir>")
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    for name, rel in ICONS.items():
        svg = fetch(f"{BASE}/{rel}").replace(b"currentColor", b"#FFFFFF")
        cairosvg.svg2png(
            bytestring=svg,
            write_to=str(out / f"{name}.png"),
            output_width=256,
            output_height=256,
        )
    (out / "LICENSE-CC0.txt").write_text(
        "Derived from Nieobie/Game-Icon-Pack under CC0 1.0 Universal.\n"
        f"Source revision: {REV}\nhttps://github.com/Nieobie/Game-Icon-Pack\n",
        encoding="utf-8",
    )

if __name__ == "__main__":
    main()
