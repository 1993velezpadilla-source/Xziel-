#!/usr/bin/env python3
"""Xziel v0.25 readability pass.

Final authority after v0.24:
- larger jump/slide/use/reload pictograms at phone size;
- larger default jump/slide visual buttons;
- retains dedicated physical-gun silhouette routing.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_mobile_v025.py <vril-root>")

root = Path(sys.argv[1])
hud = root / "source" / "render" / "r_hud.c"

def replace_function(src: str, signature: str, replacement: str) -> str:
    start = src.find(signature)
    if start < 0:
        raise SystemExit("Could not find function: " + signature)
    brace = src.find("{", start)
    if brace < 0:
        raise SystemExit("Could not find body: " + signature)
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
    return src[:start] + replacement + src[end:]

text = hud.read_text(encoding="utf-8")

action_glyph = r'''static qboolean Xziel_DrawActionGlyph(int cx, int cy, int radius,
	const char *label1, const char *label2, qboolean pressed)
{
	image_t icon = Xziel_ActionIcon(label1, label2);
	float factor = 1.00f;
	int size;
	int alpha;

	if (!icon)
		return false;

	if (!strcmp(label1, "FIRE"))
		factor = 1.23f;
	else if (!strcmp(label1, "ADS") && label2 && !strcmp(label2, "FIRE"))
		factor = 1.23f;
	else if (!strcmp(label1, "ADS"))
		factor = 1.10f;
	else if (!strcmp(label1, "RLD"))
		factor = 1.16f;
	else if (!strcmp(label1, "JUMP"))
		factor = 1.38f;
	else if (!strcmp(label1, "SLIDE"))
		factor = 1.42f;
	else if (!strcmp(label1, "USE"))
		factor = 1.16f;
	else if (!strcmp(label1, "KNIFE"))
		factor = 1.12f;
	else if (!strcmp(label1, "NADE"))
		factor = 1.10f;

	size = (int)(radius * factor);
	if (size < 16)
		size = 16;

	alpha = pressed ? 255 : 250;
	Draw_ColoredStretchPic(cx - size/2, cy - size/2, icon,
		size, size, 255,255,255,alpha);
	return true;
}'''

sig = "static qboolean Xziel_DrawActionGlyph("
pos = text.rfind(sig)
if pos < 0:
    raise SystemExit("v0.25 final action glyph missing")
text = text[:pos] + replace_function(text[pos:], sig, action_glyph)

# Increase only the default visual radius for the two small human-action
# buttons. Custom HUD per-control scale still remains authoritative.
text = text.replace(
    'Xziel_DrawTouchButton(xziel_hud_jump_x.value, xziel_hud_jump_y.value,\n\t\t0.044f, "JUMP", "", xziel_mobile_jump_pressed, editor);',
    'Xziel_DrawTouchButton(xziel_hud_jump_x.value, xziel_hud_jump_y.value,\n\t\t0.050f, "JUMP", "", xziel_mobile_jump_pressed, editor);',
    1,
)
text = text.replace(
    'Xziel_DrawTouchButton(xziel_hud_slide_x.value, xziel_hud_slide_y.value,\n\t\t0.044f, "SLIDE", "", xziel_mobile_slide_pressed, editor);',
    'Xziel_DrawTouchButton(xziel_hud_slide_x.value, xziel_hud_slide_y.value,\n\t\t0.050f, "SLIDE", "", xziel_mobile_slide_pressed, editor);',
    1,
)

hud.write_text(text, encoding="utf-8")
print("Applied Xziel v0.25 phone-readable action icons.")
