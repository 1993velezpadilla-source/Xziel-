# BO3 Nacht — recovered public asset evidence

## Mindmirror Zombies Chronicles environment pack

Archived source:
- Modme thread: `[Zombies Chronicles] All Nacht Der Untoten models`
- Author: Mindmirror
- Original public MEGA release is still downloadable.

Verified archive:
- filename: `Nacht Der Untoten Models.zip`
- bytes: 261354169
- SHA-256: `1b09b42b015f6520dfe966e026832ae2b44500fe40fa98b0039cd7e9e8ba3f58`
- entries: 583
- 33 GDT
- 33 XMODEL_BIN
- 33 XMODEL_EXPORT
- 417 TIFF images

The release states these are the 33 models used on the Zombies Chronicles Nacht remake, with duplicate textures/materials removed and normal/gloss values corrected. The thread explicitly says zombie models are not included in this pack.

### Exact 33 model directories

1. p7_zm_nac_antenna_radar_tower
2. p7_zm_nac_barrel_explosive_red
3. p7_zm_nac_barrel_explosive_red_dest
4. p7_zm_nac_barrel_explosive_red_dmg_01
5. p7_zm_nac_barrel_explosive_red_dmg_02
6. p7_zm_nac_box_wood_sml
7. p7_zm_nac_cabinet_wood_vintage
8. p7_zm_nac_cabinet_wood_vintage_door_lt
9. p7_zm_nac_cabinet_wood_vintage_door_rt
10. p7_zm_nac_cagelight
11. p7_zm_nac_chair_metal_dining
12. p7_zm_nac_concrete_pillar_block_03
13. p7_zm_nac_couch_victorian_beige
14. p7_zm_nac_crate_wood_02_iron_cross_long_lid
15. p7_zm_nac_door_help
16. p7_zm_nac_foliage_palm_pacific_snapped_01
17. p7_zm_nac_jerrycan_fuel_red
18. p7_zm_nac_light_flood_stand
19. p7_zm_nac_sapling_pacific_dmg_01
20. p7_zm_nac_sapling_pacific_dmg_02
21. p7_zm_nac_spool_wire_electric
22. p7_zm_nac_trailer_generator
23. p7_zm_nac_trailer_generator_grp
24. p7_zm_nac_trailer_wheel
25. p7_zm_nac_truck_opel_blitz
26. p7_zm_nac_wall_custom_tear_in_chunk_01
27. p7_zm_nac_wall_custom_tear_in_chunk_02
28. p7_zm_nac_wall_custom_tear_in_chunk_03
29. p7_zm_nac_wall_custom_tear_in_chunk_04
30. p7_zm_nac_wall_custom_tear_in_chunk_05
31. p7_zm_nac_wall_custom_tear_in_chunk_06
32. p7_zm_nac_wall_custom_tear_in_wall_01
33. p7_zm_nac_wire_ends

## Pavlov BO3 Nacht port

Steam Workshop item `2755515831` was successfully downloaded and indexed.

Payload:
- WindowsNoEditor.pak: 2543506907 bytes
- LinuxServer.pak: 127212802 bytes
- total Workshop payload: 2670719720 bytes

Windows PAK index:
- 3871 entries
- 3870 UASSET
- 1 UMAP

Map:
- `Pavlov/Content/CustomMaps/UGC2755515831/Nacht_de_Untoten.umap`
- extracted size: 14892083 bytes

The author publicly credits Treyarch BO1/BO3 map geometry and models and later clarified that this map's geometry is from BO3.

The PAK contains `CoD_nacht/MAP_FILES` with `zm_prototype_part*` assets and BO3-style material names, plus hundreds of map-specific meshes/materials/textures.

Current next step:
- parse the UE4.21 UMAP to recover mesh references and world transforms;
- cross-check those references against the Mindmirror BO3 model pack and `p7_zm_nac_*` / `p7_zm_gen_proto_*` asset families.
