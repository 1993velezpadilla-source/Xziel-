# Official NZ:P Map Quest-Pattern Mining

Pinned map source: `nzp-team/assets@c8135a66e00bb64577912fbf792f8fef7f47658e`

This report mines the already-extracted 20 official source maps for **quest-like entity patterns**. It is not a statement that each map has a narrative main quest; it identifies reusable interaction graphs, secret chains and state transitions.

| Map | High-signal entities | High-signal graph edges | Notable primitives |
|---|---:|---:|---|
| `nzp_xmas2` | 119 | 438 | trigger_multiple×56, trigger_interact×25, game_counter×12, func_button×11, game_songplay×7, game_screenflash×4, power_switch×2, trigger_once×1 |
| `wahnsinn` | 41 | 125 | item_switch×12, teddy_spawn×8, zapper_node×8, trigger_electro×7, zapper_light×2, power_switch×1, item_radio×1, trigger_once×1 |
| `fegefeuer` | 38 | 34 | zapper_node×30, teddy_spawn×2, func_teleporter_pad×2, func_door_nzp×1, func_teleporter_entrance×1, power_switch×1, zapper_light×1 |
| `weapon_test` | 32 | 31 | buy_weapon×31, power_switch×1 |
| `nzp_warehouse2` | 28 | 21 | zapper_node×12, teddy_spawn×3, zapper_light×3, item_radio×3, func_teleporter_entrance×1, power_switch×1, game_counter×1, game_songplay×1 |
| `ndu` | 24 | 22 | explosive_barrel×21, item_radio×1, game_counter×1, game_songplay×1 |
| `bunker-defense` | 23 | 25 | zapper_node×12, teddy_spawn×3, trigger_once×3, zapper_light×2, game_counter×1, game_songplay×1, func_ending×1 |
| `hangar` | 14 | 19 | teddy_spawn×5, game_counter×4, trigger_interact×3, power_switch×1, game_songplay×1 |
| `nzp_warehouse` | 13 | 11 | zapper_node×6, teddy_spawn×3, power_switch×1, game_counter×1, game_songplay×1, zapper_light×1 |
| `lexi_house` | 7 | 16 | teddy_spawn×3, trigger_relay×2, game_counter×1, game_songplay×1 |
| `lexi_overlook` | 7 | 0 | trigger_awardpoints×4, item_radio×3 |
| `lexi_temple` | 5 | 8 | teddy_spawn×3, game_counter×2 |
| `4all` | 6 | 0 | teddy_spawn×3, power_switch×1, item_radio×1, func_ending×1 |
| `boxxer` | 3 | 8 | teddy_spawn×1, power_switch×1, func_button×1 |
| `christmas_special` | 2 | 0 | power_switch×1, item_radio×1 |
| `b1oodv3` | 1 | 0 | power_switch×1 |
| `b1oodv4` | 1 | 0 | power_switch×1 |
| `dung3on` | 1 | 0 | power_switch×1 |
| `loop` | 1 | 0 | power_switch×1 |
| `template` | 0 | 0 | — |

## Notable concrete chains

### nzp_xmas2

- entity 154 @ source line 12520: `power_switch` — target="fake_power_activate"
- entity 326 @ source line 13988: `power_switch` — target="q_gramo_dis_start"; target2="p_turn_lights_on"; killtarget="q_gramo_normal_kill"
- entity 471 @ source line 15411: `game_songplay` — targetname="sting_power"; cost="45"
- entity 483 @ source line 15533: `game_counter` — targetname="upstairsdoor"; target="r1z"; health="3"; frags="0"; spawnflags="1"
- entity 485 @ source line 15558: `game_counter` — targetname="slidedoor"; target="slide"; health="3"; frags="0"; spawnflags="1"
- entity 520 @ source line 16939: `func_button` — target="q_bell_increment"; target2="q_bell_2"; health="1"
- entity 524 @ source line 17000: `func_button` — target="q_bell_increment"; target2="q_bell_5"; health="1"
- entity 526 @ source line 17036: `func_button` — target="q_bell_increment"; target2="q_bell_4"; health="1"
- entity 533 @ source line 17139: `func_button` — target="q_bell_increment"; target2="q_bell_7"; health="1"
- entity 534 @ source line 17158: `func_button` — target="q_bell_increment"; target2="q_bell_6"; health="1"
- entity 540 @ source line 17244: `func_button` — target="q_bell_increment"; target2="q_bell_1"; health="1"
- entity 547 @ source line 17349: `trigger_interact` — target="radio_power"; noise="sounds/misc/radio"
- entity 550 @ source line 17393: `func_button` — target="q_bell_increment"; target2="q_bell_3"; health="1"
- entity 561 @ source line 17701: `trigger_interact` — targetname="q_boiler_door_interact"; target="q_boiler_door"; spawnflags="1"; noise="sounds/misc/debris.wav"
- entity 568 @ source line 17908: `trigger_interact` — target="q_wep_frame"; target2="q_wep_frame_collect"; noise="sounds/player/pickup.wav"
- entity 569 @ source line 17927: `func_button` — target="q_body_frozen"; target2="q_body_thawed"; target3="q_body_snow"; target4="q_wep_energy_collect"; health="300"; spawnflags="1"
- entity 570 @ source line 17950: `trigger_interact` — targetname="q_token_glasses_interact"; target="q_token_glasses"; target2="q_token_glasses_wait"; target3="q_fire_g_interact"; spawnflags="1"; noise="sounds/player/pickup.wav"
- entity 576 @ source line 18137: `trigger_interact` — targetname="q_token_toy_interact"; target="q_token_toy"; target2="q_token_toy_wait"; target3="q_fire_t_interact"; spawnflags="1"; noise="sounds/player/pickup.wav"
- entity 579 @ source line 18216: `trigger_interact` — targetname="q_fire_t_interact"; target="q_fire_t"; target2="q_fire_counter"; spawnflags="1"; noise="sounds/player/pickup.wav"
- entity 580 @ source line 18237: `trigger_interact` — targetname="q_fire_s_interact"; target="q_fire_s"; target2="q_fire_counter"; spawnflags="1"; noise="sounds/player/pickup.wav"
- entity 582 @ source line 18278: `trigger_interact` — targetname="q_wep_energy_collect"; target="q_wep_energy"; target2="q_wep_cart_box_opened"; target3="q_wep_cart"; target4="q_wep_cart_interact"; killtarget="q_wep_cart_box_closed"; spawnflags="1"; noise="sounds/player/pickup.wav"
- entity 583 @ source line 18302: `trigger_interact` — targetname="q_fire_g_interact"; target="q_fire_g"; target2="q_fire_counter"; spawnflags="1"; noise="sounds/player/pickup.wav"
- entity 588 @ source line 18462: `trigger_interact` — targetname="q_token_scarf_interact"; target="q_token_scarf"; target2="q_token_scarf_wait"; target3="q_fire_s_interact"; spawnflags="1"; noise="sounds/player/pickup.wav"
- entity 594 @ source line 18615: `trigger_interact` — targetname="q_wep_cart_interact"; target="q_wep_cart"; target2="q_wep_cart_collect"; target3="q_wep_assembly_interact"; spawnflags="1"; noise="sounds/player/pickup.wav"
- entity 597 @ source line 18684: `trigger_interact` — target="sq_snowman_chime"; target2="sq_snowman_counter"; killtarget="sq_snowman_snow_1"
- entity 601 @ source line 18761: `trigger_interact` — targetname="q_wep_assembly_interact"; target="q_wep_assembly"; target2="q_wep_assembly_spr"; target3="q_wep_assembly_flash"; target4="q_wep_obtain_delay"; spawnflags="1"
- entity 603 @ source line 18804: `trigger_interact` — targetname="q_spirit_interact"; target="q_sky_change_wait"; target2="q_sky_change_flash"; target3="q_spirit"; target4="q_spirit_final"; spawnflags="1"
- entity 608 @ source line 18910: `trigger_interact` — targetname="q_key_interact"; target="q_boiler_door_interact"; killtarget="q_drawer_key"; spawnflags="1"; noise="sounds/misc/xmas/key.wav"
- entity 609 @ source line 18931: `func_button` — target="sq_free_insta"; target2="sq_free_insta_model"; health="1"
- entity 612 @ source line 19030: `func_button` — target="sq_free_points"; target2="sq_free_points_model"; health="1"

### wahnsinn

- entity 29 @ source line 6089: `power_switch`
- entity 85 @ source line 6555: `teddy_spawn` — target="mbd"
- entity 86 @ source line 6561: `item_radio`
- entity 87 @ source line 6566: `teddy_spawn` — target="mbd"
- entity 88 @ source line 6572: `teddy_spawn` — target="mbd"
- entity 153 @ source line 7002: `teddy_spawn` — target="mbd"
- entity 271 @ source line 8459: `teddy_spawn` — target="mbd"
- entity 273 @ source line 8471: `teddy_spawn` — target="mbd"
- entity 274 @ source line 8477: `teddy_spawn` — target="mbd"
- entity 284 @ source line 8573: `teddy_spawn` — target="mbd"

### fegefeuer

- entity 7 @ source line 1121: `func_door_nzp` — target="zBox"; cost="1000"
- entity 53 @ source line 1905: `teddy_spawn`
- entity 54 @ source line 1910: `func_teleporter_entrance` — target="t7"; target2="j1"; cost="0"
- entity 125 @ source line 2993: `power_switch`
- entity 239 @ source line 5202: `teddy_spawn`

### weapon_test

- entity 91 @ source line 2088: `power_switch`

### nzp_warehouse2

- entity 1 @ source line 3375: `func_teleporter_entrance` — target="pad"; target2="pad"
- entity 3 @ source line 3394: `power_switch`
- entity 252 @ source line 7780: `teddy_spawn` — target="song_counter"; noise="sounds/pu/pickup.wav"
- entity 253 @ source line 7788: `teddy_spawn` — target="song_counter"; noise="sounds/pu/pickup.wav"
- entity 254 @ source line 7796: `teddy_spawn` — target="song_counter"; noise="sounds/pu/pickup.wav"
- entity 255 @ source line 7804: `game_counter` — targetname="song_counter"; target="song_play"; health="3"
- entity 256 @ source line 7812: `game_songplay` — targetname="song_play"; cost="304"
- entity 360 @ source line 9005: `trigger_interact` — target="comms_wait"; killtarget="secret"; noise="sounds/player/land.wav"
- entity 362 @ source line 9044: `item_radio` — spawnflags="1"
- entity 363 @ source line 9052: `item_radio` — spawnflags="1"
- entity 364 @ source line 9060: `item_radio` — spawnflags="1"

### ndu

- entity 56 @ source line 2888: `item_radio`
- entity 117 @ source line 3572: `explosive_barrel` — target="song_counter"
- entity 118 @ source line 3581: `explosive_barrel` — target="song_counter"
- entity 119 @ source line 3590: `explosive_barrel` — target="song_counter"
- entity 120 @ source line 3599: `explosive_barrel` — target="song_counter"
- entity 121 @ source line 3608: `explosive_barrel` — target="song_counter"
- entity 122 @ source line 3617: `explosive_barrel` — target="song_counter"
- entity 123 @ source line 3626: `explosive_barrel` — target="song_counter"
- entity 124 @ source line 3635: `explosive_barrel` — target="song_counter"
- entity 125 @ source line 3645: `explosive_barrel` — target="song_counter"
- entity 126 @ source line 3654: `explosive_barrel` — target="song_counter"
- entity 127 @ source line 3663: `explosive_barrel` — target="song_counter"
- entity 128 @ source line 3672: `explosive_barrel` — target="song_counter"
- entity 129 @ source line 3681: `explosive_barrel` — target="song_counter"
- entity 130 @ source line 3690: `explosive_barrel` — target="song_counter"
- entity 131 @ source line 3699: `explosive_barrel` — target="song_counter"
- entity 132 @ source line 3708: `explosive_barrel` — target="song_counter"
- entity 133 @ source line 3717: `explosive_barrel` — target="song_counter"
- entity 134 @ source line 3726: `explosive_barrel` — target="song_counter"
- entity 135 @ source line 3735: `explosive_barrel` — target="song_counter"
- entity 181 @ source line 4174: `explosive_barrel` — target="song_counter"
- entity 245 @ source line 5965: `explosive_barrel` — target="song_counter"
- entity 378 @ source line 8726: `game_counter` — targetname="song_counter"; target="song_target"; health="21"; spawnflags="1"
- entity 379 @ source line 8735: `game_songplay` — targetname="song_target"; cost="338"

### bunker-defense

- entity 36 @ source line 2396: `teddy_spawn` — target="Jug"; spawnflags="1"; message="Oh No! Mein Power!"
- entity 38 @ source line 2421: `teddy_spawn` — target="PaP"; spawnflags="1"; message="Don't Dig Straight Down..."
- entity 97 @ source line 3898: `teddy_spawn` — target="Counter"; message="Listen to this track i found while digging UwU"
- entity 134 @ source line 4790: `game_counter` — targetname="Counter"; target="Song"; health="1"; spawnflags="1"
- entity 135 @ source line 4800: `game_songplay` — targetname="Song"; cost="337"
- entity 144 @ source line 4903: `trigger_once` — target="PaPZombie"
- entity 306 @ source line 7369: `func_ending` — cost="25000"

### hangar

- entity 36 @ source line 4043: `power_switch`
- entity 221 @ source line 6953: `teddy_spawn` — target="mus_egg"; noise="sounds/misc/buy.wav"
- entity 222 @ source line 6961: `teddy_spawn` — target="mus_egg"; noise="sounds/misc/buy.wav"
- entity 223 @ source line 6969: `game_counter` — targetname="mus_egg"; target="mus_play"; health="5"; spawnflags="1"; message="You Have Found Us All!"
- entity 224 @ source line 6980: `game_songplay` — targetname="mus_play"; cost="147"
- entity 231 @ source line 7676: `teddy_spawn` — target="mus_egg"; noise="sounds/misc/buy.wav"
- entity 243 @ source line 7794: `teddy_spawn` — target="mus_egg"; noise="sounds/misc/buy.wav"
- entity 292 @ source line 8383: `trigger_interact` — target="FlopDoor"; killtarget="bot3"; noise="sounds/misc/ching.wav"
- entity 293 @ source line 8399: `game_counter` — targetname="FlopDoor"; killtarget="Floppa"; health="3"; spawnflags="1"; message="3/3"
- entity 294 @ source line 8409: `trigger_interact` — target="FlopDoor"; killtarget="bot1"; noise="sounds/misc/ching.wav"
- entity 297 @ source line 8443: `teddy_spawn` — target="mus_egg"; noise="sounds/misc/buy.wav"
- entity 300 @ source line 8479: `trigger_interact` — target="FlopDoor"; killtarget="bot2"; noise="sounds/misc/ching.wav"
- entity 305 @ source line 8560: `game_counter` — targetname="FlopDoor"; health="2"; spawnflags="1"; message="2/3"
- entity 306 @ source line 8569: `game_counter` — targetname="FlopDoor"; health="1"; spawnflags="1"; message="1/3"

### nzp_warehouse

- entity 2 @ source line 1977: `power_switch`
- entity 154 @ source line 4452: `teddy_spawn` — target="song_counter"; noise="sounds/pu/pickup.wav"
- entity 155 @ source line 4460: `teddy_spawn` — target="song_counter"; noise="sounds/pu/pickup.wav"
- entity 156 @ source line 4468: `game_counter` — targetname="song_counter"; target="song_play"; killtarget="pap_door"; health="3"
- entity 157 @ source line 4477: `game_songplay` — targetname="song_play"; cost="94"
- entity 186 @ source line 4785: `teddy_spawn` — target="song_counter"; noise="sounds/pu/pickup.wav"

### lexi_house

- entity 167 @ source line 7038: `teddy_spawn` — target="mus_egg"; message="What did we do to deserve this?"; noise="sounds/misc/ching.wav"
- entity 168 @ source line 7047: `teddy_spawn` — target="mus_egg"; message="They should have never returned."; noise="sounds/misc/ching.wav"
- entity 169 @ source line 7056: `teddy_spawn` — target="mus_egg"; message="There's something in the water..."; noise="sounds/misc/ching.wav"
- entity 170 @ source line 7065: `game_counter` — targetname="mus_egg"; target="mus_play"; health="3"; spawnflags="1"
- entity 171 @ source line 7074: `game_songplay` — targetname="mus_play"; cost="305"

### lexi_overlook

- entity 169 @ source line 6167: `item_radio` — spawnflags="1"
- entity 170 @ source line 6176: `item_radio` — spawnflags="1"
- entity 172 @ source line 6192: `item_radio` — spawnflags="1"

### lexi_temple

- entity 113 @ source line 5238: `teddy_spawn` — target="PaP_Door"; message="Oh?"; noise="sounds/misc/ching.wav"
- entity 114 @ source line 5247: `teddy_spawn` — target="PaP_Door"; message="Can you find all three of us?"; noise="sounds/misc/ching.wav"
- entity 125 @ source line 5336: `game_counter` — targetname="PaP_Door"; killtarget="PaP_Wall"; health="3"; spawnflags="1"; message="You found all of us! Come reap your reward!"
- entity 126 @ source line 5346: `game_counter` — targetname="PaP_Door"; killtarget="PaP_Wall"; health="3"; spawnflags="1"; message="Pack-a-Punch is now open!"
- entity 203 @ source line 7379: `teddy_spawn` — target="PaP_Door"; message="You found me!"; noise="sounds/misc/ching.wav"

### 4all

- entity 9 @ source line 3444: `power_switch`
- entity 56 @ source line 4127: `teddy_spawn` — target="1"; spawnflags="1"; noise="sounds/misc/buy.wav"
- entity 62 @ source line 4320: `teddy_spawn` — target="2"; spawnflags="1"; noise="sounds/misc/buy.wav"
- entity 77 @ source line 4723: `teddy_spawn` — target="3"; spawnflags="1"; noise="sounds/music/tune1.wav"
- entity 81 @ source line 4787: `item_radio`
- entity 83 @ source line 4810: `func_ending` — cost="32000"

### boxxer

- entity 29 @ source line 1677: `teddy_spawn` — target="teddyremovetarget"; spawnflags="1"
- entity 49 @ source line 1932: `power_switch`
- entity 50 @ source line 1941: `func_button` — target="teddyremovetarget"; health="1"; spawnflags="0"

### christmas_special

- entity 1 @ source line 6083: `power_switch`
- entity 48 @ source line 6475: `item_radio`

### b1oodv3

- entity 96 @ source line 2601: `power_switch`

### b1oodv4

- entity 34 @ source line 1772: `power_switch`

### dung3on

- entity 35 @ source line 3393: `power_switch`

### loop

- entity 16 @ source line 951: `power_switch`

## Patterns proven by the official source maps

- **Shootable secret -> counter -> song/reward.** Official maps use `teddy_spawn` and/or other shootable secret entities as counter inputs, then fire a song or world-state target.
- **Multi-target traversal updates.** Doors commonly target multiple spawn groups/areas, coupling player traversal to zombie availability.
- **Power as shared world-state gate.** The map source combines per-map power switches with power-gated systems rather than making every consumer independently solve power.
- **Secret removal/reveal through killtarget.** Map entities remove blocker/clip/door targets as a state-transition action.
- **Trap networks as graph pairs.** Zapper nodes/lights/electro triggers form reusable activation networks rather than isolated effects.
- **Interact/counter loops.** Maps using `trigger_interact` can feed resettable counters, creating repeatable N-of-M or sequence-style secret logic.

## Important interpretation rule

A target name such as `pap`, `song`, `secret` or `counter` is useful mapper evidence, but names are not behavior by themselves. Behavior is only classified when the source entity class plus target graph supports the interpretation.
