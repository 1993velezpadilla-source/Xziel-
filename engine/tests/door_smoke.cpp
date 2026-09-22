#include "xziel/door.hpp"

#include <cassert>

int main() {
    xziel::HordeDirector horde;
    xziel::ScoreSystem score({.startingPoints = 1000});
    xziel::FpsPlayerController player;
    xziel::DoorSystem doors;

    assert(doors.addDoor(
        {
            .id = 201,
            .blocker = {
                .minimum = {-0.8f, -1.6f, 0.2f},
                .maximum = { 0.8f,  1.2f, 0.5f},
            },
            .cost = 750,
            .openDurationSeconds = 1.0f,
            .collisionReleaseProgress = 0.60f,
        },
        horde,
        player));

    auto frame = doors.activate(201, horde, player, score);
    assert(!frame.open);
    assert(frame.opening);
    assert(frame.openedThisTick);
    assert(!frame.collisionReleased);
    assert(frame.openProgress == 0.0f);
    assert(score.frame().total == 250);

    for (int i = 0; i < 50; ++i) {
        doors.step(0.01f, horde, player);
    }
    frame = *doors.frame(201);
    assert(!frame.open);
    assert(frame.opening);
    assert(!frame.collisionReleased);
    assert(frame.openProgress > 0.49f && frame.openProgress < 0.51f);

    for (int i = 0; i < 15; ++i) {
        doors.step(0.01f, horde, player);
    }
    frame = *doors.frame(201);
    assert(frame.collisionReleased);
    assert(!frame.open);

    for (int i = 0; i < 40; ++i) {
        doors.step(0.01f, horde, player);
    }
    frame = *doors.frame(201);
    assert(frame.open);
    assert(!frame.opening);
    assert(frame.collisionReleased);
    assert(frame.openProgress == 1.0f);

    frame = doors.activate(201, horde, player, score);
    assert(frame.open);
    assert(!frame.openedThisTick);
    assert(score.frame().total == 250);

    xziel::ScoreSystem poor({.startingPoints = 100});
    assert(doors.addDoor(
        {
            .id = 202,
            .blocker = {
                .minimum = {1.0f, -1.6f, 0.2f},
                .maximum = {1.5f,  1.2f, 0.5f},
            },
            .cost = 500,
        },
        horde,
        player));

    frame = doors.activate(202, horde, player, poor);
    assert(!frame.open);
    assert(!frame.opening);
    assert(frame.insufficientFundsThisTick);
    assert(poor.frame().total == 100);

    return 0;
}
