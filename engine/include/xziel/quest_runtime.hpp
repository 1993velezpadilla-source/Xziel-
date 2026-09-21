#pragma once

#include "xziel/gameplay_events.hpp"

#include <array>
#include <cstddef>
#include <cstdint>

namespace xziel {

inline constexpr std::size_t kMaxQuestSteps = 32;

struct QuestStepDefinition {
    std::uint32_t id = 0;
    GameplayEventType requiredEvent = GameplayEventType::ScriptSignal;

    // Zero means any subject. Non-zero binds the step to a specific authored
    // switch, door, pickup, boss, window, etc.
    std::uint32_t subjectId = 0;

    std::uint32_t requiredCount = 1;
};

struct QuestDefinition {
    std::uint32_t id = 0;
    std::array<QuestStepDefinition, kMaxQuestSteps> steps{};
    std::size_t stepCount = 0;
};

struct QuestFrame {
    std::uint32_t questId = 0;
    std::uint32_t activeStepId = 0;
    std::size_t activeStepIndex = 0;
    std::uint32_t activeStepProgress = 0;
    std::uint32_t activeStepRequired = 0;

    bool loaded = false;
    bool completed = false;
    bool stepCompletedThisTick = false;
    bool questCompletedThisTick = false;
};

class QuestRuntime final {
public:
    void reset() noexcept;

    [[nodiscard]] bool load(
        const QuestDefinition& definition) noexcept;

    [[nodiscard]] QuestFrame consume(
        const GameplayEvent& event) noexcept;

    [[nodiscard]] const QuestFrame& frame() const noexcept;

private:
    void refreshFrame() noexcept;

    QuestDefinition definition_{};
    QuestFrame frame_{};
    std::uint32_t stepProgress_ = 0;
};

} // namespace xziel
