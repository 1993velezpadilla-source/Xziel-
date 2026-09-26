#!/usr/bin/env python3
"""Add source-backed Wall Power / Crate Power PaP event plumbing.

The BO3 source shows:
- Wall Power stays enabled until a wall purchase can actually be upgraded;
- Crate Power stays enabled until the Mystery Box final reward can actually
  be upgraded;
- the gum is consumed only when the upgrade happens.

XZIEL adds one additional safety gate: the resolved upgraded identity must have
nativeRuntimeStatus=ready in the committed PaP catalog. This prevents an event
gum from exposing an upgraded identity whose gameplay/presentation is not ready.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_xziel_gobblegum_pap_events.py <quakec-root>")

root = Path(sys.argv[1])
custom_path = root / "source/server/defs/custom.qc"
utils_path = root / "source/server/utilities/weapon_utilities.qc"
wall_path = root / "source/server/entities/wall_weapon.qc"
box_path = root / "source/server/entities/mystery_box.qc"

custom = custom_path.read_text(encoding="utf-8")
utils = utils_path.read_text(encoding="utf-8")
wall = wall_path.read_text(encoding="utf-8")
box = box_path.read_text(encoding="utf-8")

if "// XZIEL_GOBBLEGUM_PAP_EVENT_STATE_BEGIN" not in custom:
    custom += r'''

// XZIEL_GOBBLEGUM_PAP_EVENT_STATE_BEGIN
#define XZIEL_GUM_CRATE_POWER 14
#define XZIEL_GUM_WALL_POWER  62
.float xziel_gum_active_event_identity;
// XZIEL_GOBBLEGUM_PAP_EVENT_STATE_END
'''

if "// XZIEL_GOBBLEGUM_PAP_EVENT_RUNTIME_BEGIN" not in utils:
    utils += r'''

// XZIEL_GOBBLEGUM_PAP_EVENT_RUNTIME_BEGIN
float(entity player, float gum_identity) XZIEL_GobbleGumActivatePapEvent =
{
    if (player == world || player.classname != "player")
        return false;

    if (gum_identity != XZIEL_GUM_WALL_POWER &&
        gum_identity != XZIEL_GUM_CRATE_POWER)
        return false;

    if (player.xziel_gum_held_identity != gum_identity)
        return false;

    player.xziel_gum_active_event_identity = gum_identity;
    player.xziel_gum_held_identity = 0;
    player.xziel_gum_held_uses_remaining = 0;
    return true;
};

float(entity player, float base_weapon_id, float expected_gum) XZIEL_GobbleGumResolvePapEventUpgrade =
{
    if (player == world || player.classname != "player")
        return base_weapon_id;

    if (player.xziel_gum_active_event_identity != expected_gum)
        return base_weapon_id;

    float upgraded_id = XZIEL_GetPackAPunchWeaponID(base_weapon_id);
    if (upgraded_id == W_NOWEP)
        return base_weapon_id;

    // Zero-broken-reward gate: a source-verified PaP identity is not enough.
    if (!XZIEL_PackAPunchRuntimeReady(upgraded_id))
        return base_weapon_id;

    // BO3 consumes Wall/Crate Power only when the upgrade actually succeeds.
    player.xziel_gum_active_event_identity = 0;
    return upgraded_id;
};

float(entity player, float base_weapon_id) XZIEL_GobbleGumResolveWallPowerWeapon =
{
    return XZIEL_GobbleGumResolvePapEventUpgrade(
        player, base_weapon_id, XZIEL_GUM_WALL_POWER
    );
};

float(entity player, float base_weapon_id) XZIEL_GobbleGumResolveCratePowerWeapon =
{
    return XZIEL_GobbleGumResolvePapEventUpgrade(
        player, base_weapon_id, XZIEL_GUM_CRATE_POWER
    );
};
// XZIEL_GOBBLEGUM_PAP_EVENT_RUNTIME_END
'''

wall_marker = "// XZIEL_GOBBLEGUM_WALL_POWER_HOOK"
if wall_marker not in wall:
    old = '''		tempe = self;
		self = other;

		Weapon_GiveWeapon(tempe.weapon, 0, 0, 0);

		self = tempe;
'''
    if old not in wall:
        raise SystemExit("could not find standard wall-buy Weapon_GiveWeapon anchor")
    new = '''		tempe = self;
		self = other;

        // XZIEL_GOBBLEGUM_WALL_POWER_HOOK
        float xziel_wall_weapon = XZIEL_GobbleGumResolveWallPowerWeapon(
            self, tempe.weapon
        );
		Weapon_GiveWeapon(xziel_wall_weapon, 0, 0, 0);

		self = tempe;
'''
    wall = wall.replace(old, new, 1)

box_marker = "// XZIEL_GOBBLEGUM_CRATE_POWER_HOOK"
if box_marker not in box:
    old = '''		if (random() > leave_chance) {		//teddy gen threshold, high means less chance
			self.owner.boxstatus = 2;
			self.weapon = tempf;
			self.nextthink = time + 5;
'''
    if old not in box:
        raise SystemExit("could not find final Mystery Box reward anchor")
    new = '''		if (random() > leave_chance) {		//teddy gen threshold, high means less chance
            // XZIEL_GOBBLEGUM_CRATE_POWER_HOOK
            tempf = XZIEL_GobbleGumResolveCratePowerWeapon(
                self.owner.owner, tempf
            );
            temps = GetWeaponModel(tempf, 1);
            setmodel(self, temps);
			self.owner.boxstatus = 2;
			self.weapon = tempf;
			self.nextthink = time + 5;
'''
    box = box.replace(old, new, 1)

checks = {
    "custom": (
        custom,
        [
            "// XZIEL_GOBBLEGUM_PAP_EVENT_STATE_BEGIN",
            "// XZIEL_GOBBLEGUM_PAP_EVENT_STATE_END",
        ],
    ),
    "utils": (
        utils,
        [
            "// XZIEL_GOBBLEGUM_PAP_EVENT_RUNTIME_BEGIN",
            "// XZIEL_GOBBLEGUM_PAP_EVENT_RUNTIME_END",
            "float(entity player, float gum_identity) XZIEL_GobbleGumActivatePapEvent =",
            "float(entity player, float base_weapon_id) XZIEL_GobbleGumResolveWallPowerWeapon =",
            "float(entity player, float base_weapon_id) XZIEL_GobbleGumResolveCratePowerWeapon =",
        ],
    ),
    "wall": (wall, [wall_marker]),
    "box": (box, [box_marker]),
}
for file_name, (text_value, markers) in checks.items():
    for marker in markers:
        if text_value.count(marker) != 1:
            raise SystemExit(f"{file_name}: marker/signature count mismatch for {marker}")

custom_path.write_text(custom, encoding="utf-8")
utils_path.write_text(utils, encoding="utf-8")
wall_path.write_text(wall, encoding="utf-8")
box_path.write_text(box, encoding="utf-8")

print(
    "Applied XZIEL Wall Power / Crate Power event plumbing "
    "(runtime-readiness gated; zero upgraded variants currently exposed)."
)
