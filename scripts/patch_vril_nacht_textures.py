#!/usr/bin/env python3
"""Add opt-in external texture namespace for Nacht Enhanced.

Classic mode keeps the stock embedded BSP textures. Enhanced mode first looks
under textures/nacht_enhanced/<original texture name> and falls back to the
normal Vril texture path, then to the embedded WAD/BSP pixels.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_nacht_textures.py <vril-root>")

p = Path(sys.argv[1]) / "source" / "platform" / "sdl" / "gl" / "gl_model.c"
s = p.read_text(encoding="utf-8")

decl_anchor = 'cvar_t gl_subdivide_size = {"gl_subdivide_size", "128", true};\n'
decl = 'extern cvar_t xziel_nacht_enhanced;\n'
if decl not in s:
    if decl_anchor not in s:
        raise SystemExit("gl_model cvar anchor missing")
    s = s.replace(decl_anchor, decl_anchor + decl, 1)

old = '''\t\t\t\ttexture_mode = GL_LINEAR_MIPMAP_NEAREST;
\t\t\t\tsprintf (texname, "textures/%s", mt->name);
\t\t\t\ttx->gl_texturenum = Image_LoadImage (texname, IMAGE_TGA | IMAGE_PNG | IMAGE_JPG, 0, false, true);\t\t\t//Diabolickal TGA textures
\t\t\t\ttexture_mode = GL_LINEAR;

\t\t\t  \tif (tx->gl_texturenum < 0) {
\t\t\t\t\tdata = WAD3_LoadTexture(mt);
'''

new = '''\t\t\t\ttexture_mode = GL_LINEAR_MIPMAP_NEAREST;

\t\t\t\t// Nacht Enhanced is an opt-in presentation layer. Keep stock
\t\t\t\t// embedded BSP pixels untouched in Classic mode.
\t\t\t\ttx->gl_texturenum = -1;
\t\t\t\tif (xziel_nacht_enhanced.value >= 0.5f &&
\t\t\t\t\t(!strcmp(loadmodel->name, "maps/ndu.bsp") ||
					 !strcmp(loadmodel->name, "maps/ndu_enchanted.bsp"))) {
\t\t\t\t\tsnprintf (texname, sizeof(texname), "textures/nacht_enhanced/%s", mt->name);
\t\t\t\t\ttx->gl_texturenum = Image_LoadImage (texname, IMAGE_TGA | IMAGE_PNG | IMAGE_JPG, 0, false, true);
\t\t\t\t}

\t\t\t\t// Preserve Vril's existing generic external-texture behavior for
\t\t\t\t// anything not supplied by the Enhanced namespace.
\t\t\t\tif (tx->gl_texturenum < 0) {
\t\t\t\t\tsnprintf (texname, sizeof(texname), "textures/%s", mt->name);
\t\t\t\t\ttx->gl_texturenum = Image_LoadImage (texname, IMAGE_TGA | IMAGE_PNG | IMAGE_JPG, 0, false, true);
\t\t\t\t}
\t\t\t\ttexture_mode = GL_LINEAR;

\t\t\t  \tif (tx->gl_texturenum < 0) {
\t\t\t\t\tdata = WAD3_LoadTexture(mt);
'''

if 'textures/nacht_enhanced/%s' not in s:
    if old not in s:
        raise SystemExit("HL external-texture block not found")
    s = s.replace(old, new, 1)

# The SDL renderer historically requested zombie atlases as PCX-only even
# though the generic alias loader already supports TGA. Let the high-detail
# Enchanted overrides win while preserving PCX fallback for stock packages.
rmisc = Path(sys.argv[1]) / "source" / "platform" / "sdl" / "gl" / "gl_rmisc.c"
rs = rmisc.read_text(encoding="utf-8")
for i in range(4):
    old = f'Image_LoadImage ("models/ai/zfull.mdl_{i}", IMAGE_PCX, 0, true, false)'
    new = f'Image_LoadImage ("models/ai/zfull.mdl_{i}", IMAGE_TGA | IMAGE_PCX, 0, true, false)'
    rs = rs.replace(old, new)
rmisc.write_text(rs, encoding="utf-8")

p.write_text(s, encoding="utf-8")
print("Enabled opt-in Nacht Enhanced external texture and high-detail zombie-skin paths.")
