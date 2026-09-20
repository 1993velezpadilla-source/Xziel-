#!/usr/bin/env python3
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_mobile.py <quakec-root>")

root = Path(sys.argv[1])

def replace_function(text, signature, replacement):
    start = text.find(signature)
    if start < 0:
        raise SystemExit(f"Could not find QC function: {signature}")
    brace = text.find("{", start)
    if brace < 0:
        raise SystemExit(f"Could not find body for QC function: {signature}")
    depth = 0
    end = -1
    for i in range(brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end < 0:
        raise SystemExit(f"Unterminated QC function: {signature}")
    # consume a trailing semicolon if present
    if end < len(text) and text[end] == ";":
        end += 1
    return text[:start] + replacement + text[end:]

# ---------------------------------------------------------------------------
# Export all three native weapon slots as scalar fields for Vril networking.
# ---------------------------------------------------------------------------
custom = root / "source/server/defs/custom.qc"
text = custom.read_text(encoding="utf-8")
anchor = ".float weapon_count;\n"
fields = """.float xziel_weapon1_id;
.float xziel_weapon1_mag;
.float xziel_weapon1_reserve;
.float xziel_weapon2_id;
.float xziel_weapon2_mag;
.float xziel_weapon2_reserve;
.float xziel_weapon3_id;
.float xziel_weapon3_mag;
.float xziel_weapon3_reserve;
"""
if "xziel_weapon1_id" not in text:
    if anchor not in text:
        raise SystemExit("Could not find weapon_count field anchor")
    text = text.replace(anchor, anchor + fields, 1)
custom.write_text(text, encoding="utf-8")

# weapon_utilities.qc is compiled before weapon_core.qc, so declare the helper
# here and define it later in weapon_core.qc.
text = custom.read_text(encoding="utf-8")
prototype_anchor = ".float weapon_count;\n"
prototype = "float(float weapon_id) Xziel_IsPistolWeapon;\n"
if prototype not in text:
    if prototype_anchor not in text:
        raise SystemExit("Could not find pistol-helper prototype anchor")
    text = text.replace(prototype_anchor, prototype_anchor + prototype, 1)
custom.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Inventory rules.
# Stock mode keeps classic Zombies capacity.
# Unlimited Pistol mode unlocks three total guns without Mule Kick and protects
# a pistol-family weapon from ordinary weapon replacement.
# ---------------------------------------------------------------------------
util = root / "source/server/utilities/weapon_utilities.qc"
text = util.read_text(encoding="utf-8")

set_active = r'''void Weapon_SetActiveInSlot(float slot, float play_first_raise)
{
    float weapon_count = 0;
    float rotations = 0;

    if (slot < 0)
        slot = 0;
    if (slot >= MAX_PLAYER_WEAPONS)
        slot = MAX_PLAYER_WEAPONS - 1;

    for (float i = 0; i < MAX_PLAYER_WEAPONS; i++) {
        if (self.weapons[i].weapon_id != 0)
            weapon_count++;
    }

    if (weapon_count <= 0)
        return;
    if (slot >= weapon_count)
        return;

    /* Weapon_SwapWeapons rotates right:
         [A,B]   -> [B,A]
         [A,B,C] -> [C,A,B]
       Therefore an exact array index needs (count - slot) rotations, modulo
       count. This makes the touch cards deterministic with either 2 or 3 guns. */
    if (slot != 0)
        rotations = weapon_count - slot;

    for (float i = 0; i < rotations; i++)
        Weapon_SwapWeapons(false);

    self.weapon = self.weapons[0].weapon_id;

    if (GetFrame(self.weapon, FIRST_TAKE_START) != 0 && play_first_raise == true)
        Weapon_PlayViewModelAnimation(ANIM_FIRST_TAKE, ReturnWeaponModel, 0);
    else
        Weapon_PlayViewModelAnimation(ANIM_TAKE_OUT, ReturnWeaponModel, 0);

    self.weaponskin = self.weapons[0].weapon_skin;
    self.weapon_tier = self.weapons[0].weapon_tier;
    self.Weapon_Name = GetWeaponName(self.weapon, self.weapons[0].weapon_tier);

#ifndef FTE
    self.weapon2skin = self.weapons[0].weapon_skin;
    self.Flash_Offset = GetWeaponFlash_Offset(self.weapon);
    self.Flash_Size = GetWeaponFlash_Size(self.weapon);
    self.ADS_Offset = GetWeaponADSOfs(self.weapon);
#endif
};'''
text = replace_function(text, "void Weapon_SetActiveInSlot(float slot, float play_first_raise)", set_active)

text = text.replace(
'''    if ((self.perks & P_MULE))
        weapon_slots = MULEKICK_WEAPON_SLOT;
    else
        weapon_slots = MULEKICK_WEAPON_SLOT - 1;''',
'''    if ((self.perks & P_MULE))
        weapon_slots = MULEKICK_WEAPON_SLOT;
    else
        weapon_slots = MULEKICK_WEAPON_SLOT - 1;''',
1)

text = text.replace(
'''    if (weapon_slot == MULEKICK_WEAPON_SLOT - 1 && Weapon_HasNoMulekickWeapon())
        self.weapons[weapon_slot].is_mulekick_weapon = true;''',
'''    if ((self.perks & P_MULE) &&
        weapon_slot == MULEKICK_WEAPON_SLOT - 1 &&
        Weapon_HasNoMulekickWeapon())
        self.weapons[weapon_slot].is_mulekick_weapon = true;
    else if (!(self.perks & P_MULE) && weapon_slot == MULEKICK_WEAPON_SLOT - 1)
        self.weapons[weapon_slot].is_mulekick_weapon = false;''',
1)


give_weapon = r'''void Weapon_GiveWeapon(float weapon_id, float weapon_mag, float weapon_reserve, float weapon_tier)
{
    W_HideCrosshair(self);

    float should_leave = false;
    float unlimited_pistol = cvar("xziel_mobile_unlimited_pistol") >= 0.5;
    float weapon_slots = MULEKICK_WEAPON_SLOT - 1;

    /* Xziel mobile option:
       OFF -> stock Zombies capacity (2, or 3 with Mule Kick).
       ON  -> 3 total guns without Mule Kick: two ordinary weapons plus a
              protected pistol family slot. Magazine/reload behavior stays native. */
    if (unlimited_pistol || (self.perks & P_MULE))
        weapon_slots = MULEKICK_WEAPON_SLOT;

    /* If Unlimited Pistol is enabled and we are receiving a pistol, replace
       the existing pistol rather than consuming/replacing an ordinary gun. */
    if (unlimited_pistol && Xziel_IsPistolWeapon(weapon_id)) {
        for (float i = 0; i < MAX_PLAYER_WEAPONS; i++) {
            if (self.weapons[i].weapon_id != 0 &&
                Xziel_IsPistolWeapon(self.weapons[i].weapon_id)) {
                Weapon_SetActiveInSlot(i, false);
                Weapon_AssignWeapon(0, weapon_id, weapon_mag, weapon_reserve, weapon_tier);
                return;
            }
        }
    }

    /* Use any free slot exposed by the current capacity model. */
    for (float i = 0; i < weapon_slots; i++) {
        if (self.weapons[i].weapon_id == 0) {
            Weapon_AssignWeapon(i, weapon_id, weapon_mag, weapon_reserve, weapon_tier);
            should_leave = true;
            break;
        }
    }

    if (should_leave)
        return;

    if (unlimited_pistol && !Xziel_IsPistolWeapon(weapon_id)) {
        /* Never replace the only pistol with an ordinary purchase/pickup.
           Prefer the current weapon if it is non-pistol; otherwise rotate the
           first non-pistol into slot 0 and replace that one. */
        if (self.weapons[0].weapon_id != 0 &&
            !Xziel_IsPistolWeapon(self.weapons[0].weapon_id)) {
            Weapon_AssignWeapon(0, weapon_id, weapon_mag, weapon_reserve, weapon_tier);
            return;
        }

        for (float i = 1; i < weapon_slots; i++) {
            if (self.weapons[i].weapon_id != 0 &&
                !Xziel_IsPistolWeapon(self.weapons[i].weapon_id)) {
                Weapon_SetActiveInSlot(i, false);
                Weapon_AssignWeapon(0, weapon_id, weapon_mag, weapon_reserve, weapon_tier);
                return;
            }
        }
    }

    /* Stock fallback: all eligible slots occupied, replace current weapon. */
    Weapon_AssignWeapon(0, weapon_id, weapon_mag, weapon_reserve, weapon_tier);
};'''
text = replace_function(text, "void Weapon_GiveWeapon(float weapon_id, float weapon_mag, float weapon_reserve, float weapon_tier)", give_weapon)


util.write_text(text, encoding="utf-8")

# ---------------------------------------------------------------------------
# Weapon runtime: infinite pistol reserve, slot export, direct slot impulses.
# ---------------------------------------------------------------------------
core = root / "source/server/weapons/weapon_core.qc"
text = core.read_text(encoding="utf-8")

if "Xziel_IsPistolWeapon" not in text:
    insert_at = text.find("inline void() WeaponCore_UpdateWeaponStats")
    if insert_at < 0:
        raise SystemExit("Could not find WeaponCore_UpdateWeaponStats")
    helper = r'''
float(float weapon_id) Xziel_IsPistolWeapon =
{
    switch (weapon_id) {
        case W_COLT:
        case W_357:
        case W_BIATCH:
        case W_KILLU:
            return true;
        default:
            return false;
    }
};

'''
    text = text[:insert_at] + helper + text[insert_at:]

update_stats = r'''void() WeaponCore_UpdateWeaponStats =
{
    /* Unlimited pistol mode refills RESERVE only. Magazine capacity and native
       reload timing remain untouched, so the player still has to reload. */
    if (cvar("xziel_mobile_unlimited_pistol") >= 0.5) {
        for (float i = 0; i < MAX_PLAYER_WEAPONS; i++) {
            if (self.weapons[i].weapon_id != 0 &&
                Xziel_IsPistolWeapon(self.weapons[i].weapon_id)) {
                self.weapons[i].weapon_reserve =
                    getWeaponAmmo(self.weapons[i].weapon_id);
            }
        }
    }

    self.currentammo = self.weapons[0].weapon_reserve;
    self.currentmag = self.weapons[0].weapon_magazine;
    self.currentmag2 = self.weapons[0].weapon_magazine_left;

    /* Arrays/structs are not directly networked by the standard protocol.
       Flatten the three inventory slots into scalar fields for Vril. */
    self.xziel_weapon1_id = self.weapons[0].weapon_id;
    self.xziel_weapon1_mag = self.weapons[0].weapon_magazine;
    self.xziel_weapon1_reserve = self.weapons[0].weapon_reserve;

    self.xziel_weapon2_id = self.weapons[1].weapon_id;
    self.xziel_weapon2_mag = self.weapons[1].weapon_magazine;
    self.xziel_weapon2_reserve = self.weapons[1].weapon_reserve;

    self.xziel_weapon3_id = self.weapons[2].weapon_id;
    self.xziel_weapon3_mag = self.weapons[2].weapon_magazine;
    self.xziel_weapon3_reserve = self.weapons[2].weapon_reserve;

#ifdef FTE
    self.weapon2modelindex = getmodelindex(self.weapon2model);
#endif
};'''
text = replace_function(text, "inline void() WeaponCore_UpdateWeaponStats", update_stats)

# Add direct mobile slot selection impulses. Slot 0 is already active; 60/61
# select the other visible cards in the native rotating inventory.
impulse_anchor = '''\t\tcase 33:
\t\t\tW_PrimeBetty();
\t\t\tbreak;'''
impulse_add = '''\t\tcase 33:
\t\t\tW_PrimeBetty();
\t\t\tbreak;
\t\tcase 60:
\t\t\tif (self.weapons[1].weapon_id != 0)
\t\t\t\tWeapon_SetActiveInSlot(1, false);
\t\t\tbreak;
\t\tcase 61:
\t\t\tif (self.weapons[2].weapon_id != 0)
\t\t\t\tWeapon_SetActiveInSlot(2, false);
\t\t\tbreak;'''
if "case 60:" not in text:
    if impulse_anchor not in text:
        raise SystemExit("Could not find impulse 33 anchor")
    text = text.replace(impulse_anchor, impulse_add, 1)

core.write_text(text, encoding="utf-8")

print("Patched QuakeC for Xziel mobile weapon inventory.")
