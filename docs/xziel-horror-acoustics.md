# Xziel Engine — horror acoustics

Date: 2026-09-20

## Goal

Fear should survive when the player cannot see the threat.

The engine now has a bounded room/portal acoustic graph. Map import/content
authoring can identify rooms and connect them with portals representing doors,
windows, vents, stairwells and openings.

Each portal has:

- openness
- absorption

Each room has:

- reverb preset
- reverb amount
- damping
- occlusion absorption

## Runtime behavior

A source/listener query finds the strongest transmission path through at most
64 rooms and 128 portals.

The result exposes:

- whether an acoustic path exists
- transmission
- occlusion
- low-pass target
- source/listener reverb sends
- listener reverb preset
- portal-hop count

Opening a door can therefore change a zombie sound continuously from muffled
behind a barrier to direct and bright without destroying/restarting the voice.

The existing AudioScenePlanner remains responsible for the finite voice budget.
The acoustic graph supplies environmental propagation parameters.

## Why rooms/portals instead of raycasting every voice

A large horde can contain many simultaneous footsteps and voices. Doing multiple
full collision rays for every voice every audio/control update scales poorly.

Room/portal propagation gives a stable low-cost baseline. A later high-quality
tier can add one or two local geometry rays for the highest-priority nearby
sources and combine them with the room result.

## Real-time audio boundary

The graph is control-plane code. It does not allocate or run inside the audio
callback.

The future Oboe/AAudio mixer consumes already-computed smooth gain/filter/reverb
targets. Android's low-latency audio guidance recommends callbacks and avoiding
blocking work or allocations in the real-time path.

Reference:
https://developer.android.com/games/sdk/oboe/low-latency-audio

## Horror use cases

- zombie growl behind a closed steel door: low-pass + low transmission
- door opens: transmission rises continuously
- stairwell/hall: stronger reverb tail
- outside rain: exterior reverb profile
- sewer/tunnel: long dark reverb character
- power outage: visuals can disappear while directional/muffled audio keeps the
  player's mental model of threat alive
