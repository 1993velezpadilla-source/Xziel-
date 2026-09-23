# XZIEL Diegetic Advertising System v1

Status: design + Sanctum placement plan  
Origin: Volnox concept, expanded into a reusable XZIEL map-monetization system  
Goal: keep maps free while monetizing through advertising that exists naturally inside the game world.

## Product rule

Ads must feel like set dressing, props, signage, radio/TV content, decals, plaques, flags, printed material, or other believable objects already belonging to the map.

Never use:
- forced full-screen ads during gameplay
- pop-ups over combat
- fake UI buttons
- ads that cover objectives, enemies, hit feedback, doors, interactives, or HUD
- audio ads that ignore distance/occlusion
- repeated looping that becomes annoying
- an ad dependency that prevents the map from loading or working offline

If no paid campaign is available, every slot falls back to a lore-appropriate fictional asset so the map still looks complete.

## Supported slot classes

### 1. SURFACE_STATIC
A texture/material swap on a believable surface:
- poster
- notice board
- framed picture
- wall sign
- equipment/service placard
- printed sheet
- small logo/name plate

Best for high-fill, low-annoyance campaigns.

### 2. SURFACE_VIDEO
Video displayed only on a believable screen or projection surface:
- television
- monitor
- projector
- digital display

Video must stop/idle outside the visibility budget and must never block gameplay.

### 3. SPATIAL_AUDIO
An advertisement emitted by an actual world prop:
- radio
- tape recorder
- TV
- PA speaker
- vehicle radio

Audio follows the same spatial audio rules as the map:
- 3D position
- distance attenuation
- obstruction/occlusion
- room/reverb send
- optional power-state gating
- immediate fade when the player leaves the audible radius

The player should hear it as "a radio in the room", not as an ad injected into the master bus.

### 4. PROP_BRANDING
Brand/name/logo integrated into a physical prop:
- maintenance case
- tool box
- crate
- machine plate
- clock maker plate
- vehicle panel

Keep this subtle. No emissive logo just to force attention.

### 5. ENVIRONMENT_TEXT
Short sponsor name or campaign line painted/printed into world dressing where text already makes sense.

Never imitate quest writing, warning clues, ritual symbols, interact prompts, or navigation text.

### 6. FLAG_BANNER
A physical flag/banner/sign that moves only if the map already supports bounded authored animation.

## Player-first rules

1. Gameplay is always more important than ad viewability.
2. Ads never alter enemy visibility, pathing, collision, damage, objective timing, or input.
3. No ad may appear on an altar, sigil, corpse, gore decal, grave marker, sacred focal surface, quest clue, zombie barricade, boss spawn, or required navigation landmark.
4. Ads do not increase brightness/contrast beyond the visual language of the room just to get attention.
5. Audio advertising is proximity-based, spatialized and frequency-capped.
6. A player can walk away from an audio ad. No global "voice of god" playback.
7. Never restart an ad because the player stepped in and out of range.
8. Do not count an impression merely because an asset downloaded.
9. Network/ad-server failure must be invisible to gameplay.
10. Paid assets are content, never executable code.

## Runtime architecture

Keep advertising out of the render/audio realtime path.

Recommended separation:

- AdCampaignService
  - fetches a signed campaign manifest outside gameplay-critical threads
  - selects creatives by map/slot compatibility
  - caches assets before or during safe loading periods
  - supplies only validated local asset handles to runtime

- DiegeticAdSlot
  - stable map-authored slot ID
  - type
  - transform/surface binding
  - accepted aspect ratios/codecs
  - brand-safety tags
  - fallback asset
  - impression measurement rules

- AdExposureTracker
  - visual: visibility, occlusion, view angle, on-screen area, cumulative view time
  - audio: audible radius, attenuation, occlusion, cumulative audible time
  - deduplicates exposures per campaign/session
  - queues telemetry off-thread

- CreativeValidator
  - size/duration limits
  - codec/format allowlist
  - content-category allowlist/denylist
  - checksum/signature verification
  - rejects malformed or missing assets

The map must never wait on an ad request.

## Frequency caps — initial product target

These are XZIEL UX defaults, not advertising-industry measurement standards:

- static surfaces: may remain in-world for the match
- video surface: maximum one active moving creative in the same room
- spatial audio: no repeated playback of the same creative in one match
- spatial audio: target 6–15 seconds per creative
- spatial audio: maximum two paid audio creatives per player per match by default
- after audio playback completes, the prop returns to lore/static ambience
- never trigger paid audio during boss dialogue, quest instructions, round transition stingers, critical horror one-shots, or player-down/revive priority audio

Campaigns may request lower frequency. They may not override the game's upper caps.

## Measurement

Implement measurement compatible with intrinsic in-game advertising concepts rather than counting naive "served" events.

Record, at minimum:
- campaign ID
- creative ID
- slot ID
- map ID
- media type
- asset-ready timestamp
- first eligible exposure timestamp
- cumulative visible/audible duration
- visual occlusion state
- approximate screen coverage for visual slots
- distance + attenuation state for audio slots
- session-scoped deduplication key

Do not place analytics or networking in the audio callback/render hot path.

## Privacy / targeting default

Prefer contextual inventory:
- map
- room/slot type
- game language
- broad platform class
- campaign schedule

Do not require behavioral profiling for the system to make money.

If the game or a distribution channel is covered by children's privacy rules, do not enable behavioral/targeted advertising without the required consent/compliance path. Keep a non-personalized contextual mode as the baseline.

## Disclosure / transparency

The ad must not pretend to be independent editorial/gameplay content when that would mislead the player.

For obvious real-world billboards/posters/brand signs, the commercial nature may already be apparent. For interactive, clickable, recommendation-like, or less obvious sponsored content, provide a clear "Ad"/"Advertisement"/localized equivalent close to the experience when needed.

Do not disguise a click-out as a gameplay interaction.

## SANCTUM OF ASH — candidate inventory

The current church design already contains believable hosts for this system.

### A01 — Fallen Courtyard / Parish Notice Board
Type: SURFACE_STATIC  
Priority: A  
Host: broken parish notice board already in the horror dressing plan.  
Creative shape: poster / community notice / sponsor artwork under cracked glass.  
Why it works: seen early, completely natural, no interruption.  
Rules: never cover the main entrance readability or zombie approach lanes.

### A02 — Office / Physical Radio
Type: SPATIAL_AUDIO  
Priority: A  
Host: physical radio/tape recorder already specified for the office.  
Trigger: only when player enters the authored audible area and campaign has not played this match.  
Power state: may be available as static before power; paid broadcast preferred after power restoration.  
UX: 3D mono/stereo source, attenuation + occlusion, 0.25–0.5 s fades, stop being intelligible outside the room.  
Fallback: lore radio static / survivor transmission.

### A03 — Office / Projector or Slide Surface
Type: SURFACE_VIDEO or SURFACE_STATIC  
Priority: A  
Host: projector/slide equipment already specified in the office.  
Creative shape: 4:3 or author-approved projection crop.  
Rules: silent by default; projector visual should never replace the room's quest/story evidence.  
Fallback: archived parish slides / incident material.

### A04 — Nave / Secondary Community Frame
Type: SURFACE_STATIC  
Priority: B  
Host: secondary wall frame/community notice surface away from the altar, stained-glass hero surfaces and ritual area.  
Creative shape: framed print, event card, local-looking poster.  
Rules: no placement on altar axis, Ash Sigil area, confession horror focal point, wall-buy read zones or player combat sightline.

### A05 — Boiler / Service Placard
Type: SURFACE_STATIC or PROP_BRANDING  
Priority: B  
Host: maintenance/safety/service wall or equipment plate near existing repair tools/fuse-panel dressing.  
Creative shape: service-company style plate or industrial sticker.  
Rules: must not look like a power-switch instruction or fuse quest clue.

### A06 — Tower Stairs / Maintenance Sign
Type: SURFACE_STATIC  
Priority: B  
Host: maintenance placard on a wall landing.  
Creative shape: small vertical/horizontal sign.  
Rules: keep contrast low enough that it does not become a fake navigation marker; never obscure scratched numbers or authored horror clues.

### A07 — Clock Chamber / Maker Plate
Type: PROP_BRANDING or ENVIRONMENT_TEXT  
Priority: B  
Host: small clock/maintenance maker plate.  
Creative shape: compact logo/name/text.  
Rules: cannot contain times, numbers or layouts that could be confused with the 03:17 quest clue.

### A08 — Roof / Weathered Banner or Flag
Type: FLAG_BANNER  
Priority: C / optional  
Host: authored non-navigation exterior anchor.  
Why optional: can be visually strong, so use only if it looks believable in the final fictionalized architecture.  
Rules: never dominate the tower silhouette or lightning readability.

## SANCTUM hard exclusion zones

No paid ad inventory in:
- altar / Altar Forge hero area
- Ash Sigil ritual zone
- Bell Warden spawn/fight focal point
- grave markers
- corpses/gore
- stained-glass hero art
- Seven Bells controls
- 03:17 clues
- perk/wall-buy prompts
- doors and barricade interaction surfaces
- zombie spawn windows
- player spawn look-at focal point
- any surface required to understand a route or escape path

## Placement scoring

Before a slot becomes sellable, score it in a representative gameplay capture:

- Believability: 0–5
- Gameplay obstruction risk: 0–5 (5 = none)
- Horror-tone compatibility: 0–5
- Natural player exposure: 0–5
- Quest-confusion risk: 0–5 (5 = none)
- Audio annoyance risk where applicable: 0–5 (5 = none)
- Mobile readability/performance: 0–5

Ship only slots with no critical failure and a strong aggregate score. Do not add more slots just to inflate inventory.

## Commercial packaging

Sell inventory by experience, not by raw banner count:

- "Sanctum Arrival" — courtyard notice-board placement
- "Sanctum Broadcast" — office proximity-radio placement
- "Sanctum Archive" — office projector placement
- "Sanctum Environmental Pack" — low-key static placements across service/tower spaces
- "Map Sponsor" — one restrained brand across several compatible slots with strict frequency caps

Keep the map free even when inventory is unsold.

## Next implementation pass

1. Geometry-fit A01–A08 against the current native Sanctum asset.
2. Capture screenshots from the player's actual route for every candidate.
3. Reject any candidate that competes with horror beats, combat, navigation or quests.
4. Save exact transform/surface binding in `ads/sanctum_of_ash/diegetic_slots_v1.json`.
5. Add local fallback art/audio.
6. Implement signed campaign manifest + cache.
7. Implement exposure measurement off-thread.
8. Add an internal debug view that draws slot IDs, bounds, current creative and exposure state.
9. Test a full match with ads enabled and disabled; gameplay timing must be identical.


## Google Play policy profile — 2026-09-23

Detailed research is maintained in `docs/GOOGLE_PLAY_DIEGETIC_ADS_POLICY_RESEARCH_2026-09-23.md`.

Architecture decision:
- direct diegetic sponsorship and Google/programmatic inventory are separate delivery paths
- SPATIAL_AUDIO is direct-sponsor inventory by default; do not route arbitrary programmatic audio into world radios without explicit product-format support
- programmatic native/display units must preserve all required ad attribution/AdChoices and must never be disguised as gameplay UI
- contextual delivery is the default; AAID is not required for direct contextual sponsorship
- every creative must pass content-rating, category, placement, privacy and destination checks before eligibility

### Ambient sponsor audio profile

The preferred XZIEL radio ad is intentionally quiet and subordinate to the game mix:
- 6–12 seconds preferred, 15 seconds hard maximum
- 2–3 second player dwell before first start
- ~8–14 dB below the dominant local ambience/gameplay bed at normal pass-by distance
- hard ceiling remains below the local gameplay reference; no make-up gain to fight gunshots/zombies
- 1.0–1.75 s fade-in and 0.5–1.25 s fade-out
- no gameplay ducking, no attention stingers, no head-locked playback
- suppress/fade during combat, quest VO, boss/round events, down/revive priority audio
- same creative once per match; maximum two paid proximity-radio messages per player per match; target at least 10 minutes between paid starts
- player may disable sponsored world audio; fallback lore audio replaces it and no paid exposure is counted

The design goal is environmental presence, not interruption: a player focused on combat should barely notice the sponsor; a player who intentionally listens near the radio can understand it.
