#!/usr/bin/env python3
"""Modern first-person camera feel for Xziel Android.

Presentation only. Collision, hit detection, player origin, server movement,
weapon timing and bullet trajectories remain authoritative and untouched.

Adds:
- smooth visual eye-height transitions for crouch/prone/stand;
- subtle critically-damped landing compression;
- sprint weapon lowering;
- frame-rate-independent smoothing;
- keeps classic Vril behavior when xziel_modern_movement=0.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_camera_feel.py <vril-root>")

root = Path(sys.argv[1])
view = root / "source" / "view.c"
text = view.read_text(encoding="utf-8")


def once(src: str, old: str, new: str, label: str) -> str:
    if new in src:
        return src
    if old not in src:
        raise SystemExit("missing camera-feel anchor: " + label)
    return src.replace(old, new, 1)


state_anchor = """static qboolean viewWasFalling;
vec3_t CWeaponOffset;//blubs declared this
"""
state_repl = """static qboolean viewWasFalling;
#ifdef __ANDROID__
static qboolean xziel_eyeheight_initialized;
static float xziel_eyeheight_visual;
static float xziel_land_camera_pos;
static float xziel_land_camera_vel;
static float xziel_sprint_lower;
#endif
vec3_t CWeaponOffset;//blubs declared this
"""
text = once(text, state_anchor, state_repl, "camera state")


eye_anchor = """// refresh position
\tVectorCopy (ent->origin, r_refdef.vieworg);
\tr_refdef.vieworg[2] += cl.viewheight;//blubs removed "+ bob", it's added again below actually...
"""
eye_repl = """// refresh position
\tVectorCopy (ent->origin, r_refdef.vieworg);
#ifdef __ANDROID__
\tif (Cvar_VariableValue("xziel_modern_movement") >= 0.5f)
\t{
\t\tfloat dt = (float)host_frametime;
\t\tfloat target_height = cl.viewheight;
\t\tfloat blend;
\t\tif (dt < 0.0f) dt = 0.0f;
\t\tif (dt > 0.05f) dt = 0.05f;

\t\tif (!xziel_eyeheight_initialized ||
\t\t\tfabsf(target_height - xziel_eyeheight_visual) > 48.0f)
\t\t{
\t\t\txziel_eyeheight_visual = target_height;
\t\t\txziel_eyeheight_initialized = true;
\t\t}
\t\telse
\t\t{
\t\t\t/* ~18 Hz response: fast enough for combat, no one-frame crouch pop. */
\t\t\tblend = 1.0f - expf(-18.0f * dt);
\t\t\txziel_eyeheight_visual +=
\t\t\t\t(target_height - xziel_eyeheight_visual) * blend;
\t\t}
\t\tr_refdef.vieworg[2] += xziel_eyeheight_visual;
\t}
\telse
\t{
\t\txziel_eyeheight_initialized = false;
\t\txziel_eyeheight_visual = cl.viewheight;
\t\tr_refdef.vieworg[2] += cl.viewheight;
\t}
#else
\tr_refdef.vieworg[2] += cl.viewheight;
#endif
"""
text = once(text, eye_anchor, eye_repl, "visual eye height")


landing_insert_anchor = """\tstairstep = stairsmoothing;
\tstairz = oldz - ent->origin[2];
\tr_refdef.vieworg[2] += stairz;
\tlastorgz = ent->origin[2];

// set up gun position
"""
landing_insert_repl = """\tstairstep = stairsmoothing;
\tstairz = oldz - ent->origin[2];
\tr_refdef.vieworg[2] += stairz;
\tlastorgz = ent->origin[2];

#ifdef __ANDROID__
\tif (Cvar_VariableValue("xziel_modern_movement") >= 0.5f)
\t{
\t\tfloat dt = (float)host_frametime;
\t\tconst float frequency = 17.0f;
\t\tfloat acceleration;
\t\tif (dt < 0.0f) dt = 0.0f;
\t\tif (dt > 0.05f) dt = 0.05f;

\t\t/* Reuse Vril's proven landing detection. Convert impact velocity into a
\t\t   restrained camera impulse instead of a hard positional snap. */
\t\tif (!stairstep && cl.onground && viewWasFalling &&
\t\t\tlastUpVelocity < cl.velocity[2] - 5.0f)
\t\t{
\t\t\tfloat impact = -lastUpVelocity;
\t\t\tif (impact < 0.0f) impact = 0.0f;
\t\t\tif (impact > 700.0f) impact = 700.0f;
\t\t\txziel_land_camera_vel -= impact * 0.030f;
\t\t}

\t\tacceleration =
\t\t\t(-frequency * frequency * xziel_land_camera_pos) -
\t\t\t(2.0f * frequency * xziel_land_camera_vel);
\t\txziel_land_camera_vel += acceleration * dt;
\t\txziel_land_camera_pos += xziel_land_camera_vel * dt;

\t\tif (xziel_land_camera_pos < -1.8f) xziel_land_camera_pos = -1.8f;
\t\tif (xziel_land_camera_pos > 0.35f) xziel_land_camera_pos = 0.35f;
\t\tif (fabsf(xziel_land_camera_pos) < 0.001f &&
\t\t\tfabsf(xziel_land_camera_vel) < 0.001f)
\t\t{
\t\t\txziel_land_camera_pos = 0.0f;
\t\t\txziel_land_camera_vel = 0.0f;
\t\t}

\t\tr_refdef.vieworg[2] += xziel_land_camera_pos;
\t}
\telse
\t{
\t\txziel_land_camera_pos = 0.0f;
\t\txziel_land_camera_vel = 0.0f;
\t}
#endif

// set up gun position
"""
text = once(text, landing_insert_anchor, landing_insert_repl, "landing camera spring")


old_landing = """\t//============================================================ Fall Landing Buffering ============================================================
\tif(!stairstep && cl.onground && viewWasFalling
\t&& lastUpVelocity < cl.velocity[2] - 5)//We've actually landed
\t{
\t\tVerticalOffset = (lastUpVelocity - cl.velocity[2])/25;
\t\tif(VerticalOffset < -15)
\t\t{
\t\t\tVerticalOffset = -15;
\t\t}
\t}

\tif (stairstep)
\t\tVerticalOffset = cVerticalOffset = 0;
\telse
\t\tcVerticalOffset += (VerticalOffset - cVerticalOffset) * 0.3f;

\ttemp_up[0] *= cVerticalOffset;
\ttemp_up[1] *= cVerticalOffset;
\ttemp_up[2] *= cVerticalOffset;

\tview->origin[0] +=(temp_up[0]);
\tview->origin[1] +=(temp_up[1]);
\tview->origin[2] +=(temp_up[2]);

\tif(cVerticalOffset > VerticalOffset - 2 && cVerticalOffset < VerticalOffset + 2)//Close enough to goal
\t{
\t\tVerticalOffset = 0;
\t}
"""
new_landing = """\t//============================================================ Fall Landing Buffering ============================================================
#ifdef __ANDROID__
\tif (Cvar_VariableValue("xziel_modern_movement") >= 0.5f)
\t{
\t\t/* Modern mode applies the compact camera spring above. Suppress the
\t\t   legacy large weapon-only dip so the two effects do not stack. */
\t\tVerticalOffset = 0.0f;
\t\tcVerticalOffset = 0.0f;
\t}
\telse
#endif
\t{
\t\tif(!stairstep && cl.onground && viewWasFalling
\t\t&& lastUpVelocity < cl.velocity[2] - 5)//We've actually landed
\t\t{
\t\t\tVerticalOffset = (lastUpVelocity - cl.velocity[2])/25;
\t\t\tif(VerticalOffset < -15)
\t\t\t{
\t\t\t\tVerticalOffset = -15;
\t\t\t}
\t\t}

\t\tif (stairstep)
\t\t\tVerticalOffset = cVerticalOffset = 0;
\t\telse
\t\t\tcVerticalOffset += (VerticalOffset - cVerticalOffset) * 0.3f;

\t\ttemp_up[0] *= cVerticalOffset;
\t\ttemp_up[1] *= cVerticalOffset;
\t\ttemp_up[2] *= cVerticalOffset;

\t\tview->origin[0] +=(temp_up[0]);
\t\tview->origin[1] +=(temp_up[1]);
\t\tview->origin[2] +=(temp_up[2]);

\t\tif(cVerticalOffset > VerticalOffset - 2 && cVerticalOffset < VerticalOffset + 2)
\t\t{
\t\t\tVerticalOffset = 0;
\t\t}
\t}
"""
text = once(text, old_landing, new_landing, "legacy landing isolation")


sprint_anchor = """\tview->origin[0] +=(temp_forward[0] + temp_right[0] + temp_up[0]);
\tview->origin[1] +=(temp_forward[1] + temp_right[1] + temp_up[1]);
\tview->origin[2] +=(temp_forward[2] + temp_right[2] + temp_up[2]);

\tfloat speed ="""
sprint_repl = """\tview->origin[0] +=(temp_forward[0] + temp_right[0] + temp_up[0]);
\tview->origin[1] +=(temp_forward[1] + temp_right[1] + temp_up[1]);
\tview->origin[2] +=(temp_forward[2] + temp_right[2] + temp_up[2]);

#ifdef __ANDROID__
\tif (Cvar_VariableValue("xziel_modern_movement") >= 0.5f)
\t{
\t\tfloat dt = (float)host_frametime;
\t\tfloat target = cl.stats[STAT_ZOOM] == 3 ? 1.0f : 0.0f;
\t\tfloat blend;
\t\tif (dt < 0.0f) dt = 0.0f;
\t\tif (dt > 0.05f) dt = 0.05f;
\t\tblend = 1.0f - expf(-12.0f * dt);
\t\txziel_sprint_lower += (target - xziel_sprint_lower) * blend;

\t\t/* Weapon presentation only. A lowered/forward weapon makes sprint state
\t\t   readable without touching camera aim or authoritative movement. */
\t\tAngleVectors(r_refdef.viewangles, temp_forward, temp_right, temp_up);
\t\tview->origin[0] += temp_up[0] * (-2.4f * xziel_sprint_lower)
\t\t\t+ temp_forward[0] * (1.1f * xziel_sprint_lower);
\t\tview->origin[1] += temp_up[1] * (-2.4f * xziel_sprint_lower)
\t\t\t+ temp_forward[1] * (1.1f * xziel_sprint_lower);
\t\tview->origin[2] += temp_up[2] * (-2.4f * xziel_sprint_lower)
\t\t\t+ temp_forward[2] * (1.1f * xziel_sprint_lower);
\t}
\telse
\t\txziel_sprint_lower = 0.0f;
#endif

\tfloat speed ="""
text = once(text, sprint_anchor, sprint_repl, "sprint weapon posture")

view.write_text(text, encoding="utf-8")
print("Applied Xziel modern camera/stance/landing/sprint feel.")
