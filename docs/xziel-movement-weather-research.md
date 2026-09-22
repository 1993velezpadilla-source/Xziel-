# Xziel Engine — movement, touch compression, lighting and weather research

Date: 2026-09-20

## Goal

Support a broad modern-FPS movement vocabulary without turning the phone into a
wall of virtual buttons. Advanced mobility is an engine capability, not a
requirement for every Zombies ruleset or every legacy map.

## Movement research

### Call of Duty: Modern Warfare III

Activision's movement guide documents the modern shared crouch/slide/dive
interaction:

- sprint + crouch -> slide
- sprint + hold crouch -> dive
- slide can be cancelled

Source:
https://www.callofduty.com/guides/training/call-of-duty-modern-warfare-III-play-guides-multiplayer-movement

MWIII patch notes also document user-selectable "Slide/Dive Behavior", including
tap-to-slide and tap-to-dive modes:
https://www.callofduty.com/patchnotes/2023/11/call-of-duty--modern-warfare-iii-launch-patch-notes

This is a strong model for Xziel Mobile: one stance control can represent crouch,
slide and dolphin dive contextually.

### Call of Duty: Black Ops III

Activision described BO3's system as chain-based movement with unlimited sprint,
thrust jump, power slide, wall running, swimming and fast mantling, while
maintaining weapon control during traversal.

Sources:
https://blog.activision.com/tw/zh/call-of-duty/archives/getting-started-with-the-call-of-duty-black-ops-3-multiplayer-beta
https://blog.activision.com/call-of-duty/archives/10-ways-black-ops-3-will-change-the-way-you-play-call-of-duty

The lesson is not to copy BO3 values. The useful architectural idea is that
moves should chain through a state machine instead of existing as disconnected
special cases.

### Halo Infinite

Halo exposes Crouch/Slide as one action and supports Maintain Sprint and Auto
Clamber options. That reinforces the idea that some traversal can be inferred
from context rather than demanding dedicated inputs.

Source:
https://support.halowaypoint.com/hc/en-us/articles/4407649252116-Guide-to-Halo-Infinite-Game-Settings

### Apex/Titanfall family

Apex's official bindings likewise keep crouch as a single action, while the
Titanfall movement vocabulary popularized chaining wall movement and additional
air control. Xziel supports wall-run/wall-jump/double-jump as optional capability
flags rather than forcing them into classic Zombies.

Apex controls:
https://help.ea.com/en/articles/apex-legends/pc-and-controller-settings/

### COD Mobile / Warzone Mobile input principles

Activision documents COD Mobile options for joystick sprint, fixed joystick,
fixed fire and gyro. Warzone Mobile exposes hold/toggle ADS, gyroscope options,
per-zoom sensitivity and extensive control customization.

Sources:
https://blog.activision.com/call-of-duty/2019-10/Getting-a-Grip-on-the-Call-of-Duty-Mobile-Controls
https://www.callofduty.com/blog/2024/03/call-of-duty-warzone-mobile-complete-control-plus-customization-controller-options

## Xziel mobile movement layout

The engine target is only two dedicated movement action buttons in addition to
the left stick:

### 1. Jump / Mantle

- tap on ground -> jump
- tap in air -> double jump when the current ruleset enables it
- hold near an authored ledge -> mantle
- tap during wall-run -> wall jump

### 2. Stance

- tap while walking/stationary -> crouch
- tap while sprinting -> slide
- hold while sprinting -> dolphin dive
- optional second tap / Jump while sliding -> slide cancel

### Automatic/contextual behavior

- pushing the left stick into the outer sprint ring -> sprint
- optional outermost ring -> tactical sprint
- wall-run begins automatically only when:
  - ruleset enables it
  - traversal probe marks the surface runnable
  - player is airborne and moving into a valid wall
- mantle can be assisted without a separate mantle button

This allows a complex movement system without adding buttons for Sprint, Slide,
Dive, Prone, Wall Run, Wall Jump, Double Jump and Mantle separately.

## Ruleset presets

### Classic Zombies

Enabled:
- walk
- sprint
- crouch
- jump
- optional mantle

Disabled by default:
- tactical sprint
- dolphin dive
- slide
- double jump
- wall run
- wall jump

### Modern Zombies

Enabled:
- sprint / tactical sprint
- crouch
- slide
- dolphin dive
- slide cancel
- jump
- mantle

Advanced wall movement remains map opt-in.

### Arcade / Parkour

Adds:
- double jump
- wall run
- wall jump
- aggressive air control

The engine supports all profiles while a map or mode chooses the appropriate
subset. That keeps Nacht recognizable while allowing future maps to go wild.

## First-person animation contract

Movement does not hard-code animation assets. It emits semantic cues:

- Jump
- DoubleJump
- SlideStart
- DiveStart
- WallRunStart
- WallJump
- MantleStart
- Land

The future animation graph consumes these cues for:

- hands/weapon slide pose
- dolphin-dive camera/body pitch
- viewmodel lowering during sprint/mantle
- wall-run camera roll
- landing recoil/spring
- firing permissions per state

This is important for the first-person "I can actually see that I am sliding or
diving" requirement.

## Android touch architecture

GameActivity exposes motion events to native C/C++ through input buffers and can
carry multiple pointers. Xziel will consume every event into a timestamped input
layer, then resolve gestures before the fixed simulation tick.

References:
https://developer.android.com/games/agdk/game-activity/get-started
https://developer.android.com/games/agdk/add-touch-support

## Lighting and weather

### PBR material basis

glTF 2.0 uses metallic-roughness PBR materials with base color, metallic,
roughness, normal, occlusion and emissive properties. That gives Xziel a clean
standard for modern materials instead of inheriting Quake-era surface lighting.

References:
https://www.khronos.org/gltf/pbr
https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html

### Light types

The renderer contract supports:

- directional sun/moon lights
- point lights
- spot lights
- shadow-casting flag
- volumetric participation
- emissive material bloom hints

The mobile renderer should favor baked/static lighting for map geometry and
spend dynamic shadow budget on high-value moving lights and actors. Android's
mobile lighting guidance makes the same fundamental performance distinction:
precomputed lighting has no runtime light calculation cost, while real-time
lights and shadows are expensive.

Reference:
https://developer.android.com/games/optimize/lighting-for-mobile-games-with-unity

### Rain stack

Rain is designed as several layers rather than "just particles":

1. camera-local streak particles affected by wind
2. precipitation occlusion so rain does not fall through roofs
3. contact splash particles near visible surfaces
4. accumulated global/per-material wetness
5. wet materials reduce apparent roughness and strengthen reflections
6. optional puddle masks / ripples in later renderer stages
7. fog/mist coupling for storms
8. lightning flash feeding scene exposure and dynamic lights
9. thunder audio scheduled from storm events

The current engine foundation implements deterministic rain intensity, scalable
particle budgets, wetness accumulation/drying, wind, fog and lightning flash
state. The Vulkan renderer will consume these values later.

## Performance philosophy

Rain, lights and shadows are quality-tiered instead of all-or-nothing:

- Low: small rain budget, cheap splashes, baked/static lighting bias
- Medium: larger particles and selective dynamic shadows
- High: precipitation occlusion, wet-surface response, more splashes
- Ultra: larger budgets and optional higher-cost volumetric/reflection effects

Frame pacing remains more important than maxing every effect. Android recommends
Swappy/frame pacing for smooth presentation and Vulkan as its primary low-level
graphics API for custom engines.

References:
https://developer.android.com/games/sdk/frame-pacing
https://developer.android.com/games/develop/vulkan/overview
