#!/usr/bin/env python3
"""Enable strict missing-asset behavior for verified XZIEL map packages.

Legacy NZ:P behavior is preserved unless -xzielstrictassets is present.
Imported .xzp maps use that flag so missing models or SFX cannot be silently
substituted/skipped during AAA parity validation.
"""

from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_xziel_strict_assets.py <vril-root>")

root = Path(sys.argv[1]).resolve()
model_path = root / "source/platform/sdl/gl/gl_model.c"
parse_path = root / "source/cl_parse.c"
sound_path = root / "source/snd_mem.c"

model = model_path.read_text(encoding="utf-8")
parse = parse_path.read_text(encoding="utf-8")
sound = sound_path.read_text(encoding="utf-8")

model_marker = "XZIEL_STRICT_MISSING_MODEL"
if model_marker not in model:
    old = '''	if (!buf)
	{
		// Reload with another .mdl
		buf = (unsigned *)COM_LoadStackFile("models/missing_model.mdl", stackbuf, sizeof(stackbuf));
'''
    if old not in model:
        raise SystemExit("missing SDL model fallback anchor")
    new = '''	if (!buf)
	{
		/* XZIEL_STRICT_MISSING_MODEL */
		if (COM_CheckParm("-xzielstrictassets"))
			Sys_Error("XZIEL strict assets: missing model %s", mod->name);

		// Legacy NZ:P behavior outside strict imported-map mode.
		// Reload with another .mdl
		buf = (unsigned *)COM_LoadStackFile("models/missing_model.mdl", stackbuf, sizeof(stackbuf));
'''
    model = model.replace(old, new, 1)

parse_marker = "XZIEL_STRICT_PRECACHE_MODEL"
if parse_marker not in parse:
    old = '''		// rbaldwin2 -- At last resort use a missing model
		if (cl.model_precache[i] == NULL)
		{
			cl.model_precache[i] = Mod_ForName("models/missing_model.mdl", false);
		}
'''
    if old not in parse:
        raise SystemExit("missing client precache fallback anchor")
    new = '''		// rbaldwin2 -- At last resort use a missing model
		if (cl.model_precache[i] == NULL)
		{
			/* XZIEL_STRICT_PRECACHE_MODEL */
			if (COM_CheckParm("-xzielstrictassets"))
				Host_Error("XZIEL strict assets: failed model precache %s", model_precache[i]);

			cl.model_precache[i] = Mod_ForName("models/missing_model.mdl", false);
		}
'''
    parse = parse.replace(old, new, 1)

sound_marker = "XZIEL_STRICT_MISSING_SFX"
if sound_marker not in sound:
    old = '''	if (!(data = COM_LoadStackFile(namebuffer, stackbuf, sizeof(stackbuf))))
	{
		Con_Printf ("Couldn't load %s\n", namebuffer);
		return NULL;
	}
'''
    if old not in sound:
        raise SystemExit("missing sound fallback anchor")
    new = '''	if (!(data = COM_LoadStackFile(namebuffer, stackbuf, sizeof(stackbuf))))
	{
		/* XZIEL_STRICT_MISSING_SFX */
		if (COM_CheckParm("-xzielstrictassets"))
			Host_Error("XZIEL strict assets: missing SFX %s", namebuffer);

		Con_Printf ("Couldn't load %s\n", namebuffer);
		return NULL;
	}
'''
    sound = sound.replace(old, new, 1)

for label, text_value, marker in (
    ("model", model, model_marker),
    ("parse", parse, parse_marker),
    ("sound", sound, sound_marker),
):
    if text_value.count(marker) != 1:
        raise SystemExit(f"{label}: strict asset marker count drift for {marker}")

model_path.write_text(model, encoding="utf-8")
parse_path.write_text(parse, encoding="utf-8")
sound_path.write_text(sound, encoding="utf-8")

print("Injected XZIEL strict missing-model/SFX mode (legacy behavior preserved without flag).")
