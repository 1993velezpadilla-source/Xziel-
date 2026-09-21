#!/usr/bin/env python3
"""Register Android/Vril runtime state for the separate Nacht Enchanted Lab map."""
from pathlib import Path
import sys
if len(sys.argv)!=2: raise SystemExit("usage: patch_vril_nacht_enhanced.py <vril-root>")
p=Path(sys.argv[1])/"source"/"input.c"
s=p.read_text()
anchor='cvar_t xziel_modern_zombies = {"xziel_modern_zombies", "0", true};\n'
decl='cvar_t xziel_nacht_enhanced = {"xziel_nacht_enhanced", "0", true};\n'
if decl not in s:
    if anchor not in s: raise SystemExit("modern zombie cvar anchor missing")
    s=s.replace(anchor,anchor+decl,1)
anchor='\tCvar_RegisterVariable(&xziel_modern_zombies);\n'
reg='\tCvar_RegisterVariable(&xziel_nacht_enhanced);\n'
if reg not in s:
    if anchor not in s: raise SystemExit("modern zombie registration anchor missing")
    s=s.replace(anchor,anchor+reg,1)
p.write_text(s)
print("Registered xziel_nacht_enhanced runtime cvar (off by default; ndu_enchanted enables it).")
