#include "xziel/audio_scene.hpp"

#include <array>
#include <cassert>

int main() {
    std::array<xziel::AudioSource, 6> sources{{
        {
            .id = 1,
            .kind = xziel::AudioSourceKind::PlayerWeapon,
            .distanceMeters = 0.0f,
            .baseGain = 1.0f,
            .importance = 1.0f,
            .critical = true,
        },
        {
            .id = 2,
            .kind = xziel::AudioSourceKind::ZombieVoice,
            .distanceMeters = 2.0f,
            .baseGain = 1.0f,
            .importance = 1.0f,
            .occlusion = 0.6f,
        },
        {
            .id = 3,
            .kind = xziel::AudioSourceKind::Ambience,
            .distanceMeters = 5.0f,
            .baseGain = 0.8f,
            .importance = 0.5f,
            .looping = true,
        },
        {
            .id = 4,
            .kind = xziel::AudioSourceKind::HorrorStinger,
            .distanceMeters = 0.0f,
            .baseGain = 1.0f,
            .importance = 1.0f,
            .critical = true,
        },
        {
            .id = 5,
            .kind = xziel::AudioSourceKind::ZombieFootstep,
            .distanceMeters = 18.0f,
            .baseGain = 0.9f,
            .importance = 0.8f,
        },
        {
            .id = 6,
            .kind = xziel::AudioSourceKind::Environment,
            .distanceMeters = 28.0f,
            .baseGain = 0.5f,
            .importance = 0.3f,
            .looping = true,
        },
    }};

    xziel::RenderWorkload workload{};
    workload.quality = xziel::RenderQuality::Low;

    std::array<xziel::AudioVoiceDecision, 6> decisions{};
    xziel::AudioScenePlanner planner;
    const auto count = planner.plan(
        sources.data(),
        sources.size(),
        workload,
        decisions.data(),
        decisions.size());

    assert(count == sources.size());

    bool weaponAudible = false;
    bool stingerAudible = false;
    bool occludedFiltered = false;

    for (const auto& decision : decisions) {
        if (decision.id == 1) {
            weaponAudible = decision.audible;
        }
        if (decision.id == 4) {
            stingerAudible = decision.audible;
        }
        if (decision.id == 2) {
            occludedFiltered = decision.lowPassHz < 20000.0f;
        }
    }

    assert(weaponAudible);
    assert(stingerAudible);
    assert(occludedFiltered);

    return 0;
}
