#include "xziel/door.hpp"

#include <cassert>

int main() {
    xziel::HordeDirector horde;
    xziel::ScoreSystem score({.startingPoints = 1000});
    xziel::DoorSystem doors;

    assert(doors.addDoor(
        {
            .id = 201,
            .blocker = {
                .minimum = {-0.8f, -1.6f, 0.2f},
                .maximum = { 0.8f,  1.2f, 0.5f},
            },
            .cost = 750,
        },
        horde));

    auto frame = doors.activate(201, horde, score);
    assert(frame.open);
    assert(frame.openedThisTick);
    assert(score.frame().total == 250);

    frame = doors.activate(201, horde, score);
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
        horde));
    frame = doors.activate(202, horde, poor);
    assert(!frame.open);
    assert(frame.insufficientFundsThisTick);
    assert(poor.frame().total == 100);

    return 0;
}
