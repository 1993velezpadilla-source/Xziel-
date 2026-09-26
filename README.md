# XZIEL Engine

XZIEL Engine is the current native/mobile engine project.

It is intentionally named and packaged separately from the earlier Quake/NZ:P prototype so both can coexist without being confused. The current Android application id is `com.xziel.engine`.

The Android build still uses SDL2, Vril and selected NZ:P compatibility/gameplay code as an upstream compatibility layer while XZIEL-owned rendering, runtime, map and gameplay systems replace the legacy paths incrementally.

## Current target

- Android arm64-v8a first
- XZIEL-owned modern rendering/runtime path
- Native SDL2 platform layer
- Mobile touch controls and gyroscope
- Offline bundled game data
- Reusable map runtime contracts, including Nacht reference systems
- GitHub Actions APK builds

Upstream projects and their licenses/attribution remain preserved where compatibility code is used.
