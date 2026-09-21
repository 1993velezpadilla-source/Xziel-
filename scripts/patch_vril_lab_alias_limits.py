#!/usr/bin/env python3
"""Raise alias-model budgets only for the SDL/Android renderer.

The Enchanted Lab's CC0 zombie is intentionally kept at source quality instead
of being crushed below legacy Quake's 2K vertex/triangle defaults.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_lab_alias_limits.py <vril-root>")

root = Path(sys.argv[1])
model_h = root / "source/platform/sdl/gl/gl_model.h"
r_local = root / "source/platform/sdl/r_local.h"
mesh_c = root / "source/platform/sdl/gl/gl_mesh.c"

s = model_h.read_text(encoding="utf-8")
if "#define\tMAXALIASVERTS\t8192" not in s:
    if "#define\tMAXALIASVERTS\t2048" not in s or "#define\tMAXALIASTRIS\t2048" not in s:
        raise SystemExit("SDL alias limit anchors changed")
    s = s.replace("#define\tMAXALIASVERTS\t2048", "#define\tMAXALIASVERTS\t8192", 1)
    s = s.replace("#define\tMAXALIASTRIS\t2048", "#define\tMAXALIASTRIS\t8192", 1)
model_h.write_text(s, encoding="utf-8")

s = r_local.read_text(encoding="utf-8")
if "#define MAXALIASVERTS\t\t8192" not in s:
    if "#define MAXALIASVERTS\t\t2000" not in s:
        raise SystemExit("SDL r_local alias vertex anchor changed")
    s = s.replace(
        "#define MAXALIASVERTS\t\t2000\t// TODO: tune this",
        "#define MAXALIASVERTS\t\t8192\t// Xziel Android Lab alias budget",
        1,
    )
r_local.write_text(s, encoding="utf-8")

s = mesh_c.read_text(encoding="utf-8")
repls = {
    "qboolean\tused[8192];":
        "qboolean\tused[MAXALIASTRIS];",
    "int\t\tcommands[8192];":
        "int\t\tcommands[MAXALIASTRIS * 7 + 1];",
    "int\t\tvertexorder[8192];":
        "int\t\tvertexorder[MAXALIASTRIS * 3];",
    "int\t\tstripverts[128];":
        "int\t\tstripverts[MAXALIASTRIS + 2];",
    "int\t\tstriptris[128];":
        "int\t\tstriptris[MAXALIASTRIS];",
    "\tint \tbestverts[1024];":
        "\tstatic int bestverts[MAXALIASTRIS + 2];",
    "\tint \tbesttris[1024];":
        "\tstatic int besttris[MAXALIASTRIS];",
}
for old, new in repls.items():
    if new in s:
        continue
    if old not in s:
        raise SystemExit(f"SDL gl_mesh anchor changed: {old!r}")
    s = s.replace(old, new, 1)

# Belt-and-suspenders checks before emitting into the display-list buffers.
emit_anchor = '''\tcommands[numcommands++] = 0;\t\t// end of list marker
'''
guard = '''\tif (numorder > MAXALIASTRIS * 3)
\t\tSys_Error("alias %s generated too many reordered vertices: %d", aliasmodel->name, numorder);
\tif (numcommands >= MAXALIASTRIS * 7 + 1)
\t\tSys_Error("alias %s generated too many GL commands: %d", aliasmodel->name, numcommands);

\tcommands[numcommands++] = 0;\t\t// end of list marker
'''
if "generated too many GL commands" not in s:
    if emit_anchor not in s:
        raise SystemExit("SDL alias display-list terminator anchor changed")
    s = s.replace(emit_anchor, guard, 1)

mesh_c.write_text(s, encoding="utf-8")
print("Raised SDL/Android alias budget to 8192 vertices/triangles with sized GL buffers.")
