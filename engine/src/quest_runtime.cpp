#include "xziel/quest_runtime.hpp"

#include <algorithm>

namespace xziel {

void QuestRuntime::reset() noexcept {
    definition_ = {};
    frame_ = {};
    stepProgress_ = 0;
}

bool QuestRuntime::load(
    const QuestDefinition& definition) noexcept {
    reset();

    if (definition.id == 0U ||
        definition.stepCount == 0 ||
        definition.stepCount > definition.steps.size()) {
        return false;
    }

    for (std::size_t i = 0; i < definition.stepCount; ++i) {
        const auto& step = definition.steps[i];
        if (step.id == 0U ||
            step.requiredEvent == GameplayEventType::None ||
            step.requiredCount == 0U) {
            reset();
            return false;
        }

        for (std::size_t previous = 0; previous < i; ++previous) {
            if (definition.steps[previous].id == step.id) {
                reset();
                return false;
            }
        }
    }

    definition_ = definition;
    frame_.loaded = true;
    frame_.questId = definition.id;
    refreshFrame();
    return true;
}

QuestFrame QuestRuntime::consume(
    const GameplayEvent& event) noexcept {
    frame_.stepCompletedThisTick = false;
    frame_.questCompletedThisTick = false;

    if (!frame_.loaded || frame_.completed ||
        frame_.activeStepIndex >= definition_.stepCount) {
        return frame_;
    }

    const auto& step =
        definition_.steps[frame_.activeStepIndex];

    const bool subjectMatches =
        step.subjectId == 0U ||
        step.subjectId == event.subjectId;

    if (event.type != step.requiredEvent ||
        !subjectMatches) {
        return frame_;
    }

    const std::uint32_t increment =
        std::max(event.amount, 1U);

    stepProgress_ =
        stepProgress_ > UINT32_MAX - increment
        ? UINT32_MAX
        : stepProgress_ + increment;

    if (stepProgress_ < step.requiredCount) {
        refreshFrame();
        return frame_;
    }

    frame_.stepCompletedThisTick = true;
    ++frame_.activeStepIndex;
    stepProgress_ = 0U;

    if (frame_.activeStepIndex >= definition_.stepCount) {
        frame_.completed = true;
        frame_.questCompletedThisTick = true;
        frame_.activeStepId = 0U;
        frame_.activeStepProgress = 0U;
        frame_.activeStepRequired = 0U;
        return frame_;
    }

    refreshFrame();
    return frame_;
}

const QuestFrame& QuestRuntime::frame() const noexcept {
    return frame_;
}

void QuestRuntime::refreshFrame() noexcept {
    if (!frame_.loaded ||
        frame_.activeStepIndex >= definition_.stepCount) {
        return;
    }

    const auto& step =
        definition_.steps[frame_.activeStepIndex];

    frame_.activeStepId = step.id;
    frame_.activeStepProgress = stepProgress_;
    frame_.activeStepRequired = step.requiredCount;
}

} // namespace xziel
