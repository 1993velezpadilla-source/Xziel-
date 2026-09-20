#!/usr/bin/env python3
"""Xziel v0.24: readable modern first-person slide presentation.

This pass does not alter hit direction or authoritative world collision.
It makes the existing server-authoritative crouch/slide visually read like a
modern FPS slide:
- a fast camera compression into the skid;
- a strong first-person weapon cant/translation;
- a smooth recovery instead of a one-frame crouch-looking dip;
- the pose remains additive with normal fire/recoil animations.

Applied after patch_vril_mobile_v022.py.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_mobile_v024.py <vril-root>")

root = Path(sys.argv[1])
source = root / "source"

def add_after(src: str, anchor: str, payload: str, label: str) -> str:
    if payload.strip() in src:
        return src
    if anchor not in src:
        raise SystemExit("Missing anchor: " + label)
    return src.replace(anchor, anchor + payload, 1)

# ---------------------------------------------------------------------------
# SDL touch runtime: start a presentation timer only for an actual sprint slide.
# ---------------------------------------------------------------------------
sdl = source / "platform" / "sdl" / "sys_sdl.c"
text = sdl.read_text(encoding="utf-8")

state_anchor = "static qboolean xziel_mobile_slide_pressed = false;\n"
slide_state = r'''static Uint32 xziel_mobile_slide_visual_start_ms;
static Uint32 xziel_mobile_slide_visual_end_ms;

/* -1 means inactive. 0..1 is normalized slide progress.
   Kept client-side because this is presentation only; movement remains QC. */
float Xziel_MobileSlideVisualPhase(void)
{
    Uint32 now;
    Uint32 span;
    float phase;

    if (!xziel_mobile_slide_visual_start_ms ||
        !xziel_mobile_slide_visual_end_ms)
        return -1.0f;

    now = SDL_GetTicks();
    if (now >= xziel_mobile_slide_visual_end_ms) {
        xziel_mobile_slide_visual_start_ms = 0;
        xziel_mobile_slide_visual_end_ms = 0;
        return -1.0f;
    }

    span = xziel_mobile_slide_visual_end_ms -
        xziel_mobile_slide_visual_start_ms;
    if (!span)
        return -1.0f;

    phase = (float)(now - xziel_mobile_slide_visual_start_ms) /
        (float)span;
    if (phase < 0.0f) phase = 0.0f;
    if (phase > 1.0f) phase = 1.0f;
    return phase;
}
'''
if "Xziel_MobileSlideVisualPhase" not in text:
    text = add_after(text, state_anchor, slide_state, "slide visual state")

down_start = text.find("static void Xziel_ActionDown(xziel_touch_role_t role)")
down_end = text.find("static void Xziel_ActionUp(xziel_touch_role_t role)", down_start)
if down_start < 0 or down_end < 0:
    raise SystemExit("Could not find final ActionDown/ActionUp")
chunk = text[down_start:down_end]

old_case = r'''	case XZ_TOUCH_SLIDE:
		xziel_mobile_slide_pressed = true;
		xziel_mobile_sprint_suppressed = true;
		xziel_mobile_sprint_active = false;
		xziel_mobile_sprint_retry_ms = SDL_GetTicks() + 650;
		Cbuf_AddText("impulse 34\n");
		Cbuf_Execute();
		break;
'''
new_case = r'''	case XZ_TOUCH_SLIDE:
	{
		Uint32 slide_now = SDL_GetTicks();
		qboolean confirmed_sprint =
			xziel_mobile_sprint_active || cl.stats[STAT_ZOOM] == 3;

		xziel_mobile_slide_pressed = true;

		/* Only play the dramatic skid pose for sprint -> crouch. A normal
		   standing crouch remains a normal crouch. */
		if (confirmed_sprint) {
			xziel_mobile_slide_visual_start_ms = slide_now;
			xziel_mobile_slide_visual_end_ms = slide_now + 560;
		}

		xziel_mobile_sprint_suppressed = true;
		xziel_mobile_sprint_active = false;
		xziel_mobile_sprint_retry_ms = slide_now + 650;
		Cbuf_AddText("impulse 34\n");
		Cbuf_Execute();
		break;
	}
'''
if "confirmed_sprint" not in chunk:
    if old_case not in chunk:
        raise SystemExit("Could not find final XZ_TOUCH_SLIDE ActionDown case")
    chunk = chunk.replace(old_case, new_case, 1)
    text = text[:down_start] + chunk + text[down_end:]

sdl.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# First-person presentation. Keep this in view.c so every weapon automatically
# inherits it without requiring a bespoke slide clip in every viewmodel.
# ---------------------------------------------------------------------------
view = source / "view.c"
text = view.read_text(encoding="utf-8")

extern_anchor = "vec3_t CWeaponRot;\n"
extern_block = r'''#ifdef __ANDROID__
extern float Xziel_MobileSlideVisualPhase(void);
#endif
'''
if "extern float Xziel_MobileSlideVisualPhase" not in text:
    text = add_after(text, extern_anchor, extern_block, "slide phase extern")

speed_anchor = "\tfloat speed = (0.2f + sqrtf"
slide_pose = r'''#ifdef __ANDROID__
	if (Cvar_VariableValue("xziel_modern_movement") >= 0.5f)
	{
		float slide_t = Xziel_MobileSlideVisualPhase();
		if (slide_t >= 0.0f)
		{
			float pose;
			float u;
			float skid;
			float camera_pose;

			/* Fast entry, readable hold, soft recovery. This is deliberately
			   much stronger than the normal crouch eye-height interpolation. */
			if (slide_t < 0.14f) {
				u = slide_t / 0.14f;
				pose = u*u*(3.0f - 2.0f*u);
			} else if (slide_t < 0.72f) {
				pose = 1.0f;
			} else {
				u = (slide_t - 0.72f) / 0.28f;
				if (u < 0.0f) u = 0.0f;
				if (u > 1.0f) u = 1.0f;
				pose = 1.0f - u*u*(3.0f - 2.0f*u);
			}
			skid = sinf(slide_t * 3.1415926535f);
			camera_pose = pose * (0.82f + 0.18f*skid);

			/* Camera motion is render-only: lower the eyes into the skid and
			   add a tiny body roll. cl.viewangles and bullet vectors are not
			   modified. */
			r_refdef.vieworg[2] -= 2.35f * camera_pose;
			r_refdef.viewangles[ROLL] -= 1.15f * skid;

			/* Modern slide posture: weapon/arms visibly cant across the body.
			   Fire animations and Xziel recoil are still evaluated normally,
			   so shots remain fully animated during the slide. */
			AngleVectors(r_refdef.viewangles, temp_forward, temp_right, temp_up);
			view->origin[0] +=
				temp_right[0] * (-3.45f * pose) +
				temp_up[0]    * ( 1.15f * pose) +
				temp_forward[0] * (-0.55f * pose);
			view->origin[1] +=
				temp_right[1] * (-3.45f * pose) +
				temp_up[1]    * ( 1.15f * pose) +
				temp_forward[1] * (-0.55f * pose);
			view->origin[2] +=
				temp_right[2] * (-3.45f * pose) +
				temp_up[2]    * ( 1.15f * pose) +
				temp_forward[2] * (-0.55f * pose);

			view->angles[ROLL] -= (23.0f * pose + 2.5f * skid);
			view->angles[YAW]  -= 8.0f * pose;
			view->angles[PITCH] += 5.0f * pose;
		}
	}
#endif

'''
if "Modern slide posture: weapon/arms visibly cant" not in text:
    if speed_anchor not in text:
        raise SystemExit("Could not find final viewmodel locomotion anchor")
    text = text.replace(speed_anchor, slide_pose + speed_anchor, 1)

view.write_text(text, encoding="utf-8")
print("Applied Xziel v0.24 first-person slide presentation.")
