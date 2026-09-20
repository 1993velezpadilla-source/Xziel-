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

# ---------------------------------------------------------------------------
# Inventory rules: optional third slot without requiring Mule Kick.
# ---------------------------------------------------------------------------
util = root / "source/server/utilities/weapon_utilities.qc"
text = util.read_text(encoding="utf-8")

set_active = r'''void Weapon_SetActiveInSlot(float slot, float play_first_raise)
{
    if (slot < 0)
        slot = 0;
    if (slot >= MAX_PLAYER_WEAPONS)
        slot = MAX_PLAYER_WEAPONS - 1;

    /* Native inventory is a rotating three-slot array. Rotate exactly as many
       positions as the requested HUD slot instead of treating every non-zero
       slot as "next weapon". */
    for (float i = 0; i < slot; i++)
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
'''    if ((self.perks & P_MULE) || cvar("xziel_mobile_unlimited_pistol") >= 0.5)
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

update_stats = r'''inline void() WeaponCore_UpdateWeaponStats =
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
impulse_anchor = '''        case 33:
            W_PrimeBetty();
            break;'''
impulse_add = '''        case 33:
            W_PrimeBetty();
            break;
        case 60:
            if (self.weapons[1].weapon_id != 0)
                Weapon_SetActiveInSlot(1, false);
            break;
        case 61:
            if (self.weapons[2].weapon_id != 0)
                Weapon_SetActiveInSlot(2, false);
            break;'''
if "case 60:" not in text:
    if impulse_anchor not in text:
        raise SystemExit("Could not find impulse 33 anchor")
    text = text.replace(impulse_anchor, impulse_add, 1)

core.write_text(text, encoding="utf-8")

print("Patched QuakeC for Xziel mobile weapon inventory.")
