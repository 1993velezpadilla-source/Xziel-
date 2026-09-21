#include "xziel/score.hpp"

#include <cassert>

int main() {
    {
        xziel::ScoreConfig startingConfig{};
        startingConfig.startingPoints = 500U;

        xziel::ScoreSystem startingScore(
            startingConfig);

        assert(
            startingScore.frame().total ==
            500U);

        assert(
            startingScore.trySpend(
                500U));

        assert(
            startingScore.frame().total ==
            0U);
    }

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

    const auto beforeSpend =
        score.frame().total;

    assert(
        score.trySpend(50U));

    assert(
        score.frame().total ==
        beforeSpend - 50U);

    assert(
        score.frame().spentThisTick);

    assert(
        score.frame().lastSpend ==
        50U);

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

    score.reset();

    assert(
        score.frame().total == 0U);

    assert(
        !score.frame().spentThisTick);

    const auto beforeUtility = score.frame().total;
    auto utility = score.awardUtility(10);
    assert(utility.total == beforeUtility + 10);
    assert(utility.lastAward == 10);
    assert(utility.changedThisTick);
    assert(!utility.criticalAwardThisTick);

    return 0;
}
