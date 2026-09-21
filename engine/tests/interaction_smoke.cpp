#include "xziel/interaction.hpp"

#include <cassert>

int main() {
    xziel::InteractionSystem interactions;

    assert(
        interactions.addTarget(
            {
                .id = 1,
                .kind =
                    xziel::InteractionKind::Door,
                .position = {
                    0.0f,
                    0.0f,
                    1.0f,
                },
                .maximumDistance = 2.0f,
                .minimumFacingDot = 0.4f,
                .priority = 1.0f,
                .holdSeconds = 0.0f,
                .cost = 500,
            }));

    assert(
        interactions.addTarget(
            {
                .id = 2,
                .kind =
                    xziel::InteractionKind::Switch,
                .position = {
                    0.2f,
                    0.0f,
                    1.2f,
                },
                .maximumDistance = 2.0f,
                .minimumFacingDot = 0.3f,
                .priority = 2.0f,
                .holdSeconds = 0.20f,
            }));

    auto frame =
        interactions.step(
            {},
            {0.0f, 0.0f, 1.0f},
            {},
            1.0f / 120.0f);

    assert(frame.promptVisible);
    assert(frame.targetId == 2U);
    assert(!frame.activatedThisTick);

    for (int i = 0;
         i < 30;
         ++i) {
        frame =
            interactions.step(
                {},
                {0.0f, 0.0f, 1.0f},
                {
                    .held = true,
                },
                1.0f / 120.0f);
    }

    assert(frame.activatedThisTick);
    assert(frame.holdAlpha >= 0.99f);

    // Holding after activation is latched; release is required before a second
    // activation can happen.
    frame =
        interactions.step(
            {},
            {0.0f, 0.0f, 1.0f},
            {
                .held = true,
            },
            1.0f / 120.0f);

    assert(!frame.activatedThisTick);

    (void) interactions.step(
        {},
        {0.0f, 0.0f, 1.0f},
        {},
        1.0f / 120.0f);

    bool activatedAgain = false;

    for (int i = 0;
         i < 30;
         ++i) {
        frame =
            interactions.step(
                {},
                {0.0f, 0.0f, 1.0f},
                {
                    .held = true,
                },
                1.0f / 120.0f);

        activatedAgain =
            activatedAgain ||
            frame.activatedThisTick;
    }

    assert(activatedAgain);

    return 0;
}
