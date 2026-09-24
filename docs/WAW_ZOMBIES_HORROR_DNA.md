# WORLD AT WAR ZOMBIES — HORROR DNA / MAP DESIGN BIBLE

Updated: 2026-09-22  
Project: Xziel / ZOMBIESSSSSSS PORTABLE  
Primary inspiration video: https://youtu.be/6-Mu9VXubeY  
Video title: "The horror of Call of Duty: World at War Zombies" — Doogle McDuff

> Purpose: preserve the design DNA that made early Call of Duty: World at War Zombies feel frightening, mysterious, memorable, and worth exploring, then translate that DNA into original Xziel maps without copying Treyarch/Activision assets.

## Provenance note

The exact YouTube page was identified and indexed, but direct full-stream/caption retrieval was throttled in the current tool environment. This document therefore does not claim to be a verbatim transcript. It captures the concrete points explicitly highlighted by the project owner from the video — lighting, projected light/shadow, wall writing, ambient screams/voices, background SFX, environmental details, and real horror atmosphere — and expands/cross-checks them against World at War map documentation, Activision historical material, and map-specific community research.

This is intentionally a design specification, not a transcript.

---

# 1. The central lesson

Classic World at War Zombies did not feel frightening because the zombies alone were scary.

It worked because the entire map behaved like evidence of something terrible that already happened.

The player entered after the catastrophe.

The building, lighting, sound, writing, bodies, machinery, radios, blocked windows, ruined furniture, distant cries and half-explained experiments all implied:

- people were here before you;
- they suffered;
- they tried to escape;
- something is still happening outside your sight;
- the map knows more than the player does;
- the safest-looking room may still be wrong;
- surviving does not mean understanding.

The map must therefore tell horror stories even when no enemy is visible.

**Rule:** if all zombies are removed from a Xziel map, the environment should still feel disturbing.

---

# 2. Horror is built from uncertainty, not constant action

World at War frequently leaves important things unexplained.

Nacht der Untoten is especially effective because it is small, ruined and comparatively bare. There is no friendly NPC explaining the situation. There is no safe hub. There is no large mission briefing telling the player what the bunker means. The lack of information becomes part of the horror.

Xziel should preserve that effect.

## Xziel rule

Never explain every strange sound, room, body, phrase or machine.

For every major map, include three classes of environmental detail:

### Readable
Player immediately understands it.

- boarded window
- old blood trail
- abandoned weapon
- broken door

### Suggestive
Player can form a theory.

- interrupted sentence on a wall
- dragged blood trail under a locked door
- child-sized handprint
- machinery still moving with no operator
- chair restraints

### Unresolved
Deliberately no confirmed explanation.

- distant scream from an inaccessible zone
- silhouette crossing a window once
- radio fragment with missing beginning/end
- bell ringing while the rope is still
- projector briefly showing an unknown figure
- footsteps above the player in a sealed tower

The unresolved category is critical.

---

# 3. The map should feel like a haunted physical place

The early maps were not clean combat arenas. They were places with a prior function:

- bunker / airfield
- asylum
- swamp outpost
- experimental weapons factory

The horror grows from corrupting that original function.

For Xziel, every map should answer:

- What was this place before the outbreak?
- Who worked/lived here?
- What was normal here?
- What went wrong?
- What did survivors try?
- What physical evidence remains?
- What parts of the building are still functioning incorrectly?
- What sound would this place make even without zombies?

The church in SANCTUM OF ASH is therefore not just a church skin over a Zombies map. It should feel like a ruined parish/church/tower/service complex that was occupied, transformed, defended, abandoned and then corrupted.

---

# 4. Lighting is a horror system, not decoration

The video specifically calls attention to lighting. Treat that as a core game system.

## 4.1 Never illuminate everything evenly

Uniform visibility kills uncertainty.

Use intentional contrast:

- readable combat floor
- darker ceiling volume
- dark doorways
- distant silhouettes
- bright practical source with falloff
- partially illuminated props
- light that reveals only part of a corpse/message
- bright exterior moonlight against dark interiors
- dark foreground with readable backlight

A player should frequently be able to identify shape before detail.

## 4.2 Motivated lights

Prefer lights that appear to come from a believable object:

- hanging bulb
- desk lamp
- furnace
- candle
- lantern
- emergency lamp
- fireplace
- broken fluorescent fixture
- stained-glass window
- lightning outside
- electrical arc
- projector
- burning debris
- moonlight through damaged roof

The source object gives the light narrative meaning.

## 4.3 Broken-light behavior

Not every lamp should flicker. Constant flicker becomes visual noise.

Use three groups:

- stable lights for navigation
- unstable lights for anxiety
- event lights that change because of gameplay

Event examples:

- a corridor light dies when the player crosses a trigger
- lightning exposes a figure for less than a second
- restoring power activates lights room-by-room rather than all at once
- a lamp swings after a nearby impact
- a light briefly reveals writing invisible in darkness

## 4.4 Power-state transformation

World at War used power as both gameplay and atmosphere.

In Xziel, power activation should materially change the map:

- sequential lights energize
- dead machines begin operating
- hum and transformer noise appear
- emergency lamps switch state
- certain shadows disappear while new spaces become readable
- some rooms become less comfortable because power awakens equipment
- previously silent audio emitters activate
- an old projector/radio can become usable
- tower clock or bell machinery begins moving

Power must feel like the player disturbed the building, not simply turned on UI features.

## 4.5 Projected light and moving shadow

The project owner specifically called out projection.

Use original projection effects as horror storytelling:

- stained glass casts distorted color shapes
- lightning throws window-frame shadows across walls
- fan blades or moving machinery interrupt beams
- projector beam carries dust particles
- old film/slide projector throws unstable archival imagery
- swinging lamps create moving occlusion
- silhouettes can briefly cross a projected surface
- ritual symbols only become obvious when lit from one direction

Do not use random moving shadows everywhere. Reserve them for moments the player notices.

## 4.6 Fog, dust, smoke and volumetric depth

Atmosphere is easier to believe when air has depth.

Use:

- thin exterior fog
- room dust in strong light beams
- boiler steam
- low smoke from damaged areas
- rain mist near open doors
- breath/condensation where justified
- ash particles around supernatural zones

Mobile implementation should favor sparse, camera-relevant particles and baked depth cues rather than expensive full-scene volumetrics.

---

# 5. Silence is part of the soundtrack

One of the strongest lessons from World at War is that horror audio should not mean constant horror music.

A quiet base gives every rare sound more power.

## 5.1 Audio hierarchy

Each map should have layers.

### Layer A — base room tone

Very quiet, nearly subconscious.

Examples:
- air moving through damaged windows
- distant rain
- low electrical hum
- pipes
- weak fire
- room resonance
- insects/swamp life
- boiler rumble

### Layer B — local mechanical/environmental sounds

Spatial and tied to visible objects.

Examples:
- hanging sign movement
- chain sway
- loose wood
- dripping water
- tower clock
- electrical arcing
- projector motor
- bell rope creak
- old radiator
- door under wind pressure

### Layer C — off-screen horror one-shots

Rare. Positional. Unexplained.

Examples:
- scream
- child cry
- whisper
- distant banging
- human gasp
- brief running footsteps
- animal whimper
- muffled plea
- object dropped in another room
- short laugh
- chair scrape
- metallic impact

### Layer D — enemy information

Zombie moans, runners, crawlers, attacks and nearby movement.

This layer must support gameplay readability.

### Layer E — event stingers

Use sparingly.

Examples:
- power activation
- round transition
- quest discovery
- special round
- first encounter
- major door opening
- hidden clue discovery

## 5.2 Randomized ambient events

Do not loop screams every 20 seconds.

Build a scheduler with:

- minimum cooldown
- weighted event pool
- per-zone eligibility
- distance checks
- no immediate repetition
- one-shot rarity classes
- silence windows
- round-intensity modifier
- interior/exterior filtering
- player-facing avoidance when appropriate

Recommended conceptual rarity:

- common environment event: several times per round
- uncommon disturbing event: roughly once every few minutes
- rare signature event: may not happen every match
- ultra-rare event: discovery/community discussion material

This is how maps feel alive without becoming predictable.

## 5.3 Audio occlusion

World at War developed sound occlusion so the player could perceive whether sound came through walls/levels.

Xziel should preserve that perception:

- scream behind thick stone = strongly muffled
- zombie behind wood = audible mids/highs reduced
- footsteps upstairs = ceiling-filtered but directionally readable
- exterior thunder heard from crypt = low-frequency dominant
- open doorway changes sound immediately
- stairwell transmits vertical audio differently from a closed room

This is both horror and gameplay.

## 5.4 Human sounds are more disturbing than monster spam

Verrückt is remembered for environmental human distress:

- drill + scream at the dentist chair
- crying baby / distressed woman around the morgue area
- man screaming/banging in another area
- whispering

The important lesson is not to clone those sounds.

The lesson is: the map can imply victims the player never meets.

For SANCTUM OF ASH, original equivalents can include:

- a single distant confession-like whisper
- someone crying behind a sealed vestry wall
- a heavy object dragged once in the tower
- muffled prayer that cuts off
- one scream from the roof during thunder
- rope tightening sound from the bell chamber
- coughing from below the boiler room
- choir-like breath with no melody

Keep these ambiguous and rare.

---

# 6. Environmental writing must feel like evidence, not UI

Classic World at War used wall writing, chalk, signs, boards, notes and cryptic instructions as part of the map's personality.

Nacht's unfinished HELP is powerful because it implies interruption.

Other famous wall phrases and symbols work because they can function simultaneously as:

- clue
- warning
- lore
- desperation
- misdirection
- instruction
- evidence of another survivor

## Xziel writing rules

Every map should include multiple categories.

### Survivor desperation

- unfinished messages
- crossed-out directions
- names
- tally marks
- warnings
- arrows that may no longer be correct

### Institutional residue

- maintenance signs
- room labels
- evacuation map
- service logs
- old church schedules
- safety notices
- handwritten repair notes

### Research/occult layer

- diagrams
- dates
- repeated numbers
- symbols
- measurements
- strange geometry
- experiments
- annotations over religious or technical documents

### Contradictory evidence

Two notes should sometimes disagree.

That encourages theory-making.

## Placement rule

Never put all writing at eye level on clean walls.

Use:

- low near floor
- behind movable/hidden prop
- partly covered by soot
- above door frame
- inside cabinet
- under stair
- on back of notice board
- on broken glass
- projected onto a surface
- written over an older message
- visible only from a particular angle

---

# 7. Physical horror props

World at War repeatedly uses ordinary objects that become disturbing through context.

Reference functions documented across the original map set include:

- ruined barricades
- crashed aircraft
- dentist chair
- morgue/crematory elements
- hanging body
- blood and handprints
- animal-testing evidence
- radios
- clocks
- chalkboards
- corkboards
- experiment areas
- strange meteor/mineral
- broken industrial equipment
- occult/experimental machinery

Xziel must not copy specific protected models. Recreate the design function with original assets.

For SANCTUM OF ASH:

- broken confession booth
- blood-darkened hymn book
- snapped rosary
- displaced altar cloth
- fallen censer
- rusted maintenance tools
- bell-rope burn marks
- church registry with names crossed out
- cracked funeral photographs
- old service-room lockers
- boiler pressure gauge stuck above redline
- wax-covered floor where candles burned for too long
- damaged stained glass
- collapsed pews forming improvised barricades
- old projector / parish archive film equipment
- medical/emergency supplies abandoned after failed refuge attempt

---

# 8. Horror through implied history

The strongest map details answer no question directly but suggest a sequence of events.

Example pattern:

1. safe place was established;
2. survivors barricaded it;
3. something got inside;
4. people retreated;
5. somebody tried an experiment/ritual;
6. power or machinery failed;
7. final messages stop;
8. player arrives.

For each map, author a hidden pre-player timeline.

The timeline does not need to be shown in order.

Scatter evidence so players reconstruct it.

---

# 9. Story should exist in the environment before it exists in exposition

World at War gradually expanded lore through:

- radios
- hidden transmissions
- wall messages
- notes
- film/projector content
- clocks and numbers
- research spaces
- mysterious objects
- Easter eggs

This makes story discovery player-driven.

## Xziel rule

A player who never searches should still understand:

"I am in a dangerous ruined place and something terrible happened."

A player who explores should discover:

"Specific people did specific things here."

A dedicated community should be able to theorize:

"There may be a larger connection across maps."

All three layers should coexist.

---

# 10. Diegetic media: radios, recordings, projectors

Der Riese's radios/recordings and projector/film-reel style of storytelling are especially useful references.

For Xziel, every major map should have at least one diegetic media system, but the system should fit the location.

SANCTUM OF ASH candidates:

- parish radio receiver
- old tape recorder
- church PA/intercom
- archival film projector
- slide projector
- phonograph
- answering machine in the office
- emergency-service handheld radio
- boiler maintenance voice recorder

The playback object should exist physically in the world.

Some recordings should be partial:

- start with static
- skip
- distort
- end abruptly
- contain background events more important than the speaker

The player should sometimes hear the environment inside the recording: banging, a scream, a bell, gunshots, breathing, footsteps, machinery.

---

# 11. Each map needs its own horror identity

Do not reuse the exact same scary-sound pack and lighting setup everywhere.

## Nacht der Untoten design DNA

Primary emotion: **isolation**.

Ingredients:

- small space
- minimal explanation
- fog
- ruined military architecture
- distant exterior emptiness
- crude wall writing
- blocked windows
- no comfort
- mystery box as the only strange game-like object
- silhouettes appearing beyond barricades
- sense that nobody is coming

Xziel translation:
Use this DNA for compact survival areas and opening rooms.

## Verrückt design DNA

Primary emotion: **human suffering / institutional horror**.

Ingredients:

- asylum architecture
- split team at start
- dark corridors
- medical/torture implication
- disturbing human audio
- power as a major state change
- traps
- super-fast zombies increasing panic
- whispers and cries tied to specific places

Xziel translation:
Use location-specific human history. The horror should feel embedded in rooms.

## Shi No Numa design DNA

Primary emotion: **isolation in hostile nature + strange research**.

Ingredients:

- swamp/jungle
- weather and wet atmosphere
- multiple outbuildings
- hanging body
- radios
- meteor / unexplained material
- mysterious sounds
- hellhounds
- uneven visibility and dangerous exterior paths

Xziel translation:
Exterior horror should use weather, distance and partial visibility rather than only darkness.

## Der Riese design DNA

Primary emotion: **industrial experiment site where the disaster began**.

Ingredients:

- nighttime factory
- machines
- teleportation/experiments
- clocks/numbers
- child-related uncanny sounds
- dog whimper / animal experiment implications
- radios
- notes, chalkboards, corkboards
- hanging body
- Pack-a-Punch / long-term progression
- hidden transmissions
- projector/film elements in later interpretations
- lore that rewards inspection

Xziel translation:
Late-map spaces should feel like the player is reaching the hidden source of the outbreak.

---

# 12. Gameplay and horror must reinforce each other

Atmosphere cannot be detached from mechanics.

## Windows and barricades

Barricades do three jobs:

1. gameplay delay;
2. visual boundary;
3. horror reveal.

A zombie first seen as a silhouette behind boards is more frightening than a zombie simply spawning in a visible room.

Add:

- wood strain sounds before plank removal
- fingers/arms visible through gaps
- dust from impacts
- different break patterns
- occasional exterior lightning behind silhouettes
- no visible spawn-pop

## Doors

Old doors should not just disappear after purchase.

Where engine permits:

- handle movement
- latch click
- hinge creak
- collision-safe opening
- debris shift
- sound propagation change
- new room tone fading in

Do not over-physics doors. Animation should be deterministic and stable.

## Power

Power is progression + audiovisual event + danger.

## Special rounds

Special enemies should temporarily change the soundscape and lighting.

A dog/creature round equivalent should have a recognizable environmental warning before enemies arrive.

## Mystery system

The randomized-weapon mechanic should feel supernatural and risky.

Its sound/light can act as a beacon, but it should also feel out of place in the environment.

---

# 13. Zombie presentation

Early World at War zombies feel threatening because they are not clean, readable theme-park monsters.

Important principles:

- damaged silhouettes
- unpredictable gait variation
- moans and screams at different distances
- sudden runners
- faces not always fully illuminated
- bodies reacting physically to impact
- gore used to support brutality, not comedy
- variation by location / former occupation
- sound before sight in some encounters
- no identical synchronized animation army

Xziel already plans multiple human-created mocap-style zombie animations. Use them to ensure two ordinary walkers can look behaviorally different even when moving at similar speeds.

Desired movement pools:

- slow dragging walk
- stiff military walk
- injured lean
- uneven limping gait
- twitch walk
- head-down wander
- sudden acceleration
- panicked sprint
- shoulder-first barricade pressure
- crawler variants

Avoid animation roulette that destroys gameplay readability. Speed classes must remain readable.

---

# 14. Horror pacing across a match

## Early rounds

- maximum silence
- sparse zombie vocals
- allow player to hear building
- introduce one or two signature ambient sounds
- lighting mostly stable
- teach safe geometry

## Mid rounds

- more environmental machinery active
- more enemy audio
- power changes map
- additional rooms expose stronger horror props
- rare stingers become eligible
- weather can intensify
- more dangerous routes

## Late rounds

Do not simply make ambience louder.

Instead:

- shorter silence windows
- more nearby enemy cues
- occasional environmental failures
- lights can enter alternate state
- supernatural event layers become active
- high-level quest spaces expose deeper lore

Player still needs a clean mix for survival.

---

# 15. "Something happened here" density target

Every major room should contain at least one story detail.

Every major zone should contain:

- one dominant visual motif
- one unique ambient sound family
- one piece of readable history
- one unresolved detail
- one gameplay landmark
- one lighting identity

Not every wall needs clutter.

Negative space is important.

---

# 16. Original SANCTUM OF ASH horror pass

This section directly applies the above DNA to the current church map.

## Fallen Courtyard

Lighting:
- cold moon / storm ambience
- warm leaking window light
- occasional lightning silhouette of tower
- wet ground highlights
- no broad fill light

Audio:
- wind
- rain
- distant thunder
- loose metal/sign
- one extremely rare far-away human scream
- zombie calls beyond walls
- church bell that may ring once before power

Story:
- abandoned emergency barricade
- blood leading toward nave
- parish notice board with evacuation message
- one unfinished chalk warning near entry

Unresolved:
- upstairs window silhouette that can occur once per match

## Nave

Lighting:
- broken stained glass projection
- candle islands
- dark rafters
- occasional lightning through high windows
- altar becomes visual anchor

Audio:
- building creak
- rain on roof
- distant organ resonance
- pew wood stress
- rare breath/whisper near confession area

Story:
- displaced pew barricades
- blood path
- torn hymn pages
- survivor marks
- altar altered after outbreak

Unresolved:
- organ emits one note without player interaction under rare conditions

## Office / corridor

Lighting:
- desk lamp / narrow practical light
- projector beam or archive equipment
- mostly warm decay surrounded by darkness

Audio:
- paper rustle in draft
- old clock
- wall/ceiling movement
- emergency radio static

Story:
- parish registry
- maintenance notes
- photographs
- incomplete incident timeline
- crossed-out names

Unresolved:
- recorder contains a fragment that ends with a noise from behind the speaker

## Boiler room

Lighting:
- red/orange furnace glow
- dark service corners
- steam obscures sightline intermittently
- emergency lamp state changes on power restore

Audio:
- boiler rumble
- pipes
- pressure release
- metal contraction
- low-frequency mechanical resonance

Story:
- evidence people used the room as temporary shelter
- failed repair
- blood on valve/door
- emergency supplies

Unresolved:
- coughing or tapping behind inaccessible wall, extremely rare

## Tower stairs

Lighting:
- narrow pools
- severe vertical shadow
- occasional exterior flash
- moving rope shadow

Audio:
- stair wood/stone
- rope tension
- wind through openings
- footsteps above with no confirmed source

Story:
- dropped tools
- broken lantern
- scratched numbers
- rope burns / drag marks

## Ringing chamber

Lighting:
- bell silhouette
- backlight from openings
- dust in beam
- minimal floor fill

Audio:
- rope
- bell metal settling
- low resonant room tone
- directional impact when bell system activates

Unresolved:
- bell resonance occasionally contains a faint vocal-like tail

## Clock chamber

Lighting:
- moon slices through mechanism
- rotating gear shadow after power
- tiny practical maintenance lamps

Audio:
- ticking
- gear movement
- stressed wood/metal
- distant bell

Story:
- repeated time references
- repair notebook
- deliberate 03:17 clues for Seven Bells quest

## Roof / tower top

Lighting:
- storm becomes dominant
- lightning creates full-scene one-frame reveals
- city/landscape remains mostly dark
- strong silhouette composition

Audio:
- high wind
- thunder
- distant fires
- bell
- occasional far-off siren or human distress if lore supports it

The roof should feel exposed rather than safe.

---

# 17. Ambient-event system specification

Create a reusable map-side ambient event manager.

Each event record should support:

- event id
- audio asset id
- allowed zones
- minimum/maximum distance
- rarity weight
- min cooldown
- global cooldown category
- max plays per match
- round range
- power-state requirement
- quest-state requirement
- weather requirement
- 2D/3D flag
- occlusion enabled
- subtitle/accessibility text when appropriate
- optional visual event id
- optional light event id

Example conceptual events:

- courtyard_far_scream_01
- nave_organ_single_note_01
- office_radio_static_burst_02
- boiler_wall_cough_rare_01
- tower_steps_above_rare_01
- ringing_bell_vocal_tail_ultrarare_01

Rare sounds should never become required gameplay clues unless there is a deterministic accessible equivalent.

---

# 18. Lighting-event system specification

Reusable event types:

- flicker burst
- fixture fail
- power-on sequence
- lightning flash
- swinging-light projection
- projector pulse
- ritual glow
- electrical arc
- candle extinguish
- emergency-light switch

Rules:

- preserve combat readability
- avoid full-screen strobe spam
- avoid rapid flashes that create accessibility problems
- lightning should not erase all enemy silhouettes
- important navigation lighting must remain reliable
- quest-critical cues should have audio or UI/accessibility backup

---

# 19. Environmental-storytelling checklist

Before approving a map, verify:

- Is there evidence of people before the player?
- Is there at least one unfinished action/message?
- Are there signs of failed defense?
- Are there location-specific props?
- Is there at least one unexplained detail?
- Is some lore optional?
- Does the map tell a story without text?
- Do sound and lighting imply activity outside the player's sight?
- Are there details players may discover only after many matches?
- Do repeated playthroughs preserve mystery through variation?

---

# 20. Things NOT to do

- Do not turn horror into constant jumpscares.
- Do not play screams on a predictable timer.
- Do not make every light flicker.
- Do not cover every wall in blood.
- Do not place readable lore everywhere like collectible markers.
- Do not explain every supernatural event.
- Do not use direct Call of Duty/Treyarch ripped audio, textures, models or map assets in the commercial/original Xziel lane.
- Do not make darkness so extreme that mobile players cannot navigate.
- Do not use physics-heavy props that can randomly explode across the map or destabilize gameplay.
- Do not let horror effects obscure critical enemy information.
- Do not copy iconic wall phrases verbatim into final original maps.

Use the technique, not the copyrighted expression.

---

# 21. Acceptance criteria for "real horror"

A map passes the horror review only if all of these are true:

1. Walking the map with no zombies still produces tension.
2. The player can identify the map from its ambient sound alone.
3. At least three rooms have unique room-tone/ambient identities.
4. Silence exists and is intentional.
5. Rare positional events cannot be predicted after one match.
6. Lighting creates silhouettes and depth, not only visibility.
7. Power changes both mechanics and atmosphere.
8. Environmental writing includes both useful and useless/ambiguous material.
9. Lore can be discovered without pausing gameplay for exposition.
10. At least one visual detail can be missed by most players.
11. At least one sound detail can be missed by most players.
12. The map has a coherent pre-player catastrophe timeline.
13. Zombie animation/vocal variation prevents clone-army presentation.
14. The map remains readable on mobile.
15. Nothing essential depends on copyrighted COD asset extraction.

---

# 22. Research evidence captured

## World at War foundation

Activision's Zombies Chronicles retrospective describes:
- Nacht der Untoten as an abandoned airfield overrun by endless undead;
- Verrückt as a German asylum with dark corridors and secrets;
- Shi No Numa as a swamp surrounded by jungle and hellhounds.

Source:
https://blog.activision.com/call-of-duty/archives/almost-ten-years-of-undead-history-comes-together-in-call-of-duty-black-ops-iii-zombies-chronicles

## Environmental-detail density

The World at War Zombies Library catalogs the map set using categories including:
- wall writing
- signs
- corkboards
- pictures, notes and posters
- hanging man
- mysterious sounds
- radio transmissions
- clocks
- chalkboards
- hidden notes
- Dr. Maxis' office
- songs / character quotes

Source:
https://www.callofdutyzombies.com/zombie-library/zombies-library/worldatwar/call-of-duty-world-at-war-zombies-library-overview-interviews-r59/

## Verrückt human-distress audio

Community-documented World at War Verrückt details include:
- dentist-chair interaction producing drill/pain audio;
- crying baby / distressed woman audio near the morgue area;
- screaming/banging;
- strange whispering.

Sources:
https://www.codzombieguides.com/verr%C3%BCckt-remastered
https://zombiesplusworkshop.fandom.com/wiki/Verr%C3%BCckt

These are reference examples only; Xziel should create original equivalents.

## Shi No Numa diegetic radio storytelling

Shi No Numa contains multiple radios/transmissions and uses static / fragmented field communication as environmental storytelling.

Source:
https://www.callofdutyzombies.com/zombie-library/zombies-library/worldatwar/shinonuma/radio-transmissions-r52/

## Der Riese hidden ambient details

Community documentation records:
- children singing near the power area;
- dog whimpering near a teleporter;
- wall writing tied to progression;
- 1:15 clock reference;
- radios / experiment recordings.

Source:
https://callofduty.fandom.com/wiki/Der_Riese/Trivia

The World at War Zombies Library also documents Der Riese wall writing, corkboards, chalkboards, hidden notes, hanging man, clock, office, manual and radio transmissions.

## World at War sound technology

World at War introduced/developed advanced occlusion and distance/reflection behavior so sounds could differ through walls and across vertical spaces, reinforcing spatial awareness.

Source:
https://en.wikipedia.org/wiki/Call_of_Duty%3A_World_at_War

## Direct video target

Primary project-owner reference:
https://youtu.be/6-Mu9VXubeY

Indexed title:
"The horror of Call of Duty: World at War Zombies"

Creator:
Doogle McDuff

---

# 23. Project-level directive

When building or revising any Xziel Zombies map, agents should consult this document before:

- lighting pass
- ambience pass
- prop dressing
- wall-writing / clue pass
- quest/lore pass
- power-system presentation
- environmental animation
- zombie animation/audio variation
- weather
- post-processing
- room acoustics

The goal is not to make every map look like World at War.

The goal is to preserve the design logic that made the old maps frightening:

**darkness + silence + implication + physical place + environmental evidence + rare unexplained events + spatial audio + deliberate light + mystery.**
