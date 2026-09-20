#!/usr/bin/env python3
"""Xziel v0.24: allow normal weapon fire during the mobile slide.

The v0.21 slide correctly exits sprint and enters crouch, but the sprint-stop
viewmodel transition can still leave the weapon animation locked for a short
moment. Clear only that sprint-stop animation lock. Reload/swap/grenade timing
is intentionally left untouched, so slide cannot be used to cancel gameplay
cooldowns.

Applied after patch_quakec_mobile_v022.py.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_mobile_v024.py <quakec-root>")

root = Path(sys.argv[1])
weapon = root / "source" / "server" / "weapons" / "weapon_core.qc"
text = weapon.read_text(encoding="utf-8")

start = text.find("void() Xziel_MobileCrouchSlide =")
if start < 0:
    raise SystemExit("Could not find Xziel_MobileCrouchSlide")
end = text.find("\n};", start)
if end < 0:
    raise SystemExit("Could not find Xziel_MobileCrouchSlide end")
end += 3
chunk = text[start:end]

old = '''\tW_AimOut();
\tif (self.sprinting)
\t\tW_SprintStop();
\tself.sprintflag = false;
'''
new = '''\tW_AimOut();
\tif (self.sprinting)
\t\tW_SprintStop();

\t// Sprint-stop is only a presentation transition. The slide has its own
\t// first-person pose in Vril, so do not let that old transition block the
\t// first shot. Reload/swap/grenade delay fields are deliberately untouched.
\tself.new_anim_stop = false;
\tself.new_anim2_stop = false;
\tself.fire_delay = 0;
\tself.fire_delay2 = 0;

\tself.sprintflag = false;
'''
if "do not let that old transition block" not in chunk:
    if old not in chunk:
        raise SystemExit("Could not find slide sprint-stop block")
    chunk = chunk.replace(old, new, 1)
    text = text[:start] + chunk + text[end:]

weapon.write_text(text, encoding="utf-8")
print("Applied Xziel v0.24 fire-during-slide behavior.")
