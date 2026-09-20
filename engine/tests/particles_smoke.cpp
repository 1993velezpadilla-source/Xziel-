#include "xziel/particles.hpp"

#include <array>
#include <cassert>

int main() {
    xziel::ParticleEmitterConfig rain{};
    rain.kind = xziel::ParticleKind::Rain;
    rain.origin = {0.0f, 8.0f, 0.0f};
    rain.halfExtents = {5.0f, 0.5f, 5.0f};
    rain.baseVelocity = {0.0f, -12.0f, 0.0f};
    rain.particlesPerSecond = 240.0f;
    rain.lifetimeMinSeconds = 0.4f;
    rain.lifetimeMaxSeconds = 0.8f;
    rain.maxAlive = 128;
    rain.spawnDistanceMeters = 25.0f;
    rain.fadeStartDistanceMeters = 18.0f;

    xziel::ParticleEmitter emitter(rain, 128);

    xziel::ParticleSpawnContext context{};
    context.cameraPosition = {0.0f, 1.7f, 0.0f};
    context.windVelocity = {1.5f, 0.0f, 0.2f};

    std::uint32_t peakAlive = 0;
    for (int i = 0; i < 240; ++i) {
        const auto stats = emitter.advance(context, 1.0f / 120.0f);
        peakAlive = stats.alive > peakAlive ? stats.alive : peakAlive;
        assert(stats.alive <= 128);
    }

    assert(peakAlive > 0);

    std::array<xziel::ParticleRenderItem, 128> renderItems{};
    const auto count = emitter.buildRenderItems(
        context.cameraPosition,
        renderItems.data(),
        renderItems.size());
    assert(count <= renderItems.size());

    // Off-distance emitters stop spawning but existing particles can retire.
    context.cameraPosition = {1000.0f, 1000.0f, 1000.0f};
    const auto culled = emitter.advance(context, 1.0f / 60.0f);
    assert(culled.culledEmitters == 1);

    // Giant frame deltas are clamped, preventing spawn explosions.
    context.cameraPosition = {0.0f, 1.7f, 0.0f};
    const auto stalled = emitter.advance(context, 10.0f);
    assert(stalled.spawnedThisFrame <= 32);

    return 0;
}
