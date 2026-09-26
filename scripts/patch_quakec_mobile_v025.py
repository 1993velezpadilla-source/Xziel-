#!/usr/bin/env python3
"""Xziel v0.25 quick fix: allow sprint movement while weapon reload continues.

Stock NZ:P starts/stops sprint by replacing the current viewmodel animation and
zeroing reload_delay/reload_delay2. That cancels an in-progress reload. On
mobile, sprint is movement intent: if a reload is already active, keep the
reload animation/timers authoritative while still enabling sprint speed/state.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_mobile_v025.py <quakec-root>")

root = Path(sys.argv[1])
weapon = root / "source" / "server" / "weapons" / "weapon_core.qc"
text = weapon.read_text(encoding="utf-8")

def replace_function(src: str, signature: str, replacement: str) -> str:
    start = src.find(signature)
    if start < 0:
        raise SystemExit("Could not find function: " + signature)
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit("Could not find function body: " + signature)
    depth = 0
    end = -1
    for i in range(brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit("Could not find function end: " + signature)
    if end < len(src) and src[end] == ";":
        end += 1
    return src[:start] + replacement + src[end:]

sprint_stop = r'''void() W_SprintStop =
{
    if (self.isBuying || !self.sprinting)
        return;

    float xziel_reloading =
        self.reload_delay > time ||
        self.reload_delay2 > time;

    /* Reload owns the viewmodel until its ammo callback completes. Sprint
       stop may change movement state, but must not overwrite that animation. */
    if (!xziel_reloading) {
        Weapon_PlayViewModelAnimation(ANIM_SPRINT_STOP, ReturnWeaponModel, 0);

        // Run Walk for a few frames to simulate an ease in velocity.
        PAnim_Walk6();
    }

    self.zoom = 0;
    if (!xziel_reloading)
        self.tp_anim_time = 0;
    self.sprinting = 0;
    self.into_sprint = 0;

    /* Sprint transitions may release their own fire lock, but reload timers
       are intentionally preserved. They are the authority for completion. */
    self.fire_delay2 = self.fire_delay = 0;

    self.sprint_stop_time = time;
    self.sprint_duration = self.sprint_timer;
}'''

sprint_start = r'''void W_SprintStart () {
    if (self.speed_penalty_time > time || self.zoom != 0)
        return;

    self.sprint_start_time = time;

    if (self.sprint_rest_time > sprint_max_time)
        self.sprint_duration = 0.0;
    else
        self.sprint_duration -= self.sprint_rest_time;

    if (!self.sprintflag) {
        return;
    }

    float xziel_reloading =
        self.reload_delay > time ||
        self.reload_delay2 > time;

    if (self.fire_delay > time ||
        self.fire_delay2 > time ||
        (!xziel_reloading && self.new_anim_stop) ||
        (!xziel_reloading && self.new_anim2_stop) ||
        self.isBuying ||
        self.downed ||
        !(self.flags & FL_ONGROUND) ||
        self.sprint_delay > time) {
        return;
    }

    /* While reloading, sprint changes locomotion only. Do not replace the
       reload viewmodel animation or its end callback. */
    if (!xziel_reloading)
        Weapon_PlayViewModelAnimation(ANIM_SPRINT_START, ContinueRun, 0);

    self.zoom = 3;
    self.sprint_delay = time + 1;
    self.sprinting = true;

    /* Stock NZ:P clears reload_delay here, which cancels the reload. Keep
       those timers intact. For ordinary sprint, preserve stock fire unlock. */
    if (!xziel_reloading)
        self.fire_delay2 = self.fire_delay = 0;
}'''

text = replace_function(text, "void() W_SprintStop =", sprint_stop)
text = replace_function(text, "void W_SprintStart ()", sprint_start)

weapon.write_text(text, encoding="utf-8")
print("Applied Xziel v0.25 reload-while-sprinting quick fix.")
