# Google Play / In-Game Advertising Compliance Research — 2026-09-23

Scope: XZIEL / ZOMBIESSSSSSS PORTABLE diegetic advertising system.

This is an engineering/product policy checklist, not legal advice. Re-check source policies before a public release because platform rules change.

## Executive decision

Use two clearly separated monetization paths:

### PATH A — DIRECT DIEGETIC SPONSORSHIP
XZIEL contracts directly with a sponsor and ships/caches a validated creative into an authored world slot.

Best uses:
- wall posters and frames
- service/maintenance plates
- branded props and packaging
- vehicle livery
- newspapers/flyers/calendars
- in-world radio sponsor messages
- TV/projector material
- flags/banners where visually natural

This path gives XZIEL the most control over horror tone, volume, frequency, content rating compatibility and offline fallback.

### PATH B — GOOGLE/PROGRAMMATIC INVENTORY
Use only Google-supported SDK formats and obey the relevant AdMob/Ad Manager requirements for that format.

Important:
- programmatic native ads require clear ad attribution such as "Ad", "Advertisement" or "Sponsored" and AdChoices where applicable.
- do not assume a custom proximity-radio implementation qualifies as supported Google audio inventory.
- Google audio/video publisher products have their own product-specific rules in addition to Google Play policy.
- until a Google product explicitly supports our exact 3D-radio use case, treat SPATIAL_AUDIO as direct-sponsor inventory rather than piping generic programmatic audio into the world.

This split prevents the engine from trying to force a programmatic mobile-ad format into a game-world interaction it was not designed for.

## Google Play policy findings

### Ads are considered part of the app
Google Play states that ads and their associated offers are part of the app and must comply with Play policies, including restricted-content rules.

Engineering consequence:
- every creative passes XZIEL content validation before becoming eligible
- campaign content rating must be <= the app's applicable content rating
- landing destination must also be appropriate

Source:
https://support.google.com/googleplay/android-developer/answer/9857753

### No disruptive or unexpected gameplay ads
Google Play prohibits disruptive advertising and gives unexpected ads during gameplay/beginning of a level or content segment as violations. Non-full-screen or integrated advertising that does not interfere with normal gameplay is treated differently from disruptive full-screen interstitial behavior.

XZIEL rule:
- never interrupt player control
- never put an ad between "Play" and gameplay
- never interrupt round start
- no forced full-screen gameplay ads
- no ad overlays over combat
- no ad gates before doors/objectives
- world ads remain world objects and never steal input focus

Sources:
https://support.google.com/googleplay/android-developer/answer/9857753
https://support.google.com/googleplay/android-developer/answer/12271244

### Do not mimic UI or system behavior
Ads must not impersonate app UI, operating-system notifications or warnings.

XZIEL rule:
- no fake interact prompt
- no fake objective marker
- no fake loot icon
- no fake system notification
- no fake "download complete", low battery, warning, message, achievement, revive or reward UI
- no sponsored asset that looks like a wall-buy/perk prompt

Source:
https://support.google.com/googleplay/android-developer/answer/9857753

### Ad content must fit the app content rating
Google Play requires ads and associated offers to be appropriate for the app's content rating.

XZIEL campaign gate:
- deny creatives above the current app rating
- deny destination apps/offers above rating
- use a conservative brand-safety allowlist
- never let an ad network choose unrestricted categories

Source:
https://support.google.com/googleplay/android-developer/answer/9859655

### Play Console ad declaration
Google Play requires developers to declare whether an app contains ads. It explicitly lists ad SDK banners/interstitials/native ads and house ads as examples that should be declared. The Play documentation separately notes that the "Contains ads" label does not itself indicate other commercial content such as paid product placement.

XZIEL release rule:
- if an ad SDK or dynamic ad network is present, declare that the app contains ads
- direct paid product placements still require compliance with applicable law and Play policies even when the Store label does not describe product placement
- keep Play Console declarations synchronized with actual shipped behavior

Source:
https://support.google.com/googleplay/android-developer/answer/9859455

### Data Safety / Advertising ID
Developers are responsible for data collected/shared by their own code and third-party SDKs. Android Advertising ID use has declaration/permission requirements, and users can reset/delete the identifier.

XZIEL privacy-first default:
- contextual sponsorship does not require AAID
- do not collect AAID merely because an ad system can
- keep exposure measurement session-scoped where possible
- if a programmatic SDK collects/shares device identifiers, reflect the actual behavior accurately in Data Safety
- isolate ad telemetry from player identity

Sources:
https://support.google.com/googleplay/android-developer/answer/6048248
https://support.google.com/googleplay/android-developer/answer/13323374

## Children / Families policy gate

If children are included in the Play target audience, additional rules apply.

Google Play requires, among other things:
- Families Self-Certified Ads SDKs for ads served to children/users of unknown age when an ads SDK is used
- no interest-based advertising or remarketing for those users
- child-appropriate ad content
- Families-compliant ad formats
- accurate target-audience declarations
- a neutral age screen for mixed audiences when needed
- strict identifier/data rules

Google also states that direct advertiser deals using an SDK for inventory management can be permitted without the SDK itself being Families self-certified, but the developer remains responsible for compliant content and data practices.

XZIEL rule:
- do not accidentally opt into a child-directed audience
- if children are ever intentionally included, switch the whole ad subsystem into a separately reviewed Families mode before serving anything
- contextual-only targeting remains the safest baseline

Sources:
https://support.google.com/googleplay/android-developer/answer/9893335
https://support.google.com/googleplay/android-developer/answer/9900633
https://support.google.com/googleplay/android-developer/answer/9867159

## AdMob / Google programmatic native constraints

Google AdMob native ads can visually match an app, but they still require clear attribution. Google documents an "Ad", "Advertisement" or "Sponsored" badge and AdChoices overlay requirements for its native implementation.

Therefore:
- a Google-served poster cannot be made indistinguishable from ordinary world art
- programmatic Google slots need a readable sponsored/ad treatment appropriate to the format
- do not hide required controls/attribution inside dirt, darkness or geometry
- avoid placing clickable units near constant gameplay interactions because accidental clicks are a policy/traffic-quality risk

Sources:
https://support.google.com/admob/answer/6239795
https://support.google.com/admanager/answer/7031536
https://support.google.com/admob/answer/6293636

## Google-served audio caution

Google's advertising/publisher products impose additional audio rules depending on product and placement. Google Ad Manager audio inventory is designed around audio/VAST inventory, and Google Publisher rules include constraints for audio/video playback. Google Ads third-party serving guidance also contains audio-specific requirements.

Engineering conclusion:
- do not implement "generic AdMob audio ad -> automatic world radio" by assumption
- keep XZIEL's automatic proximity-radio sponsor format as DIRECT DIEGETIC SPONSORSHIP unless/until the selected ad product's terms explicitly support the implementation
- if using a Google-served audio format later, implement its current product-specific mute/autoplay/control requirements exactly

Sources:
https://support.google.com/admanager/answer/7642796
https://support.google.com/admanager/answer/10437795
https://support.google.com/adspolicy/answer/94230

## XZIEL AMBIENT SPONSOR AUDIO — v2

Intent: a paid radio transmission should behave like quiet environmental storytelling. A player who is fighting should barely register it. A player who stops near the radio and listens can understand it.

### Hard UX rules
- never duck gunshots, zombies, footsteps, dialogue, quest VO, music or round cues for an ad
- no compressor/limiter setup that makes the sponsor voice jump in front of the mix
- no stinger, bass drop, siren, alarm, telephone ring or sudden transient used only to grab attention
- no master-bus playback
- no center/head-locked voice
- source must have a physical world position
- normal geometry occlusion applies
- leave the room -> ad fades naturally
- combat begins -> ad gently fades under/pauses instead of fighting the gameplay mix
- no restart exploit when crossing the trigger boundary
- no ad playback immediately after player down/revive, boss spawn, quest instruction or round transition

### Quiet-mix target
These are internal XZIEL UX targets, not Google/IAB measurement standards.

At a normal pass-by distance:
- sponsor voice target: approximately 8–14 dB below the dominant local gameplay/ambience bed
- hard ceiling: do not let the sponsor voice become louder than 6 dB below the local gameplay/ambience reference
- no automatic "make-up gain" if the room is noisy
- transient peaks remain controlled; no attention-grabbing peak normalization
- fade in: 1.0–1.75 s
- fade out: 0.5–1.25 s
- minimum dwell before first start: 2.0–3.0 s
- preferred paid message duration: 6–12 s
- absolute XZIEL creative maximum: 15 s for this ambient format
- same paid creative: max once per match
- total paid proximity-radio messages: max 2 per player per match
- minimum spacing between paid audio starts: target 10 minutes

The IAB gaming creative guidance recommends keeping game audio ads short, avoiding loud spikes and limiting frequency; its published best practice says 15 seconds is ideal and discusses one-to-three audio ads per 20 minutes. XZIEL intentionally chooses a lower-disruption profile.

IAB source:
https://www.iab.com/guidelines/creative-guidelines-and-best-practices-in-advertising-in-gaming/

### Trigger state machine
A paid spatial audio creative becomes eligible only when:
1. asset is already local/validated
2. player is inside the same authored room/audibility zone
3. player has remained in range for the dwell threshold
4. no critical narrative VO is active
5. no boss/round transition state is active
6. local combat intensity is below the configured threshold
7. campaign/session frequency cap allows it

If combat begins while playing:
- ramp sponsor bus down instead of ducking the game
- optionally pause at a sentence boundary
- resume only if still in range and the interruption was short
- otherwise mark the creative "attempted" and do not aggressively restart it

### Disclosure
Industry best practice from IAB recommends an audible ad disclosure for gaming audio. For direct sponsor radio inventory:
- use a short natural radio-announcer disclosure such as a localized "sponsored message" inside the transmission
- keep it at the same quiet world-source level; do not make the disclosure louder as an attention hack
- when subtitles are enabled, tag the caption as sponsored
- if a companion screen/logo is interactive, it must also be clearly identified and must not imitate gameplay UI

### Optional player control
Recommended:
- "Sponsored world audio" toggle
- default ON only when allowed by the chosen distribution/ad model
- respects master/ambience volume
- OFF means use lore fallback audio and report no paid audio exposure
- no reward/penalty for turning it off

This gives players who are especially sensitive to advertising a clean escape without removing the free-map business model for everyone else.

## LOW-IMPACT INVENTORY IDEAS FOR FUTURE MAPS

Prefer placements where advertising is plausible even in the real-world version of the environment.

### Near-zero interruption
- newspapers on tables
- magazine covers
- calendar sponsor footer
- cardboard boxes / packing labels
- tool cases
- equipment manufacturer plates
- cleaning-product containers
- batteries / flashlight packaging
- delivery crates
- vending-machine skins
- coffee cups
- food wrappers
- vehicle livery
- license-plate frame / dealership plate
- workshop/service stickers
- small monitor boot/logo screen
- station identification card beside a radio
- projector slide footer
- corkboard flyers
- receipts/invoices
- map brochure rack
- hotel keycard / office access-card art where appropriate
- emergency-supply cartons
- branded umbrellas or rain gear

### Stronger but still diegetic
- bus-stop poster
- storefront sign
- exterior billboard
- theater marquee
- stadium/racetrack board
- subway platform panel
- gas-station signage
- TV commercial visible in a room
- radio broadcast
- digital departure/information board sponsor panel

### Avoid even if monetizable
- crosshair/HUD sponsorship
- ads on ammo counter
- ads on reload prompt
- ads on perk/wall-buy UI
- ad on mystery-box result
- ad in revive/downed UI
- ad audio mixed as narrator
- ad triggered by taking damage
- ad on door prompt
- branded jump-scare
- sponsor logos on corpses/gore
- sponsor logo replacing a quest clue
- bright animated signage in a horror sightline just for attention

## Creative rotation without pop-in

For static world ads:
- pick the creative before entering the map/zone when possible
- hold that creative for the full match or a long authored interval
- do not hot-swap a poster while it is visible
- swap between matches or while a surface is definitely out of view
- keep fallback geometry/material identical so network failure causes no pop

For video:
- no autoplay sound
- one moving paid surface per room maximum
- reduce/update-rate when distant
- freeze to a valid poster frame when not eligible to animate

## Contextual targeting ideas that do not need behavioral profiling

Campaign selector may use:
- map ID
- slot type
- game language
- country/region if obtained through a compliant coarse mechanism
- platform class
- current campaign schedule
- game content-rating compatibility
- sponsor category compatibility with the map

Do not require:
- contact list
- precise location
- microphone-derived profiling
- browsing history
- cross-app behavioral profile

## Brand-safety denylist recommendation

Even when the app's rating might technically permit some categories, XZIEL should default-deny high-friction categories unless explicitly reviewed:
- tobacco/nicotine
- recreational drugs
- gambling/betting
- adult sexual/dating content
- deceptive financial products
- shock/gore creatives
- political persuasion
- weapons sales
- scam-like install/cleaner/virus-warning creatives

This protects the atmosphere and reduces policy/reputation risk.

## Validation checklist before enabling a paid slot

A slot fails if any answer is "yes":
- Could it obscure an enemy?
- Could it be mistaken for an objective?
- Could it be mistaken for UI?
- Could it cause an accidental tap?
- Does it become louder/brighter than gameplay merely to force attention?
- Does it start at a round/level boundary?
- Does it alter gameplay timing?
- Does it require network access for the map to work?
- Can it show content above the app's rating?
- Does it collect identity data not needed for contextual delivery?
- Does it violate the selected ad provider's product-specific format requirements?

A slot passes only after a real mobile playthrough with ads enabled and disabled shows equivalent gameplay timing and readability.
