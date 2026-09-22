#include "xziel/quest_runtime.hpp"

#include <cassert>

int main() {
    xziel::QuestDefinition quest{};
    quest.id = 500;
    quest.steps[0] = {
        .id = 1,
        .requiredEvent = xziel::GameplayEventType::PowerStateChanged,
        .subjectId = 10,
        .requiredCount = 1,
    };
    quest.steps[1] = {
        .id = 2,
        .requiredEvent = xziel::GameplayEventType::QuestItemCollected,
        .subjectId = 20,
        .requiredCount = 3,
    };
    quest.steps[2] = {
        .id = 3,
        .requiredEvent = xziel::GameplayEventType::ScriptSignal,
        .subjectId = 99,
        .requiredCount = 1,
    };
    quest.stepCount = 3;

    xziel::QuestRuntime runtime;
    assert(runtime.load(quest));
    assert(runtime.frame().activeStepId == 1);

    auto frame = runtime.consume({
        .type = xziel::GameplayEventType::PowerStateChanged,
        .subjectId = 11,
    });
    assert(frame.activeStepId == 1);

    frame = runtime.consume({
        .type = xziel::GameplayEventType::PowerStateChanged,
        .subjectId = 10,
    });
    assert(frame.stepCompletedThisTick);
    assert(frame.activeStepId == 2);

    frame = runtime.consume({
        .type = xziel::GameplayEventType::QuestItemCollected,
        .subjectId = 20,
        .amount = 2,
    });
    assert(frame.activeStepProgress == 2);
    assert(!frame.stepCompletedThisTick);

    frame = runtime.consume({
        .type = xziel::GameplayEventType::QuestItemCollected,
        .subjectId = 20,
    });
    assert(frame.stepCompletedThisTick);
    assert(frame.activeStepId == 3);

    frame = runtime.consume({
        .type = xziel::GameplayEventType::ScriptSignal,
        .subjectId = 99,
    });
    assert(frame.completed);
    assert(frame.questCompletedThisTick);

    return 0;
}
