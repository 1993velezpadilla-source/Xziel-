#!/usr/bin/env python3
"""Fetch and rasterize the CC0 HUD icon set used by Xziel mobile.

Upstream: Nieobie/Game-Icon-Pack
License: CC0 1.0 Universal
Pinned revision: b1a5fec8b68c99e7b46484db707610ab2414ad4c
"""
from pathlib import Path
from urllib.request import Request, urlopen
import io
import re
import sys
import zipfile
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
    "slide": "8-ui/arrow-down-02.svg",
    "pistol": "3-gear/pistol.svg",
    "weapon": "3-gear/bullet.svg",
    "weapon_wonder": "4-nature/lightning.svg",
    "weapon_launcher": "3-gear/missile.svg",
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
    # Weapon cards use actual CC0 gun artwork rather than a hand-drawn glyph.
    # Kay Lousberg's pack is CC0, transparent PNG, and explicitly includes
    # pistol/revolver/shotgun/sniper/SMG/assault-rifle artwork.
    # OpenGameArt canonical page:
    # https://opengameart.org/content/2d-guns
    try:
        weapon_zip = fetch("https://opengameart.org/sites/default/files/guns_gameassets.zip")
        with zipfile.ZipFile(io.BytesIO(weapon_zip)) as archive:
            names = [
                n for n in archive.namelist()
                if n.lower().endswith(".png")
                and "__macosx" not in n.lower()
                and "spritesheet" not in n.lower()
            ]

            def pick(keyword: str) -> str | None:
                choices = []
                for name in names:
                    base = Path(name).stem.lower()
                    if keyword not in base:
                        continue
                    if any(bad in base for bad in ("magazine", "bullet", "ammo", "box")):
                        continue
                    score = 0
                    if "@2x" in base or "2x" in base:
                        score += 5
                    if "separate" in name.lower() or "individual" in name.lower():
                        score += 3
                    if "alternate" not in name.lower() and "alt" not in base:
                        score += 1
                    choices.append((score, len(name), name))
                if not choices:
                    return None
                choices.sort(key=lambda x: (-x[0], x[1], x[2]))
                return choices[0][2]

            categories = {
                "weapon_pistol.png": "pistol",
                "weapon_revolver.png": "revolver",
                "weapon_shotgun.png": "shotgun",
                "weapon_sniper.png": "sniper",
                "weapon_smg.png": "smg",
                "weapon_assault.png": "assault",
            }
            picked = {}
            for filename, keyword in categories.items():
                selected = pick(keyword)
                if selected:
                    payload = archive.read(selected)
                    (out / filename).write_bytes(payload)
                    picked[keyword] = filename

            # Preserve legacy names used by older checkpoints.
            if "pistol" in picked:
                (out / "pistol.png").write_bytes((out / picked["pistol"]).read_bytes())
            if "assault" in picked:
                (out / "weapon.png").write_bytes((out / picked["assault"]).read_bytes())
    except Exception as exc:
        # The Nieobie CC0 pistol/bullet icons remain a deterministic fallback
        # if OpenGameArt is temporarily unavailable during CI.
        print(f"warning: Kay Lousberg weapon art unavailable: {exc}", file=sys.stderr)

    # CI must always produce every HUD path even when OpenGameArt is down or
    # the upstream archive changes a filename. The fallback images are also
    # CC0 from the already-pinned Nieobie pack.
    fallback_map = {
        "weapon_pistol.png": "pistol.png",
        "weapon_revolver.png": "pistol.png",
        "weapon_shotgun.png": "weapon.png",
        "weapon_sniper.png": "weapon.png",
        "weapon_smg.png": "weapon.png",
        "weapon_assault.png": "weapon.png",
    }
    for dst, src in fallback_map.items():
        target = out / dst
        if not target.exists():
            target.write_bytes((out / src).read_bytes())

    (out / "LICENSE-CC0.txt").write_text(
        "Xziel mobile HUD assets are CC0/public-domain.\n"
        "Touch/action icons: Nieobie/Game-Icon-Pack, CC0 1.0 Universal.\n"
        f"Source revision: {REV}\nhttps://github.com/Nieobie/Game-Icon-Pack\n"
        "Weapon card art: Kay Lousberg, 2D Guns, CC0.\n"
        "https://opengameart.org/content/2d-guns\n",
        encoding="utf-8",
    )

if __name__ == "__main__":
    main()
