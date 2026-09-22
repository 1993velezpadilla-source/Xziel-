#include "xziel/horror.hpp"

#include <cassert>

int main() {
    xziel::HorrorConfig config{};
    config.stingerCooldownSeconds = 2.0f;
    config.minimumScareGapSeconds = 0.5f;

    xziel::HorrorDirector director(config);

    xziel::HorrorStimulus calm{};
    for (int i = 0; i < 120; ++i) {
        const auto frame = director.advance(calm, 1.0f / 120.0f);
        assert(frame.tension >= 0.0f && frame.tension <= 1.0f);
        assert(frame.adrenaline >= 0.0f && frame.adrenaline <= 1.0f);
        assert(!frame.requestAudioStinger);
    }

    xziel::HorrorStimulus chase{};
    chase.threatProximity = 1.0f;
    chase.hordePressure = 1.0f;
    chase.recentDamage = 0.8f;
    chase.lowHealthPressure = 0.9f;
    chase.beingChased = true;
    chase.scriptedScareWindow = true;

    bool sawStinger = false;
    for (int i = 0; i < 240; ++i) {
        const auto frame = director.advance(chase, 1.0f / 120.0f);
        sawStinger = sawStinger || frame.requestAudioStinger;
        assert(frame.vignetteStrength <= config.maxVignette + 0.0001f);
        assert(frame.lightFlickerHz <= config.maxFlickerHz + 0.0001f);
        assert(frame.exposureBiasEv >= -config.maxExposureDropEv - 0.0001f);
    }
    assert(sawStinger);

    // Cooldown prevents audio-stinger spam.
    const auto after = director.advance(chase, 1.0f / 120.0f);
    assert(!after.requestAudioStinger);

    // A safe room must pull pressure downward.
    const float beforeSafe = after.tension;
    xziel::HorrorStimulus safe{};
    safe.safeRoom = true;
    for (int i = 0; i < 240; ++i) {
        director.advance(safe, 1.0f / 120.0f);
    }
    assert(director.frame().tension < beforeSafe);

    return 0;
}
