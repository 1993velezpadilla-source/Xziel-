# Xziel Horror Lighting Architecture v1

Status: runtime implementation active on `engine/horror-lighting-v1`.

## Goal

Make darkness, practical lights, fog, exposure and material response part of
gameplay presentation rather than a decorative post effect. Xziel must retain
readable combat and stable mobile frame time while creating deliberate
negative space, silhouettes, uncertain depth and controlled contrast.

This is a clean-room implementation. Public talks, documentation and
open-source projects are used as behavior/architecture references only. No
proprietary game code, shaders, assets or leaked data are copied.

## Public references distilled

### Dead Space Remake

EA/Motive public GDC material describes a lighting-fixture workflow,
systematic light behavior, an intensity director, color grading and ACES
integration. Public EA art material also emphasizes real-time fixtures,
volumetric fog and atmospheric/VFX interaction.

Xziel lesson:
- lights are authored fixtures with gameplay meaning;
- global intensity/mood is a director output, not random per-light mutation;
- exposure and grade belong to the scene-lighting system;
- fog must participate in silhouettes and depth separation.

References:
- https://www.gdcvault.com/play/1029228/Harnessing-the-Power-of-Light
- https://www.ea.com/games/dead-space/dead-space/news/art-deep-dive-environments

### Alien: Isolation

Public postmortem/technical discussion around Alien: Isolation repeatedly
highlights a deferred-lighting-heavy environment and strong use of volumetric
lighting/atmosphere.

Xziel lesson:
- horror depends on many motivated practical sources, not one global sun;
- particles/fog should respond to scene light where budget allows;
- local-light count must be bounded aggressively on mobile instead of copying
  a desktop/console deferred-lighting budget.

### Silent Hill 2 Remake

Bloober/PlayStation public material highlights fully dynamic lighting/GI as a
major contributor to atmosphere.

Xziel lesson:
- indirect fill and believable response matter, but Xziel should achieve this
  with baked/probe/IBL support plus bounded dynamic lights rather than trying
  to reproduce a heavyweight desktop GI system on Android.

Reference:
- https://blog.playstation.com/2024/05/30/how-silent-hill-2-remake-is-revitalizing-the-classic-with-unreal-engine-5/

### Frictional / Amnesia HPL2

Frictional publicly released the Amnesia engine/game source under GPL.

Xziel lesson:
- it is useful for studying public behavior and tool concepts;
- GPL code is not copied into Xziel's engine implementation.

Reference:
- https://github.com/FrictionalGames/AmnesiaTheDarkDescent

### Google Filament

Filament is the primary mobile PBR reference for physically meaningful light,
pre-exposure/exposure, material response, color grading, fog and mobile
renderer budgeting.

References:
- https://google.github.io/filament/main/filament.html
- https://google.github.io/filament/Filament.html

## Runtime pipeline

```
HorrorStimulus
      |
      v
HorrorDirector
  tension / adrenaline
      |
      +-----------------------+
      |                       |
      v                       v
EnvironmentSystem      HorrorLightingDirector
 rain / wetness /      key / ambient / fog
 lightning             exposure / grade
                              |
                      rank local practicals
                      deterministic flicker
                      quality light budget
                              |
                              v
                    StaticMeshEnvironmentState
                              |
                              v
                    per-frame Vulkan UBO
                              |
             +----------------+----------------+
             |                                 |
             v                                 v
       legacy scan path                  PBR material path
 captured-light texture            GGX / Smith / Fresnel
             |                  normal / ORM / emissive
             +----------------+----------------+
                              |
                              v
                     atmosphere / fog
                              |
                              v
                    exposure + filmic curve
                    saturation + contrast
                              |
                              v
                           frame
```

## v1 mobile budget

The engine owns up to eight ranked runtime lights so higher-end backends can
grow without changing gameplay contracts. The current Android forward shader
consumes at most four local lights per fragment.

Policy target:
- Low: two important local lights.
- Medium: up to four.
- High/Ultra: current forward path still caps at four; future Forward+/clustered
  path may consume more without changing the authored map contract.
- One scene key/directional light is separate from the local budget.
- Shadow casting is planned/budgeted independently through ShadowPlanner.
- Volumetric flags are author intent. v1 uses them for ranking; full froxel
  scattering is a later render pass.

## Sanctum mood contract

The initial Sanctum rig deliberately avoids uniform illumination.

- warm amber practical/key light creates readable focal anchors;
- blue-black ambient fill keeps shadow detail from collapsing completely;
- cold doorway/moon spill produces silhouette separation;
- a restrained red emergency practical provides threat color without painting
  the entire scene red;
- exposure starts below neutral and drops slightly as tension rises;
- saturation is restrained as tension rises;
- fog density grows with tension;
- lightning raises key energy so silhouettes emerge through haze;
- flicker is deterministic and clamped to 3 Hz to avoid uncontrolled strobing.

The goal is readable fear: the player should understand threats and navigation
while large parts of the image remain uncertain.

## Material path

PBR materials use:
- sRGB base color;
- tangent-space normal;
- ORM (occlusion / roughness / metallic);
- emissive;
- GGX normal distribution;
- Smith visibility;
- Schlick Fresnel.

Legacy photogrammetry remains an unlit/captured-light path. It still receives
atmosphere, exposure and grade so legacy scans live in the same world without
being relit incorrectly.

## Lighting units

v1 stores normalized linear RGB plus engine-relative intensity because legacy
content has not yet been authored in physical units. The long-term contract is
to migrate authored lights toward:
- lumens for point/spot practicals;
- lux for directional/large-area illumination;
- nits for emissive surfaces;
while preserving a compatibility normalization layer.

## Next phases

### v1.1 — authored map lights
Extend XMAP with explicit point/spot light records, fixture IDs, shadow intent,
volumetric intent, flicker profile and importance. Remove the temporary
arena-derived Sanctum rig once the map asset owns its fixtures.

### v1.2 — shadows
Connect selected lights to ShadowPlanner:
- one high-priority dynamic shadow source on low/medium;
- bounded additional sources on high/ultra;
- distance/resolution/update-rate adaptation;
- cached/static shadows for architecture where practical.

### v1.3 — true HDR composite
Move the scene resolve target from swapchain format to a supported HDR
intermediate (prefer R16G16B16A16_SFLOAT when viable), then move exposure,
filmic tone mapping, bloom and final color grade to the scene composite pass.
HUD remains native-resolution after tone mapping.

### v1.4 — IBL / reflection probes
Add irradiance/specular probes for stable indirect fill. Dynamic/local lights
remain for motivated practicals and gameplay events.

### v1.5 — volumetric fog
Add depth-aware froxel or low-resolution volume integration on capable tiers.
Only important lights inject scattering. Lower tiers retain analytic distance
fog and authored fog volumes.

### v1.6 — Forward+ light lists
When scenes need more than four local sources, build tile/cluster light lists
on GPU/CPU according to device tier. Keep the current fixed forward path as the
low-cost fallback.

## Acceptance gates

A lighting feature is not complete because a screenshot looks good.

Every release candidate must prove:
- no shader/descriptor validation errors;
- stable Vulkan pipeline creation;
- no per-frame allocation in the static world hot path;
- bounded local light count;
- deterministic flicker for deterministic tests;
- no rapid unbounded flashing;
- GPU pass timing remains inside tier budget;
- lighting stays legible at combat exposure;
- visual comparison uses the same camera/content/quality tier;
- 15/30-minute Android thermal soak before calling the tier shippable.

The creative target is fear through contrast, silhouettes, motivated light and
depth uncertainty. The engineering target is a bounded, measurable system that
can survive a full zombie horde on mobile.
