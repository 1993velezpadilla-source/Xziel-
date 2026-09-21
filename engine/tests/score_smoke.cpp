#include "xziel/score.hpp"

#include <cassert>

int main() {
    xziel::ScoreSystem score;

    auto frame =
        score.awardHit(
            xziel::ZombieHitRegion::Torso,
            false);

    assert(frame.total == 10U);
    assert(frame.lastAward == 10U);

    frame =
        score.awardHit(
            xziel::ZombieHitRegion::Head,
            true);

    assert(frame.total == 130U);
    assert(frame.lastAward == 120U);
    assert(frame.criticalAwardThisTick);

    frame =
        score.awardRoundClear(3);

    assert(frame.total == 275U);
    assert(frame.lastAward == 145U);
    assert(!frame.criticalAwardThisTick);

    score.reset();
    assert(score.frame().total == 0U);

    const auto beforeSpend =
        score.frame().total;

    assert(
        score.trySpend(50U));

    assert(
        score.frame().total ==
        beforeSpend - 50U);

    assert(
        score.frame().spentThisTick);

    const auto afterSpend =
        score.frame().total;

    assert(
        !score.trySpend(
            0xFFFFFFFFU));

    assert(
        score.frame().total ==
        afterSpend);

    assert(
        score.frame().
            insufficientFundsThisTick);

    return 0;
}
