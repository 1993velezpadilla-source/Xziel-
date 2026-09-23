#include "xziel/sanctum_immersion.hpp"

#include <algorithm>
#include <cassert>
#include <cmath>

int main() {
    {
        xziel::DoorFrame previous{};
        previous.id = 7;

        xziel::DoorFrame current = previous;
        current.opening = true;
        current.openedThisTick = true;

        auto event =
            xziel::SanctumSoundEventRouter::door(
                previous,
                current);
        assert(event.valid());
        assert(
            event.cue ==
            xziel::SanctumSoundCue::DoorWoodOpenStart);

        previous = current;
        previous.openedThisTick = false;
        previous.openProgress = 0.40f;
        current = previous;
        current.openProgress = 0.50f;

        event =
            xziel::SanctumSoundEventRouter::door(
                previous,
                current);
        assert(
            event.cue ==
            xziel::SanctumSoundCue::DoorWoodCreak);
    }

    {
        xziel::BarricadeFrame previous{};
        previous.intactPlanks = 3;

        xziel::BarricadeFrame current = previous;
        current.intactPlanks = 2;
        current.plankRemovedThisTick = true;

        const auto event =
            xziel::SanctumSoundEventRouter::barricade(
                19,
                previous,
                current);
        assert(
            event.cue ==
            xziel::SanctumSoundCue::BarricadePlankRip);
    }

    {
        const auto dry =
            xziel::SanctumSoundEventRouter::footstep(
                1,
                xziel::SanctumSurface::Wood,
                false);
        const auto wet =
            xziel::SanctumSoundEventRouter::footstep(
                1,
                xziel::SanctumSurface::WetWood,
                true);

        assert(
            dry.cue ==
            xziel::SanctumSoundCue::FootstepWood);
        assert(
            wet.cue ==
            xziel::SanctumSoundCue::FootstepWetWood);
        assert(wet.gain > dry.gain);
    }

    {
        xziel::ThunderAudioScheduler thunder;
        thunder.schedule(55, 100.0f);
        assert(thunder.pending());

        auto event = thunder.advance(0.10f);
        assert(!event.valid());

        event = thunder.advance(0.10f);
        assert(!event.valid());

        event = thunder.advance(0.10f);
        assert(event.valid());
        assert(
            event.cue ==
            xziel::SanctumSoundCue::ThunderMid);
        assert(!thunder.pending());
    }

    {
        xziel::WindowAtmosphereSystem window;
        bool heardRattle = false;
        bool heardCreak = false;
        float maximumAngle = 0.0f;

        for (int i = 0; i < 400; ++i) {
            const auto frame =
                window.advance(
                    {12.0f, 0.0f, 2.0f},
                    0.025f);
            maximumAngle =
                std::max(
                    maximumAngle,
                    std::fabs(frame.angleDegrees));
            heardRattle =
                heardRattle || frame.rattleThisTick;
            heardCreak =
                heardCreak || frame.creakThisTick;
        }

        assert(maximumAngle > 1.0f);
        assert(heardRattle);
        assert(heardCreak);
    }

    return 0;
}
