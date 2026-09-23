# XZIEL DIEGETIC MONETIZATION BIBLE — Deep Research v1
Updated: 2026-09-23

Purpose: monetize free XZIEL / ZOMBIESSSSSSS PORTABLE maps without designing gameplay around advertising.

This document expands the existing diegetic-ad system with current Google Play policy research, IAB/MRC gaming measurement guidance, FTC disclosure guidance, and implementation patterns observed in intrinsic in-game advertising platforms such as Anzu, Frameplay, AdInMo and Gadsme.

This is product/engineering research, not legal advice. Re-check current platform and local-law requirements before public launch.

---

# 1. NORTH STAR

The player should be able to finish a full match without ever feeling interrupted by advertising.

The commercial system succeeds when:
- the map still feels authored rather than monetized;
- a brand can obtain measurable exposure;
- the player never loses control, visibility, audio priority or navigation clarity;
- unsold inventory becomes normal lore instead of empty rectangles;
- network failure cannot change gameplay;
- ad measurement is credible enough to sell to serious advertisers.

Core XZIEL rule:

> The map is not built around the ad. The ad is allowed to inhabit the map.

---

# 2. WHAT THE INDUSTRY CALLS THIS

IAB/MRC use the intrinsic in-game advertising family for advertising embedded inside gameplay environments.

Useful IAB categories include:
- Dynamic In-Game Advertising (DIGA)
- Digital Video In-Game Advertising (DVIGA)
- Static In-Game Advertising (SIGA)
- Hardcoded In-Game Ad Objects

IAB's 2025 Gaming Measurement Framework also treats Display, Video, Audio and Custom gaming formats separately and calls out baseline metrics such as impressions, viewability, reach, frequency, audio duration and audible impressions.

Sources:
- https://www.iab.com/blog/intrinsic-in-game-measurement-guidelines/
- https://www.iab.com/guidelines/gaming-measurement-framework/
- https://www.iab.com/wp-content/uploads/2025/06/IAB_Gaming_Measurement_Framework_June_2025.pdf
- https://www.mediaratingcouncil.org/standards-and-guidelines

Commercial implication:
XZIEL does not need to invent a weird category called "hidden game ads." We can sell recognized intrinsic inventory while keeping the creative execution extremely subtle.

---

# 3. GOOGLE PLAY: SAFE PRODUCT SHAPE

Google Play's Ads policy prohibits disruptive ads that unexpectedly interfere with gameplay, cause inadvertent clicks, or block normal use. The policy explicitly distinguishes non-interfering monetization from disruptive full-screen behavior.

XZIEL should therefore favor persistent environmental inventory over interruption inventory.

Allowed-design direction:
- posters
- plaques
- billboards
- TV/projector surfaces
- radio props
- product packaging
- vehicle liveries
- store signs
- newspaper/magazine assets
- service-company markings
- sponsor attribution integrated near the relevant asset when required

Avoid:
- unexpected full-screen ads during gameplay
- ad before a gameplay action takes effect
- forced ad gates
- deceptive close buttons
- ad surface overlapping common tap zones
- fake system notifications
- fake quest/UI prompts

Google source:
https://support.google.com/googleplay/android-developer/answer/9857753

---

# 4. PAID PRODUCT PLACEMENT VS AD SDK INVENTORY

Google Play's Play Console documentation explicitly distinguishes the Store's "Contains ads" label from other commercial content such as paid product placement. If the app uses ad SDK/display/native/banner ads, declare ads. Paid product placement still has to comply with applicable local law.

Source:
https://support.google.com/googleplay/android-developer/answer/9859455

XZIEL architecture therefore has three commercial paths.

## A. DIRECT PRODUCT PLACEMENT
Sponsor pays XZIEL directly.

Examples:
- branded drink can on a desk
- real tool manufacturer on repair case
- vehicle livery
- radio sponsor message
- poster under glass
- branded batteries near flashlight
- clock maker/service-company plate

Advantages:
- maximum artistic control
- no third-party runtime SDK required
- easy contextual delivery
- easy offline fallback
- easiest to keep horror-compatible

## B. DIRECT DYNAMIC CAMPAIGN
XZIEL's own campaign service selects signed creative for approved map slots.

Advantages:
- can rotate sponsors without app update
- still keeps full XZIEL creative approval
- no need to let arbitrary network content enter the game

Requirements:
- secure signed manifest
- asset allowlist
- content-rating gate
- cache/fallback
- telemetry
- campaign expiration

## C. PROGRAMMATIC / THIRD-PARTY SDK
Use an intrinsic gaming provider or Google-supported format.

Advantages:
- external demand/fill
- standardized advertiser workflow

Costs:
- SDK/privacy review
- consent obligations
- more creative-control complexity
- provider-specific impression rules
- potential AD_ID/Data Safety impact

Default recommendation:
Start with A + B. Make C optional, modular and removable.

---

# 5. WHAT CURRENT INTRINSIC AD PLATFORMS TEACH US

## Frameplay
Frameplay's implementation exposes authored "Ad Spaces" with fixed ratios, placeholder materials, quality multipliers and activation colliders. Its best-practice guidance explicitly says "less is always more" and warns that too many visible ad spaces overwhelm the scene and reduce individual impression quality.

Strong ideas to copy clean-room:
- each slot has unique ID/name
- placeholder/fallback is first-class
- only activate/download when player is relevant to area
- lower texture resolution for small distant placements
- measure obstruction, angle and visibility
- do not require an ad to exist for the prop to look correct
- limit simultaneous visible inventory

Sources:
- https://docs.frameplay.gg/guide/ad-spaces/
- https://docs.frameplay.gg/guide/best-practices/
- https://docs.frameplay.gg/guide/revenue/

## AdInMo
AdInMo links placement keys to visual or audio game objects and documents audio/video/display impression behavior. Its current product also supports clickable placements with a pre-click visualizer and magnifier stage.

Strong ideas:
- treat audio source as an authored game object
- placement-specific capabilities
- click behavior is opt-in per placement
- additional interaction stage before leaving gameplay
- debug/impression-validity tooling is crucial

Do NOT copy its audio volume threshold literally into XZIEL. Our ambient sponsor format is intentionally quieter and direct-sponsor-first.

Sources:
- https://documentation.adinmo.com/sdk-integration
- https://documentation.adinmo.com/adding-placements
- https://documentation.adinmo.com/creating-your-first-placement
- https://documentation.adinmo.com/ad-placements-and-debugging-tools

## Anzu
Anzu positions intrinsic placements as player-first, inside gameplay, with publisher placement control. In February 2026 it introduced click-enabled intrinsic formats using deliberate interactions such as double-tap and tap-and-hold to reduce accidental clicks.

Strong idea:
A commercial click must require an interaction distinct from normal combat.

Source:
https://www.anzu.io/news/anzu-redefines-in-game-advertising-with-performance-driven-player-first-intrinsic-formats

## Gadsme
Gadsme emphasizes native in-world assets, no overlays/popups/interstitial interruptions, and support for proprietary C++ engines in addition to major engines.

Useful validation:
XZIEL's custom-engine architecture does not inherently prevent intrinsic programmatic monetization.

Source:
https://www.gadsme.com/publishers

Vendor revenue/uplift percentages are vendor marketing claims, not XZIEL forecasts. Do not use them in financial planning without our own observed data.

---

# 6. DENSITY: HOW TO MAKE ADS FEEL LIKE REALITY, NOT A STORE

Never maximize "number of placements." Maximize quality.

XZIEL scene-density rule:
- normal room: 0–1 clearly readable paid placement
- large exterior plaza/street: up to 2 paid placements if naturally separated
- hero horror room: preferably 0
- critical combat arena: 0 prominent moving paid placements
- never create a wall containing several unrelated advertiser tiles

A single believable service-company plaque can be worth more to the experience than six banners.

Only one moving paid surface may be readable in the same room at once.

---

# 7. "WORLD INVENTORY" IDEA BANK

## Printed / paper
- parish/community notice board
- newspaper front page
- magazine cover
- calendar sponsor footer
- corkboard flyer
- receipt/invoice
- delivery note
- map brochure
- maintenance worksheet
- event poster
- old coupon
- transit map sponsor strip

## Industrial/service
- generator manufacturer plate
- boiler service label
- breaker-box service sticker
- tool-case logo
- battery packaging
- flashlight box
- electrical cable reel branding
- emergency supply carton
- fire-extinguisher service tag
- paint bucket
- cleaning-product bottle
- maintenance uniform patch

## Food / everyday props
- coffee cup
- paper bag
- vending-machine skin
- canned drink
- water bottle
- snack wrapper
- cereal/food carton
- restaurant takeaway box
- delivery crate

Do not create unnatural hero product close-ups just for sponsor visibility.

## Vehicles / transportation
- van/truck livery
- taxi door marking
- delivery-company logo
- bus-stop poster
- fuel-station sign
- dealership/license-plate frame
- mechanic/service sticker
- cargo markings

## Electronics / media
- radio station card
- small TV commercial
- monitor boot logo
- projector slide footer
- VHS/tape label
- speaker manufacturer plate
- electrical appliance badge

## Architecture
- storefront fascia
- building service plaque
- small sponsor plate on notice board
- public-information board footer
- arena/stadium board in maps where natural
- construction hoarding
- weathered billboard
- road-side sign

## Character-adjacent
Use very cautiously:
- clothing patch
- backpack manufacturer tag
- watch face/manufacturer
- sunglasses
- generic consumable held by NPC

Never turn zombies, corpses, clergy, ritual victims or gore into branded mannequins.

---

# 8. AUDIO: "BARELY THERE" SPONSOR MIX

The radio advertisement must behave as ambience.

## Routing
Create a dedicated world bus:

World
 └─ Ambience
     └─ SponsoredWorldAudio

The sponsor bus can be attenuated by gameplay activity.
Gameplay buses are NEVER attenuated by the sponsor.

## One-way priority system
Inputs that can push sponsor level DOWN:
- nearby gunfire
- enemy vocal intensity
- player damage/down state
- quest/dialogue VO
- round transition
- boss events
- horror one-shot
- important navigation sound

Nothing pushes gameplay down for sponsor intelligibility.

## Mix philosophy
At pass-by distance:
- player may notice human speech exists
- words do not need to be fully intelligible
- if player approaches the physical radio during a calm moment, the message becomes understandable

Internal starting target:
- 8–14 dB below dominant local gameplay/ambience at normal pass-by
- never auto-boost to compete with a noisy room
- no attention transient
- no ad-only bass enhancement
- no ad-only stereo widening
- no head-locked center voice
- room occlusion/low-pass/reverb apply like other world sources

These values are XZIEL UX targets, not Google/IAB compliance thresholds.

## Activation
Eligible only when:
- local validated asset ready
- physical source active
- player in authored room
- dwell >= 2–3 seconds
- no priority VO/event
- combat intensity under threshold
- frequency cap available

If gameplay becomes busy:
sponsor fades DOWN.

Never restart because player crosses the trigger repeatedly.

## Frequency
XZIEL conservative starting profile:
- 6–12 sec preferred
- 15 sec maximum
- same creative once/match
- max two paid world-audio messages/player/match
- target >=10 min between paid starts

IAB's gaming framework recognizes audible impressions, audio duration, reach and frequency as relevant audio metrics. That gives us something advertisers understand without making audio loud.

Source:
https://www.iab.com/guidelines/gaming-measurement-framework/

---

# 9. USER VOLUME / MUTE BEHAVIOR

Critical rule:
Sponsored audio obeys the user's game audio settings.

If master/world audio is muted:
- sponsor is muted
- no fake audible impression
- no separate "ad volume" bypass

If sponsored-world-audio setting is disabled:
- play lore fallback
- no paid audio exposure counted

Do not force the device volume upward.
Do not bypass Android audio focus.
Do not start a separate foreground audio session.

---

# 10. INTERACTION: NON-CLICK BY DEFAULT

Default:
- poster = not clickable
- TV = not clickable
- radio = not clickable
- prop logo = not clickable

Reason:
clicks are not required to sell brand-awareness inventory and add accidental-click / gameplay-interruption risk.

If performance inventory is added later:
- no single tap in combat
- no interaction that shares FIRE/ADS/USE/RELOAD/LOOT controls
- require explicit inspect/ad interaction state
- consider hold or double-confirm
- never open browser immediately from an accidental touch
- clearly show commercial nature before external navigation
- pause only if an intentional external-navigation interaction occurs

Google AdMob considers accidental clicks/invalid traffic a serious publisher risk.

Sources:
- https://support.google.com/admob/answer/3342054
- https://support.google.com/admob/answer/6213019

---

# 11. MEASUREMENT THAT SERIOUS ADVERTISERS CAN BUY

Do not report "we downloaded the poster."

## Visual baseline
Per IAB gaming framework:
- impressions
- viewability
- time in view
- reach
- frequency

XZIEL signals:
- slot loaded locally
- slot attached/renderable
- camera frustum
- facing angle
- screen coverage
- geometry occlusion
- UI/particle obstruction
- cumulative qualified view time

## Audio baseline
Per IAB 2025 framework:
- audible impressions
- reach
- frequency
- audio duration/listen-through

XZIEL signals:
- source playing
- user audio state
- effective gain
- distance
- occlusion
- cumulative audible duration
- completion quartile
- sponsor attenuation due to combat

Never count audio when effective output is effectively muted.

## Custom sponsorship
IAB 2025 framework includes sponsorship/integration/custom formats with metrics such as impressions, viewability, reach, frequency, session duration and conversion where applicable.

This means a full "Map Sponsor" package can be sold using standard measurement language.

---

# 12. ANTI-FRAUD / IVT

Serious buyers care whether impressions are real.

Implement:
- session nonce
- dedupe identical exposure bursts
- impossible camera movement detection
- impossible session duration guard
- background/minimized app rejection
- bot/test-build flag
- developer/test devices excluded from billable reporting
- no impression if slot behind camera
- no visual impression if fully occluded
- no audio impression if user audio muted
- campaign signature verification
- telemetry replay protection
- aggregate anomaly reporting

IAB's 2025 framework explicitly recommends invalid-traffic detection/filtration guidance as a core measurement reference.

Source:
https://www.iab.com/wp-content/uploads/2025/06/IAB_Gaming_Measurement_Framework_June_2025.pdf

---

# 13. PRIVACY: MAKE CONTEXTUAL INVENTORY THE DEFAULT

High-value contextual variables:
- map ID
- zone
- slot class
- app language
- device/platform class
- broad country/region where lawfully available
- campaign schedule
- game rating
- sponsor category compatibility

Do not require:
- precise GPS
- contacts
- microphone profiling
- browsing history
- installed-app profiling
- persistent cross-app identity

Benefits:
- less privacy complexity
- fewer SDK permissions
- easier player trust
- still commercially useful because map/scene context is rich

If Google publisher products serve personalized ads in the EEA, UK or Switzerland, Google requires a certified CMP integrated with IAB TCF. Google was supporting TCF v2.3 during 2026.

Sources:
- https://support.google.com/admob/answer/13554116
- https://support.google.com/admob/answer/16918505

---

# 14. THIRD-PARTY SDK FIREWALL

Google Play states that the app developer is responsible for third-party SDK data collection and policy compliance as though the app collected that data directly.

Therefore every ad SDK must be optional behind an abstraction layer.

Required vendor audit before integration:
- SDK size
- native libraries / architectures
- permissions
- background services
- startup behavior
- network domains
- identifiers collected
- consent APIs
- data-retention docs
- child/family status
- crash rate
- render-thread work
- audio-thread behavior
- offline behavior
- remote-code capability
- dependency conflicts
- Play SDK Index issues

Source:
https://support.google.com/googleplay/android-developer/answer/13326895

If an SDK does not meet XZIEL standards, remove it without changing map files.

---

# 15. FAMILIES / AGE GATE

If the target audience includes children, Google Play Families adds strong restrictions, including child-appropriate content, Families-certified SDK requirements in relevant cases, limits on interest-based ads/remarketing and ad-format rules.

Product decision:
Do not casually select child audience groups in Play Console.

If XZIEL intentionally enters a child-inclusive audience later:
- separate Families compliance project
- neutral age screen where applicable
- contextual ads only for child/unknown users
- review direct paid product placement too
- child-appropriate creatives
- certified SDK path where required

Source:
https://support.google.com/googleplay/android-developer/answer/9893335

---

# 16. FTC DISCLOSURE PRINCIPLE

FTC guidance includes explicit video-game examples.

Important distinction:
A real-product billboard in a virtual world is obviously advertising and may not require an extra disclosure merely to reveal that the billboard was paid. Product placement may also not require disclosure where payment is not material to the consumer and no deceptive product claim is made.

But if commercial content is formatted so users may not recognize its nature, or it acts like gameplay/recommendation content, disclosure may be needed.

XZIEL rule:
- environmental branding may remain naturally environmental where legally appropriate
- anything clickable/recommendation-like gets clearer sponsorship treatment
- never disguise commercial navigation as gameplay
- no misleading objective product claims

Source:
https://www.ftc.gov/business-guidance/resources/native-advertising-guide-businesses

---

# 17. CREATIVE ACCEPTANCE

Every creative receives:
- category classification
- app-rating check
- slot-fit check
- tone check
- brightness/motion check
- audio loudness check
- text readability/disclosure check where needed
- destination check if interactive
- malware/file-type validation
- expiration
- checksum/signature

Reject:
- scammy system-cleaner/virus messaging
- fake system UI
- shocking images
- gore creatives
- political persuasion
- weapons sales
- gambling/betting
- nicotine/tobacco
- recreational drugs
- explicit sexual content
- deceptive financial claims
- anything that mimics quest text
- anything using arrows/highlight language that could alter navigation

The XZIEL denylist can be stricter than platform minimums.

---

# 18. CREATIVE TRANSFORMATION RULES

We may weather or integrate a creative only inside advertiser-approved bounds.

Safe transformations:
- physically based lighting
- scene shadows
- mild grime overlay around frame/prop
- perspective transform
- bounded color response to local lighting
- CRT/projector treatment when agreed

Do not:
- cover legal/disclosure text
- distort brand logo beyond approval
- recolor product misleadingly
- crop required copy
- make programmatic attribution invisible
- apply horror gore directly over sponsor creative without permission

Frameplay similarly warns that heavy shader/post-processing changes can reduce impression quality.

Source:
https://docs.frameplay.gg/guide/best-practices/

---

# 19. PERFORMANCE / MOBILE BUDGET

Ads are not allowed to cost meaningful frame time.

Static:
- atlas or texture handle
- lazy request before zone entry
- downscale according to expected screen footprint
- no per-frame CPU work beyond existing visibility measurement

Video:
- one moving paid surface/room maximum
- decode only near eligible visibility
- pause/freeze out of relevance
- cap resolution to real screen contribution
- no HDR/high-bitrate creative by default on mobile

Audio:
- decode/cache outside realtime callback
- source behaves like existing spatial source
- no network work in audio callback

Telemetry:
- sampled/aggregated
- batched
- background queue
- never sync network on render/audio thread

---

# 20. FALLBACK-FIRST DESIGN

Every placement must look finished without an advertiser.

Fallback examples:
- fictional local business
- parish event
- maintenance manufacturer
- emergency broadcast
- archive slide
- radio survivor tape
- public-service notice
- fake period newspaper

No:
- blank white rectangle
- "YOUR AD HERE"
- network error message
- obvious generic placeholder

Frameplay's placeholder-material concept validates this direction.

---

# 21. CAMPAIGN PACKAGES WE CAN SELL

## Map Presence
One premium static placement.
Good for smaller sponsors.

## Environmental Sponsor
Several small brand-safe placements using one brand across compatible props.
Never multiple competing brands in one sightline.

## Broadcast Sponsor
One ambient radio transmission plus an associated small visual radio-station/sponsor card.

## Archive Sponsor
Office/monitor/projector visual package.

## Exterior Sponsor
Vehicle + noticeboard/storefront, only on compatible maps.

## Founding Map Sponsor
Restrained category exclusivity across a map.
Includes direct product placement + environmental static assets.
No takeover UI.

## Local Puerto Rico Pack
Where map fiction/location makes sense:
- local businesses
- restaurants
- music/event brands
- service companies
- auto/dealer brands
- telecommunications
- consumer brands

Context must fit the map; do not randomly inject regional ads into fiction where they break period/place continuity.

---

# 22. WHAT WE SHOULD NOT SELL

Even if someone offers more money:
- HUD takeover
- crosshair brand
- ammo counter brand
- perk-machine sponsor if it harms mechanic readability
- forced browser click
- branded jumpscare
- boss named after advertiser
- quest objective requiring product interaction
- revive sponsor
- death-screen ad
- round-start ad
- ad louder than game
- unskippable sponsor voice
- brand on corpse/grave/ritual victim
- sponsor that demands we move an objective for viewability

Short-term CPM is not worth damaging retention.

---

# 23. CLICK-ENABLED FUTURE MODE

Only build if the core no-click business works first.

Possible flow:
1. player intentionally enters inspect mode near an eligible sponsor object
2. subtle "Sponsored" affordance appears
3. hold/double-confirm interaction
4. optional detail card
5. explicit external-link action
6. only then leave/pause game

No single accidental thumb press opens a browser.

Anzu's 2026 performance formats and AdInMo's pre-click/magnifier concept show the industry is already designing extra-intent mechanics for intrinsic clicks.

Sources:
- https://www.anzu.io/news/anzu-redefines-in-game-advertising-with-performance-driven-player-first-intrinsic-formats
- https://documentation.adinmo.com/creating-your-first-placement

---

# 24. SELLING POINT TO BRANDS

XZIEL's pitch should not be:
"We hide ads so players can't tell."

Pitch:
"We integrate brands into authored, measurable world inventory without interrupting gameplay."

That is both commercially stronger and safer.

Advertiser value:
- long sessions
- context
- natural exposure
- measurable view time
- low clutter
- no banner blindness caused by HUD spam
- category exclusivity possible
- custom creative integration
- audio/visual cross-format package
- direct campaign option

Player value:
- free maps
- no interstitial gameplay interruption
- no paywall caused by map releases
- richer environmental dressing
- optional sponsored audio control

---

# 25. XZIEL INTERNAL SUCCESS METRICS

Advertising is successful only if BOTH sides pass.

Commercial:
- fill rate
- qualified impressions
- time in view
- audible duration
- reach/frequency
- sponsor renewal
- revenue/player hour

Player protection:
- retention delta ads ON vs OFF
- session-length delta
- FPS/frame-time delta
- crash delta
- network MB/session
- ad-mute rate
- complaint rate
- accidental interaction rate
- quest/navigation mistakes near sponsored surfaces

If revenue rises but player metrics degrade, the system is failing.

---

# 26. IMPLEMENTATION ROADMAP

Phase 0 — policy/design
- DONE: Google Play guardrails
- DONE: Sanctum semantic slots
- DONE: ambient sponsor audio profile
- DONE: deep vendor/IAB research

Phase 1 — local prototype
- geometry-fit Sanctum slots
- fallback art
- sponsor-world audio bus
- visibility/audibility tracker
- debug overlay

Phase 2 — measurement
- visual exposure accumulator
- audible exposure accumulator
- local session report
- invalid/test traffic flags

Phase 3 — direct campaigns
- signed campaign manifest
- creative cache
- expiration
- category/rating gate
- upload/admin tooling

Phase 4 — commercial pilot
- one direct sponsor
- one map
- static-first
- optional one ambient radio creative
- compare player behavior ads ON/OFF

Phase 5 — optional external demand
- evaluate Anzu/Frameplay/AdInMo/Gadsme or other current providers
- SDK/privacy/performance audit
- never bind map format directly to vendor SDK

---

# 27. SOURCE INDEX

Google Play / Google:
- https://support.google.com/googleplay/android-developer/answer/9857753
- https://support.google.com/googleplay/android-developer/answer/9859455
- https://support.google.com/googleplay/android-developer/answer/9893335
- https://support.google.com/googleplay/android-developer/answer/13326895
- https://support.google.com/googleplay/android-developer/answer/6048248
- https://support.google.com/admob/answer/6239795
- https://support.google.com/admob/answer/3342054
- https://support.google.com/admob/answer/6213019
- https://support.google.com/admob/answer/13554116
- https://support.google.com/admanager/answer/7642796

Industry standards:
- https://www.iab.com/blog/intrinsic-in-game-measurement-guidelines/
- https://www.iab.com/guidelines/gaming-measurement-framework/
- https://www.iab.com/wp-content/uploads/2025/06/IAB_Gaming_Measurement_Framework_June_2025.pdf
- https://www.mediaratingcouncil.org/standards-and-guidelines
- https://www.iab.com/guidelines/campaign-data-standards/

Consumer advertising disclosure:
- https://www.ftc.gov/business-guidance/resources/native-advertising-guide-businesses

Intrinsic platforms researched:
- https://www.anzu.io/
- https://docs.frameplay.gg/
- https://documentation.adinmo.com/
- https://www.gadsme.com/
