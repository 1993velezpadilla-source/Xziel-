#!/usr/bin/env python3
"""Xziel v0.21 mobile crouch/slide gameplay patch.

Keeps stock NZ:P stance/dolphin-dive commands intact. Mobile uses impulse 34:
- standing/crouched: toggle stand <-> crouch
- sprinting: short grounded slide, ending crouched
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_mobile_v021.py <quakec-root>")

root = Path(sys.argv[1])
custom = root / "source" / "server" / "defs" / "custom.qc"
weapon = root / "source" / "server" / "weapons" / "weapon_core.qc"

ctext = custom.read_text(encoding="utf-8")
fields = r'''
// Xziel mobile slide state. Server-authoritative so movement/collision remains
// inside NZ:P rather than being faked by the Android client.
.float xziel_slide_end;
.vector xziel_slide_dir;
'''
if ".float xziel_slide_end;" not in ctext:
    ctext += "\n" + fields + "\n"
custom.write_text(ctext, encoding="utf-8")

text = weapon.read_text(encoding="utf-8")

slide_code = r'''
void() Xziel_MobileSlideThink =
{
	if (self.xziel_slide_end <= 0)
		return;

	if (self.xziel_slide_end <= time) {
		self.xziel_slide_end = 0;
		return;
	}

	if (self.downed || self.dive || !(self.flags & FL_ONGROUND)) {
		self.xziel_slide_end = 0;
		return;
	}

	float remaining = (self.xziel_slide_end - time) / 0.55;
	if (remaining < 0) remaining = 0;
	if (remaining > 1) remaining = 1;

	// Front-loaded momentum that decays to crouch-speed territory. Only raise
	// velocity to the slide floor; never erase stronger knockback/explosion
	// momentum that the real game has already applied.
	float target_speed = 92 + (148 * remaining);
	vector horizontal = [self.velocity_x, self.velocity_y, 0];
	float current_speed = vlen(horizontal);

	if (current_speed < target_speed) {
		self.velocity_x = self.xziel_slide_dir_x * target_speed;
		self.velocity_y = self.xziel_slide_dir_y * target_speed;
	}
};

void() Xziel_MobileCrouchSlide =
{
	if (self.downed || !(self.flags & FL_ONGROUND) ||
		self.changestance == true || self.new_ofs_z != self.view_ofs_z)
		return;

	if (!self.sprinting) {
		Change_StanceToggle();
		return;
	}

	vector horizontal = [self.velocity_x, self.velocity_y, 0];
	float speed = vlen(horizontal);

	makevectors(self.v_angle);
	if (speed < 8) {
		self.xziel_slide_dir = v_forward;
		self.xziel_slide_dir_z = 0;
		speed = 0;
	} else {
		self.xziel_slide_dir = horizontal * (1 / speed);
	}

	W_AimOut();
	W_SprintStop();
	Player_SetStance(self, PLAYER_STANCE_CROUCH, false);

	self.xziel_slide_end = time + 0.55;

	if (speed < 240) {
		self.velocity_x = self.xziel_slide_dir_x * 240;
		self.velocity_y = self.xziel_slide_dir_y * 240;
	}
};
'''

anchor = "void () Impulse_Functions ="
if "void() Xziel_MobileCrouchSlide" not in text:
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit("Could not find Impulse_Functions anchor")
    text = text[:idx] + slide_code + "\n" + text[idx:]

impulse_anchor = """\t\tcase 33:
\t\t\tW_PrimeBetty();
\t\t\tbreak;
"""
if "case 34:" not in text:
    if impulse_anchor not in text:
        raise SystemExit("Could not find impulse 33 anchor")
    text = text.replace(
        impulse_anchor,
        impulse_anchor + """\t\tcase 34:
\t\t\tXziel_MobileCrouchSlide();
\t\t\tbreak;
""",
        1,
    )

think_anchor = "\tCheckRevive(self);\n"
if "Xziel_MobileSlideThink();" not in text:
    if think_anchor not in text:
        raise SystemExit("Could not find CheckPlayer update anchor")
    text = text.replace(
        think_anchor,
        think_anchor + "\tXziel_MobileSlideThink();\n",
        1,
    )

weapon.write_text(text, encoding="utf-8")
print("Applied Xziel v0.21 server-authoritative mobile slide.")
