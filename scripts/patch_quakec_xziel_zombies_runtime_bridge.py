#!/usr/bin/env python3
"""Add a stable XZIEL semantic bridge for BO3-style perk/power-up systems.

Higher-level XZIEL systems (Wunderfizz, GobbleGum, scripted rewards) should call
these helpers rather than depend directly on NZ:P's internal numeric IDs.

This bridge exposes only primitives that already exist upstream. Widow's Wine,
Fire Sale and Death Machine intentionally return unsupported until their native
XZIEL implementations land.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_xziel_zombies_runtime_bridge.py <quakec-root>")

root = Path(sys.argv[1])
power_path = root / "source/server/entities/powerups.qc"
perk_path = root / "source/server/entities/perk_a_cola.qc"

power = power_path.read_text(encoding="utf-8")
perk = perk_path.read_text(encoding="utf-8")

power_marker = "// XZIEL_ZOMBIES_POWERUP_BRIDGE_BEGIN"
if power_marker not in power:
    power += r'''

// XZIEL_ZOMBIES_POWERUP_BRIDGE_BEGIN
// Stable semantic IDs owned by XZIEL, not by upstream NZ:P.
#define XZIEL_PU_NUKE          1
#define XZIEL_PU_INSTAKILL     2
#define XZIEL_PU_DOUBLEPOINTS  3
#define XZIEL_PU_CARPENTER     4
#define XZIEL_PU_MAXAMMO       5
#define XZIEL_PU_RANDOMPERK     6
#define XZIEL_PU_BONUSPOINTS   7
#define XZIEL_PU_FIRESALE      8
#define XZIEL_PU_DEATHMACHINE  9

float(float semantic_id) XZIEL_CorePowerupSupported =
{
    switch (semantic_id) {
        case XZIEL_PU_NUKE:
        case XZIEL_PU_INSTAKILL:
        case XZIEL_PU_DOUBLEPOINTS:
        case XZIEL_PU_CARPENTER:
        case XZIEL_PU_MAXAMMO:
        case XZIEL_PU_RANDOMPERK:
        case XZIEL_PU_BONUSPOINTS:
            return true;
        default:
            return false;
    }
};

float(float semantic_id) XZIEL_CorePowerupNativeId =
{
    switch (semantic_id) {
        case XZIEL_PU_NUKE: return PU_NUKE;
        case XZIEL_PU_INSTAKILL: return PU_INSTAKILL;
        case XZIEL_PU_DOUBLEPOINTS: return PU_DOUBLEPTS;
        case XZIEL_PU_CARPENTER: return PU_CARPENTER;
        case XZIEL_PU_MAXAMMO: return PU_MAXAMMO;
        case XZIEL_PU_RANDOMPERK: return PU_FREEPERK;
        case XZIEL_PU_BONUSPOINTS: return PU_BONUSPOINTS;
        default: return -1;
    }
};

float(vector where, float semantic_id) XZIEL_SpawnCorePowerup =
{
    float native_id = XZIEL_CorePowerupNativeId(semantic_id);
    if (native_id < 0)
        return false;

    Spawn_Powerup(where, native_id);
    return true;
};

float() XZIEL_PackAPunchGrantPrimitiveSupported =
{
    return true;
};

float(vector where) XZIEL_SpawnPackAPunchGrant =
{
    Spawn_Powerup(where, PU_UPGRADEWEAPON);
    return true;
};
// XZIEL_ZOMBIES_POWERUP_BRIDGE_END
'''

perk_marker = "// XZIEL_ZOMBIES_PERK_BRIDGE_BEGIN"
if perk_marker not in perk:
    perk += r'''

// XZIEL_ZOMBIES_PERK_BRIDGE_BEGIN
#define XZIEL_PERK_MULEKICK    1
#define XZIEL_PERK_JUGGERNOG   2
#define XZIEL_PERK_QUICKREVIVE 3
#define XZIEL_PERK_SPEEDCOLA   4
#define XZIEL_PERK_DOUBLETAP2  5
#define XZIEL_PERK_STAMINUP    6
#define XZIEL_PERK_DEADSHOT    7
#define XZIEL_PERK_WIDOWSWINE  8

float(float semantic_id) XZIEL_PerkSupported =
{
    switch (semantic_id) {
        case XZIEL_PERK_MULEKICK:
        case XZIEL_PERK_JUGGERNOG:
        case XZIEL_PERK_QUICKREVIVE:
        case XZIEL_PERK_SPEEDCOLA:
        case XZIEL_PERK_DOUBLETAP2:
        case XZIEL_PERK_STAMINUP:
        case XZIEL_PERK_DEADSHOT:
            return true;
        default:
            return false;
    }
};

float(float semantic_id) XZIEL_PerkNativeBit =
{
    switch (semantic_id) {
        case XZIEL_PERK_MULEKICK: return P_MULE;
        case XZIEL_PERK_JUGGERNOG: return P_JUG;
        case XZIEL_PERK_QUICKREVIVE: return P_REVIVE;
        case XZIEL_PERK_SPEEDCOLA: return P_SPEED;
        case XZIEL_PERK_DOUBLETAP2: return P_DOUBLE;
        case XZIEL_PERK_STAMINUP: return P_STAMIN;
        case XZIEL_PERK_DEADSHOT: return P_DEAD;
        default: return 0;
    }
};

float(entity player, float semantic_id) XZIEL_PlayerHasPerk =
{
    float perk_bit = XZIEL_PerkNativeBit(semantic_id);
    if (!perk_bit)
        return false;
    return (player.perks & perk_bit) != 0;
};

// Logic-only grant used by scripted reward systems. Presentation-aware systems
// should still route through the drink/machine sequence before calling this.
float(entity player, float semantic_id) XZIEL_GrantPerkLogic =
{
    float perk_bit = XZIEL_PerkNativeBit(semantic_id);
    if (!perk_bit || player == world || player.classname != "player")
        return false;
    if (player.perks & perk_bit)
        return false;

    entity old_self = self;
    self = player;
    GivePerk(perk_bit);
    self = old_self;
    return true;
};
// XZIEL_ZOMBIES_PERK_BRIDGE_END
'''

for text, begin, end in (
    (power, power_marker, "// XZIEL_ZOMBIES_POWERUP_BRIDGE_END"),
    (perk, perk_marker, "// XZIEL_ZOMBIES_PERK_BRIDGE_END"),
):
    if text.count(begin) != 1 or text.count(end) != 1:
        raise SystemExit(f"runtime bridge marker mismatch: {begin}")

required_power = [
    "XZIEL_CorePowerupSupported",
    "XZIEL_CorePowerupNativeId",
    "XZIEL_SpawnCorePowerup",
    "XZIEL_SpawnPackAPunchGrant",
]
for token in required_power:
    if power.count(token) < 1:
        raise SystemExit(f"missing power-up bridge token: {token}")

required_perk = [
    "XZIEL_PerkSupported",
    "XZIEL_PerkNativeBit",
    "XZIEL_PlayerHasPerk",
    "XZIEL_GrantPerkLogic",
]
for token in required_perk:
    if perk.count(token) < 1:
        raise SystemExit(f"missing perk bridge token: {token}")

power_path.write_text(power, encoding="utf-8")
perk_path.write_text(perk, encoding="utf-8")
print("Applied XZIEL Zombies semantic runtime bridge (7 perks, 7 power-ups, PaP grant primitive).")
