#!/usr/bin/env python3
"""Add Xziel mobile combat feedback to NZ:P QuakeC."""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_quakec_combatfx.py <quakec-root>")

root = Path(sys.argv[1])

# Standard Vril currently owns service 58 for HUD config. Xziel damage
# feedback therefore uses the next free server->client service, 59.
defs = root / "source/server/defs/standard.qc"
text = defs.read_text(encoding="utf-8")
anchor = "#define \tSVC_ACHIEVEMENT \t\t\t52\n"
if "SVC_XZIELDAMAGE" not in text:
    if anchor not in text:
        raise SystemExit("Could not find SVC_ACHIEVEMENT protocol anchor")
    text = text.replace(anchor, anchor + "#define     SVC_XZIELDAMAGE             59\n", 1)
defs.write_text(text, encoding="utf-8")

# Reliable one-client damage number event. FTE is intentionally a no-op here;
# Xziel Android uses the Standard Vril protocol path.
clientfuncs = root / "source/server/clientfuncs.qc"
text = clientfuncs.read_text(encoding="utf-8")
anchor = "void(entity who, float death_marker) nzp_hitmarker =\n"
if "nzp_damage_number" not in text:
    idx = text.find(anchor)
    if idx < 0:
        raise SystemExit("Could not find nzp_hitmarker insertion point")
    block = r'''
//
// nzp_damage_number(who, damage, critical)
// Xziel mobile floating combat text. Body damage is white, critical/headshot
// damage is gold on the client.
//
void(entity who, float damage, float critical) nzp_damage_number =
{
#ifndef FTE
	msg_entity = who;
	WriteByte(MSG_ONE, SVC_XZIELDAMAGE);
	WriteLong(MSG_ONE, rint(damage));
	WriteByte(MSG_ONE, critical);
#endif
};

'''
    text = text[:idx] + block + text[idx:]
clientfuncs.write_text(text, encoding="utf-8")

damage = root / "source/server/damage.qc"
text = damage.read_text(encoding="utf-8")
if "void(entity who, float damage, float critical) nzp_damage_number;" not in text:
    insert_at = text.find("void(entity attacker, float d_style) DieHandler")
    if insert_at < 0:
        raise SystemExit("Could not find damage handler declaration point")
    text = text[:insert_at] + (
        "void(entity who, float damage, float critical) nzp_damage_number;\n\n"
    ) + text[insert_at:]

if "nzp_damage_number(attacker" not in text:
    # Locate the current zombie/dog branch inside DamageHandler semantically.
    # Do not depend on exact indentation or blank-line layout from upstream.
    damage_sig = "void(entity victim, entity attacker, float damage, float d_style) DamageHandler ="
    damage_start = text.find(damage_sig)
    if damage_start < 0:
        raise SystemExit("Could not find DamageHandler")
    branch_marker = 'if (victim.classname == "ai_zombie" || victim.classname == "ai_dog") {'
    branch_pos = text.find(branch_marker, damage_start)
    if branch_pos < 0:
        raise SystemExit("Could not find zombie/dog branch inside DamageHandler")
    line_end = text.find("\n", branch_pos)
    if line_end < 0:
        raise SystemExit("Could not find end of zombie/dog branch line")
    line_end += 1
    damage_hook = (
        "\t\t/* Xziel floating damage numbers; gameplay damage stays server-authoritative. */\n"
        "\t\tif (attacker.classname == \"player\" && d_style != DMG_TYPE_OTHER && damage > 0)\n"
        "\t\t\tnzp_damage_number(attacker, damage, d_style == DMG_TYPE_HEADSHOT);\n\n"
    )
    text = text[:line_end] + damage_hook + text[line_end:]

damage.write_text(text, encoding="utf-8")

print("Patched QuakeC Xziel combat feedback.")
