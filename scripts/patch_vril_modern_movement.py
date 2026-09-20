#!/usr/bin/env python3
"""Modern grounded FPS movement for Xziel Android on top of Vril.

The collision/step solver remains Vril's proven Quake brush movement so maps,
triggers and zombie interactions stay compatible. This replaces only the
player velocity response: ground acceleration/friction, air steering and
player-only gravity.

Goals:
- crisp modern FPS start/stop response
- preserve external momentum/knockback
- no classic Quake bunny-hop speed farming
- snappier jump arc without changing useful jump height much
- player-only gravity so grenades/projectiles keep original trajectories
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_modern_movement.py <vril-root>")

root = Path(sys.argv[1])
source = root / "source"

def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise SystemExit(f"missing anchor: {label}")
    return text.replace(old, new, 1)

# ---------------------------------------------------------------------------
# Server movement response
# ---------------------------------------------------------------------------
p = source / "sv_user.c"
text = p.read_text(encoding="utf-8")

cvar_anchor = 'cvar_t\tsv_idealpitchscale = {"sv_idealpitchscale","0.8"};\n'
cvars = r'''
#ifdef __ANDROID__
/* Xziel grounded-modern movement profile.
   These are intentionally independent from Quake's sv_* defaults so
   legacy/non-Android movement remains untouched. */
cvar_t xziel_modern_movement = {"xziel_modern_movement", "1", true};
cvar_t xziel_ground_accel = {"xziel_ground_accel", "14.0", true};
cvar_t xziel_ground_friction = {"xziel_ground_friction", "7.5", true};
cvar_t xziel_ground_stopspeed = {"xziel_ground_stopspeed", "105.0", true};
cvar_t xziel_air_accel = {"xziel_air_accel", "4.0", true};
cvar_t xziel_air_wishcap = {"xziel_air_wishcap", "55.0", true};
cvar_t xziel_player_gravity = {"xziel_player_gravity", "1.30", true};
#endif
'''
if "xziel_modern_movement" not in text:
    text = replace_once(text, cvar_anchor, cvar_anchor + cvars, "sv_user movement cvars")

old_friction = r'''void SV_UserFriction (void)
{
	float	*vel;
	float	speed, newspeed, control;
	vec3_t	start, stop;
	float	friction;
	trace_t	trace;

	vel = velocity;

	speed = sqrtf(vel[0]*vel[0] +vel[1]*vel[1]);
	if (!speed)
		return;

// if the leading edge is over a dropoff, increase friction
	start[0] = stop[0] = origin[0] + vel[0]/speed*16;
	start[1] = stop[1] = origin[1] + vel[1]/speed*16;
	start[2] = origin[2] + sv_player->v.mins[2];
	stop[2] = start[2] - 34;

	trace = SV_Move (start, vec3_origin, vec3_origin, stop, true, sv_player);

	if (trace.fraction == 1.0f)
		friction = sv_friction.value*sv_edgefriction.value;
	else
		friction = sv_friction.value;

// apply friction
	control = speed < sv_stopspeed.value ? sv_stopspeed.value : speed;
	newspeed = speed - (float)host_frametime*control*friction;

	if (newspeed < 0)
		newspeed = 0;
	newspeed /= speed;

	vel[0] = vel[0] * newspeed;
	vel[1] = vel[1] * newspeed;
	vel[2] = vel[2] * newspeed;
}'''

new_friction = r'''void SV_UserFriction (void)
{
	float	*vel;
	float	speed, newspeed, control;
	vec3_t	start, stop;
	float	friction;
	trace_t	trace;

	vel = velocity;

	speed = sqrtf(vel[0]*vel[0] +vel[1]*vel[1]);
	if (!speed)
		return;

#ifdef __ANDROID__
	if (xziel_modern_movement.value >= 0.5f)
	{
		/* Modern grounded response: deterministic horizontal braking with no
		   Quake edge-friction spike. Vertical velocity is not damped here. */
		friction = xziel_ground_friction.value;
		if (friction < 0.0f) friction = 0.0f;
		control = speed < xziel_ground_stopspeed.value ?
			xziel_ground_stopspeed.value : speed;
		newspeed = speed - (float)host_frametime * control * friction;
		if (newspeed < 0.0f)
			newspeed = 0.0f;
		newspeed /= speed;
		vel[0] *= newspeed;
		vel[1] *= newspeed;
		return;
	}
#endif

// if the leading edge is over a dropoff, increase friction
	start[0] = stop[0] = origin[0] + vel[0]/speed*16;
	start[1] = stop[1] = origin[1] + vel[1]/speed*16;
	start[2] = origin[2] + sv_player->v.mins[2];
	stop[2] = start[2] - 34;

	trace = SV_Move (start, vec3_origin, vec3_origin, stop, true, sv_player);

	if (trace.fraction == 1.0f)
		friction = sv_friction.value*sv_edgefriction.value;
	else
		friction = sv_friction.value;

// apply friction
	control = speed < sv_stopspeed.value ? sv_stopspeed.value : speed;
	newspeed = speed - (float)host_frametime*control*friction;

	if (newspeed < 0)
		newspeed = 0;
	newspeed /= speed;

	vel[0] = vel[0] * newspeed;
	vel[1] = vel[1] * newspeed;
	vel[2] = vel[2] * newspeed;
}'''
if "Modern grounded response" not in text:
    text = replace_once(text, old_friction, new_friction, "SV_UserFriction")

old_accel = r'''void SV_Accelerate (void)
{
	int			i;
	float		addspeed, accelspeed, currentspeed;

	currentspeed = DotProduct (velocity, wishdir);
	addspeed = wishspeed - currentspeed;
	if (addspeed <= 0)
		return;
	accelspeed = sv_accelerate.value*(float)host_frametime*wishspeed;
	if (accelspeed > addspeed)
		accelspeed = addspeed;

	for (i=0 ; i<3 ; i++)
		velocity[i] += accelspeed*wishdir[i];
}'''

new_accel = r'''void SV_Accelerate (void)
{
	int			i;
	float		addspeed, accelspeed, currentspeed;
	float		accel = sv_accelerate.value;

#ifdef __ANDROID__
	if (xziel_modern_movement.value >= 0.5f)
		accel = xziel_ground_accel.value;
#endif

	currentspeed = DotProduct (velocity, wishdir);
	addspeed = wishspeed - currentspeed;
	if (addspeed <= 0)
		return;
	accelspeed = accel*(float)host_frametime*wishspeed;
	if (accelspeed > addspeed)
		accelspeed = addspeed;

	for (i=0 ; i<3 ; i++)
		velocity[i] += accelspeed*wishdir[i];
}'''
if "float\t\taccel = sv_accelerate.value;" not in text:
    text = replace_once(text, old_accel, new_accel, "SV_Accelerate")

old_air = r'''void SV_AirAccelerate (vec3_t wishveloc)
{
	int			i;
	float		addspeed, wishspd, accelspeed, currentspeed;

	wishspd = VectorNormalize (wishveloc);
	if (wishspd > 30)
		wishspd = 30;
	currentspeed = DotProduct (velocity, wishveloc);
	addspeed = wishspd - currentspeed;
	if (addspeed <= 0)
		return;
//	accelspeed = sv_accelerate.value * host_frametime;
	accelspeed = sv_accelerate.value*wishspeed * (float)host_frametime;
	if (accelspeed > addspeed)
		accelspeed = addspeed;

	for (i=0 ; i<3 ; i++)
		velocity[i] += accelspeed*wishveloc[i];
}'''

new_air = r'''void SV_AirAccelerate (vec3_t wishveloc)
{
	int			i;
	float		addspeed, wishspd, accelspeed, currentspeed;

	wishspd = VectorNormalize (wishveloc);

#ifdef __ANDROID__
	if (xziel_modern_movement.value >= 0.5f)
	{
		float before_speed, after_speed, speed_cap;
		float target = wishspd;

		/* Modern shooters allow steering in the air but do not turn a jump
		   into a Quake speed-building mechanic. */
		if (target > xziel_air_wishcap.value)
			target = xziel_air_wishcap.value;

		before_speed = sqrtf(velocity[0]*velocity[0] + velocity[1]*velocity[1]);
		currentspeed = DotProduct (velocity, wishveloc);
		addspeed = target - currentspeed;
		if (addspeed <= 0)
			return;

		accelspeed = xziel_air_accel.value * target * (float)host_frametime;
		if (accelspeed > addspeed)
			accelspeed = addspeed;

		velocity[0] += accelspeed * wishveloc[0];
		velocity[1] += accelspeed * wishveloc[1];

		/* Input may steer existing momentum but cannot farm ever-higher
		   horizontal speed. Preserve knockback/launch speed if already above
		   the normal movement cap. */
		after_speed = sqrtf(velocity[0]*velocity[0] + velocity[1]*velocity[1]);
		speed_cap = sv_player->v.maxspeed * 1.03f;
		if (before_speed > speed_cap)
			speed_cap = before_speed;
		if (after_speed > speed_cap && after_speed > 0.0f)
		{
			float ratio = speed_cap / after_speed;
			velocity[0] *= ratio;
			velocity[1] *= ratio;
		}
		return;
	}
#endif

	if (wishspd > 30)
		wishspd = 30;
	currentspeed = DotProduct (velocity, wishveloc);
	addspeed = wishspd - currentspeed;
	if (addspeed <= 0)
		return;
//	accelspeed = sv_accelerate.value * host_frametime;
	accelspeed = sv_accelerate.value*wishspeed * (float)host_frametime;
	if (accelspeed > addspeed)
		accelspeed = addspeed;

	for (i=0 ; i<3 ; i++)
		velocity[i] += accelspeed*wishveloc[i];
}'''
if "cannot farm ever-higher" not in text:
    text = replace_once(text, old_air, new_air, "SV_AirAccelerate")

p.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Player-only gravity. Do not touch grenades, projectiles, zombies, props.
# ---------------------------------------------------------------------------
p = source / "sv_phys.c"
text = p.read_text(encoding="utf-8")

gravity_anchor = '''\tif (val && val->_float)
\t\tent_gravity = val->_float;
\telse
\t\tent_gravity = 1.0f;
\tent->v.velocity[2] -= ent_gravity * sv_gravity.value * (float)host_frametime;
'''
gravity_repl = '''\tif (val && val->_float)
\t\tent_gravity = val->_float;
\telse
\t\tent_gravity = 1.0f;

#ifdef __ANDROID__
\t/* Increase gravity only for actual players. Projectile/throwable arcs and
	   non-player physics retain the original map/game behavior. */
\tif (((int)ent->v.flags & FL_CLIENT) && xziel_modern_movement.value >= 0.5f)
\t\tent_gravity *= xziel_player_gravity.value;
#endif

\tent->v.velocity[2] -= ent_gravity * sv_gravity.value * (float)host_frametime;
'''
if "Increase gravity only for actual players" not in text:
    if "extern cvar_t xziel_modern_movement;" not in text:
        include_anchor = 'cvar_t\tsv_maxvelocity = {"sv_maxvelocity","100000"};\n'
        externs = '''#ifdef __ANDROID__
extern cvar_t xziel_modern_movement;
extern cvar_t xziel_player_gravity;
#endif
'''
        text = replace_once(text, include_anchor, include_anchor + externs, "sv_phys movement externs")
    text = replace_once(text, gravity_anchor, gravity_repl, "SV_AddGravity player multiplier")
p.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Register movement controls.
# ---------------------------------------------------------------------------
p = source / "sv_main.c"
text = p.read_text(encoding="utf-8")

extern_anchor = '\textern\tcvar_t\tsv_aim;\n'
externs = r'''#ifdef __ANDROID__
	extern cvar_t xziel_modern_movement;
	extern cvar_t xziel_ground_accel;
	extern cvar_t xziel_ground_friction;
	extern cvar_t xziel_ground_stopspeed;
	extern cvar_t xziel_air_accel;
	extern cvar_t xziel_air_wishcap;
	extern cvar_t xziel_player_gravity;
#endif
'''
if "extern cvar_t xziel_modern_movement;" not in text:
    text = replace_once(text, extern_anchor, extern_anchor + externs, "SV_Init movement externs")

register_anchor = '\tCvar_RegisterVariable (&sv_aim);\n'
registers = r'''#ifdef __ANDROID__
	Cvar_RegisterVariable (&xziel_modern_movement);
	Cvar_RegisterVariable (&xziel_ground_accel);
	Cvar_RegisterVariable (&xziel_ground_friction);
	Cvar_RegisterVariable (&xziel_ground_stopspeed);
	Cvar_RegisterVariable (&xziel_air_accel);
	Cvar_RegisterVariable (&xziel_air_wishcap);
	Cvar_RegisterVariable (&xziel_player_gravity);
#endif
'''
if "Cvar_RegisterVariable (&xziel_modern_movement);" not in text:
    text = replace_once(text, register_anchor, register_anchor + registers, "SV_Init movement registration")

p.write_text(text, encoding="utf-8")
print("Applied Xziel modern grounded FPS movement.")
