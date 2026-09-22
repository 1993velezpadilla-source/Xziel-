# Zombie animation source catalog

Updated: 2026-09-22

This catalog records sources found during the human-performed zombie animation search.

## Status meanings

- **IN_REPO** — raw motion may be redistributed under the source terms and is imported by this repository.
- **EXTERNAL_ONLY** — useful for the game, but raw asset redistribution is not established by the public page/EULA. Acquire through the original provider/account and keep outside the public repository unless the license is verified.
- **BLOCKED_COMMERCIAL** — current terms do not fit a commercial game release.
- **REVIEW** — promising source, but license or provenance is not clear enough to ingest.

## Sources

| Source | Human performance / capture | Useful zombie content | Formats / notes | Status | Source |
|---|---|---|---|---|---|
| CMU Graphics Lab Motion Capture Database | Yes — optical human motion capture | Explicit ZombieWalk, Zombie, zombie march + limp, wounded, creep, slow, clumsy, scared, crawl, get-up, attacks, falls | FBX conversion imported; root motion | **IN_REPO** | http://mocap.cs.cmu.edu / https://huggingface.co/datasets/gbionics/cmu-fbx |
| Quaternius Universal Animation Library 2 | Human-authored animation; do **not** claim optical mocap | Zombie idle, scratch, forward walk + general humanoid actions | CC0 GLB; 43 embedded clips in the Standard GLB | **IN_REPO** | https://quaternius.com/packs/universalanimationlibrary2.html |
| Rokoko — 12 free zombie animations | Yes — Sam Lazarus, Smartsuit Pro II + Smartgloves | 12 zombie / Halloween performances, full-body + fingers | FBX, Mixamo skeleton, 30 FPS; permitted for commercial projects | **EXTERNAL_ONLY** pending raw-redistribution confirmation | https://www.rokoko.com/resources/rokoko-mocap-12-free-zombie-animations |
| Rokoko — 263 free mocap assets | Yes — mocap library | Walk/run, idle, fight and other donor motions useful for zombie variation | Commercial-project use advertised; form/account-gated | **EXTERNAL_ONLY** pending raw-redistribution confirmation | https://www.rokoko.com/free-resources |
| MoCap Central — free 120+ sample pack | Yes — captured performer; cleaned 30 FPS with finger animation | Includes zombie eating off the floor plus many reactions/actions | UE5/Unity-oriented sample library | **EXTERNAL_ONLY**; acquire from provider and retain provider license | https://mocapcentral.com/products/mocap-studio-series-sample-pack-free |
| MoCap Online — free demo pack | Yes — professional mocap provider | Zombie sample(s) plus mobility/action samples | FBX, Blender, Unreal, Unity, BIP, iClone | **EXTERNAL_ONLY**; provider download/EULA | https://mocaponline.itch.io/mocap-online-demo |
| MoCap Online — Zombie packs | Yes — professional actors, optical mocap | Large zombie locomotion/attack/crawl/chase/hit/death/turn libraries | Paid packs; several engine/native formats | **EXTERNAL_ONLY** | https://mocaponline.com/blogs/mocap-news/zombie-animation-pack |
| WondAR Studios — Zombie walk series | Yes — professional actors, Xsens; some clips also Manus gloves | Zombie Walk 1/2/3/5 and related motions | FBX / converted GLB-glTF-USDZ on Fab | **EXTERNAL_ONLY** under marketplace license | https://www.fab.com/listings/b1693d0f-49e5-484b-acf2-f9e4aa3ddb6d |
| WondAR Studios — Zombie eating | Yes — Xsens human mocap | Zombie eating performance | FBX / converted GLB-glTF-USDZ | **EXTERNAL_ONLY** under marketplace license | https://www.fab.com/listings/555c7a3a-bbfa-4cb8-9688-c53c5d6c5e88 |
| Yost Labs 3-Space samples | Yes — inertial human capture | Sample zombie walk + zombie attack BVH | Commercial/redistribution license required by Yost for covered works | **BLOCKED_COMMERCIAL** until a suitable license is obtained | https://yostlabs.com/category/downloads/all-3-space-downloads/ |
| PerMo / PersonaMotion | Yes — 5 professional actors, 41 optical markers; marker C3D + BVH + SMPL-H | Explicit Zombie style across motion contents | Excellent research/reference dataset | **BLOCKED_COMMERCIAL** — repository states non-commercial scientific research terms | https://github.com/AIRC-KETI-VISION/PerMo-dataset |
| BlenderArtists legacy zombie BVH link | Claimed human BVH-based animation | Zombie walk | Old MediaFire link; provenance/license not sufficiently clear | **REVIEW** — do not ingest | https://blenderartists.org/t/free-human-animation-based-bvh-motion-capture/562876 |

## Production rule

The public game repository must never become a mirror for marketplace, account-gated, or research-only motion data.

For runtime variety, prefer multiple independent performances in the same semantic bucket rather than speed-warping one clip:

- walk / shamble / limp / injured / creep / wild-body / old / clumsy / scared
- crawl / ground movement
- idle / twitch / scratch
- reach / swipe / frenzy
- get-up from face-down / side / back
- hit / fall / death candidates
- start-run / chase / stop

Every ingested raw file must retain source, capture ID/performer ID when known, license class, SHA-256, and semantic tags in the catalog.
