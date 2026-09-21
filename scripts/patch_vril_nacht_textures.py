#!/usr/bin/env python3
"""Bind Enchanted external textures to the separate ndu_enchanted BSP only.

Stock ndu always follows Vril's normal texture path. The Lab BSP first checks
textures/nacht_enhanced/<original texture name>, then Vril's generic external
texture path, then the embedded WAD/BSP pixels.
"""
from pathlib import Path
import sys

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_vril_nacht_textures.py <vril-root>")

p = Path(sys.argv[1]) / "source" / "platform" / "sdl" / "gl" / "gl_model.c"
s = p.read_text(encoding="utf-8")

old = '''\t\t\t\ttexture_mode = GL_LINEAR_MIPMAP_NEAREST;
\t\t\t\tsprintf (texname, "textures/%s", mt->name);
\t\t\t\ttx->gl_texturenum = Image_LoadImage (texname, IMAGE_TGA | IMAGE_PNG | IMAGE_JPG, 0, false, true);\t\t\t//Diabolickal TGA textures
\t\t\t\ttexture_mode = GL_LINEAR;

\t\t\t \tif (tx->gl_texturenum < 0) {
\t\t\t\t\tdata = WAD3_LoadTexture(mt);
'''

new = '''\t\t\t\ttexture_mode = GL_LINEAR_MIPMAP_NEAREST;

\t\t\t\t// Xziel Lab textures are tied to the separate BSP identity.
\t\t\t\t// Stock maps can never inherit them from a persisted cvar.
\t\t\t\ttx->gl_texturenum = -1;
\t\t\t\tif (!strcmp(loadmodel->name, "maps/ndu_enchanted.bsp")) {
\t\t\t\t\tsnprintf (texname, sizeof(texname), "textures/nacht_enhanced/%s", mt->name);
\t\t\t\t\ttx->gl_texturenum = Image_LoadImage (texname, IMAGE_TGA | IMAGE_PNG | IMAGE_JPG, 0, false, true);
\t\t\t\t}

\t\t\t\t// Preserve Vril's existing generic external-texture behavior.
\t\t\t\tif (tx->gl_texturenum < 0) {
\t\t\t\t\tsnprintf (texname, sizeof(texname), "textures/%s", mt->name);
\t\t\t\t\ttx->gl_texturenum = Image_LoadImage (texname, IMAGE_TGA | IMAGE_PNG | IMAGE_JPG, 0, false, true);
\t\t\t\t}
\t\t\t\ttexture_mode = GL_LINEAR;

\t\t\t \tif (tx->gl_texturenum < 0) {
\t\t\t\t\tdata = WAD3_LoadTexture(mt);

\t\t\t\t\t// Never hand GL_Upload32 a NULL source. A malformed/portable
\t\t\t\t\t// package may be missing a WAD or external texture; keep the
\t\t\t\t\t// renderer alive with a bounded diagnostic checker instead.
\t\t\t\t\tif (data == NULL) {
\t\t\t\t\t\tint fallback_pixels = tx->width * tx->height;
\t\t\t\t\t\tdata = malloc(fallback_pixels * 4);
\t\t\t\t\t\tif (data == NULL)
\t\t\t\t\t\t\tSys_Error("Missing texture %s and fallback allocation failed\\n", mt->name);

\t\t\t\t\t\tfor (int p = 0; p < fallback_pixels; ++p) {
\t\t\t\t\t\t\tint x = p % tx->width;
\t\t\t\t\t\t\tint y = p / tx->width;
\t\t\t\t\t\t\tbyte c = (((x >> 3) ^ (y >> 3)) & 1) ? 92 : 36;
\t\t\t\t\t\t\tdata[p * 4 + 0] = c;
\t\t\t\t\t\t\tdata[p * 4 + 1] = 8;
\t\t\t\t\t\t\tdata[p * 4 + 2] = c;
\t\t\t\t\t\t\tdata[p * 4 + 3] = 255;
\t\t\t\t\t\t}
\t\t\t\t\t\tCon_Printf("Xziel: missing texture %s; using safe fallback\\n", mt->name);
\t\t\t\t\t}
'''

if 'textures/nacht_enhanced/%s' not in s:
    if old not in s:
        raise SystemExit("HL external-texture block not found")
    s = s.replace(old, new, 1)

# The SDL renderer historically requested zombie atlases as PCX-only even
# though the generic alias loader supports TGA. Keep TGA support available for
# the Lab's future real zombie-model/skin integration while retaining PCX.
rmisc = Path(sys.argv[1]) / "source" / "platform" / "sdl" / "gl" / "gl_rmisc.c"
rs = rmisc.read_text(encoding="utf-8")
for i in range(4):
    old_skin = f'Image_LoadImage ("models/ai/zfull.mdl_{i}", IMAGE_PCX, 0, true, false)'
    new_skin = f'Image_LoadImage ("models/ai/zfull.mdl_{i}", IMAGE_TGA | IMAGE_PCX, 0, true, false)'
    rs = rs.replace(old_skin, new_skin)
rmisc.write_text(rs, encoding="utf-8")

p.write_text(s, encoding="utf-8")
print("Bound Nacht Enchanted external textures to ndu_enchanted only.")
