#!/usr/bin/env python3
"""Add a presentation-only 2026 weapon recoil layer to Vril.

This deliberately does NOT alter authoritative aim, bullet spread, weapon fire
cadence, QuakeC recoil values, damage, movement, or ADS timing. It uses the
existing per-weapon recoil event only to animate the first-person weapon model.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_animation_feel.py <vril-root>")

root = Path(sys.argv[1])
source = root / "source"

view = source / "view.c"
text = view.read_text(encoding="utf-8")

anchor = "vec3_t CWeaponRot;\n"
block = r'''
/* Xziel mobile presentation-only weapon kick.
   The server/QC recoil remains authoritative; this layer only moves the
   first-person model a few render units so pistols/revolvers/shotguns/heavy
   rifles visibly kick without changing where bullets go. */
static float xziel_vm_recoil_back;
static float xziel_vm_recoil_up;
static float xziel_vm_recoil_roll;

void Xziel_AddVisualWeaponRecoil(const vec3_t kick)
{
	float mag = sqrtf(kick[0]*kick[0] + kick[1]*kick[1] + kick[2]*kick[2]);
	float back = mag * 0.45f;
	float up = mag * 0.16f;
	float roll = kick[1] * 0.08f;

	if (back > 1.75f) back = 1.75f;
	if (up > 0.70f) up = 0.70f;
	if (roll > 1.35f) roll = 1.35f;
	if (roll < -1.35f) roll = -1.35f;

	xziel_vm_recoil_back += back;
	xziel_vm_recoil_up += up;
	xziel_vm_recoil_roll += roll;

	if (xziel_vm_recoil_back > 2.20f) xziel_vm_recoil_back = 2.20f;
	if (xziel_vm_recoil_up > 0.95f) xziel_vm_recoil_up = 0.95f;
	if (xziel_vm_recoil_roll > 2.0f) xziel_vm_recoil_roll = 2.0f;
	if (xziel_vm_recoil_roll < -2.0f) xziel_vm_recoil_roll = -2.0f;
}

static void Xziel_UpdateVisualWeaponRecoil(void)
{
	float dt = (float)host_frametime;
	float decay;
	if (dt < 0) dt = 0;
	if (dt > 0.05f) dt = 0.05f;

	/* Critically quick visual return: enough to read as mechanical kick,
	   short enough not to make touch aiming feel floaty. */
	decay = expf(-18.0f * dt);
	xziel_vm_recoil_back *= decay;
	xziel_vm_recoil_up *= decay;
	xziel_vm_recoil_roll *= decay;

	if (fabsf(xziel_vm_recoil_back) < 0.001f) xziel_vm_recoil_back = 0;
	if (fabsf(xziel_vm_recoil_up) < 0.001f) xziel_vm_recoil_up = 0;
	if (fabsf(xziel_vm_recoil_roll) < 0.001f) xziel_vm_recoil_roll = 0;
}
'''
if "Xziel_AddVisualWeaponRecoil" not in text:
    if anchor not in text:
        raise SystemExit("Could not find CWeaponRot anchor")
    text = text.replace(anchor, anchor + block, 1)

update_anchor = "\tDropRecoilKick();\n"
if "Xziel_UpdateVisualWeaponRecoil();" not in text:
    if update_anchor not in text:
        raise SystemExit("Could not find recoil update call")
    text = text.replace(
        update_anchor,
        update_anchor + "\tXziel_UpdateVisualWeaponRecoil();\n",
        1,
    )

# Apply recoil after ADS translation, before locomotion bob. This keeps ADS
# alignment intact at rest while the shot itself visibly displaces the model.
origin_anchor = '''\tview->origin[0] +=(temp_forward[0] + temp_right[0] + temp_up[0]);
\tview->origin[1] +=(temp_forward[1] + temp_right[1] + temp_up[1]);
\tview->origin[2] +=(temp_forward[2] + temp_right[2] + temp_up[2]);

\tfloat speed ='''
origin_repl = '''\tview->origin[0] +=(temp_forward[0] + temp_right[0] + temp_up[0]);
\tview->origin[1] +=(temp_forward[1] + temp_right[1] + temp_up[1]);
\tview->origin[2] +=(temp_forward[2] + temp_right[2] + temp_up[2]);

#ifdef __ANDROID__
\t/* Physical-looking viewmodel kick: backwards toward the camera with a
\t   smaller upward component. No camera/aim mutation. */
\tview->origin[0] -= temp_forward[0] * xziel_vm_recoil_back;
\tview->origin[1] -= temp_forward[1] * xziel_vm_recoil_back;
\tview->origin[2] -= temp_forward[2] * xziel_vm_recoil_back;
\tview->origin[0] += temp_up[0] * xziel_vm_recoil_up;
\tview->origin[1] += temp_up[1] * xziel_vm_recoil_up;
\tview->origin[2] += temp_up[2] * xziel_vm_recoil_up;
\tview->angles[ROLL] += xziel_vm_recoil_roll;
#endif

\tfloat speed ='''
if "Physical-looking viewmodel kick" not in text:
    if origin_anchor not in text:
        raise SystemExit("Could not find ADS-origin tail")
    text = text.replace(origin_anchor, origin_repl, 1)

view.write_text(text, encoding="utf-8")

clparse = source / "cl_parse.c"
text = clparse.read_text(encoding="utf-8")

extern_anchor = "extern int crosshair_spread;\n"
if "Xziel_AddVisualWeaponRecoil" not in text:
    if extern_anchor not in text:
        raise SystemExit("Could not find cl_parse recoil extern anchor")
    text = text.replace(
        extern_anchor,
        extern_anchor + "extern void Xziel_AddVisualWeaponRecoil(const vec3_t kick);\n",
        1,
    )

kick_anchor = '''\tcl.gun_kick[0] += kick[0];
\tcl.gun_kick[1] += kick[1];
\tcl.gun_kick[2] += kick[2];
'''
kick_repl = '''\tcl.gun_kick[0] += kick[0];
\tcl.gun_kick[1] += kick[1];
\tcl.gun_kick[2] += kick[2];

#ifdef __ANDROID__
\tXziel_AddVisualWeaponRecoil(kick);
#endif
'''
if "Xziel_AddVisualWeaponRecoil(kick);" not in text:
    if kick_anchor not in text:
        raise SystemExit("Could not find parsed gun-kick accumulation")
    text = text.replace(kick_anchor, kick_repl, 1)

clparse.write_text(text, encoding="utf-8")
print("Applied Xziel presentation-only weapon recoil polish.")
