#include "xziel/gameplay_events.hpp"

#include <cassert>

int main() {
    xziel::GameplayEventQueue queue;

    assert(queue.push({
        .type = xziel::GameplayEventType::DoorOpened,
        .subjectId = 7,
        .simulationTick = 100,
    }));
    assert(queue.push({
        .type = xziel::GameplayEventType::ZombieKilled,
        .subjectId = 9,
        .amount = 1,
        .simulationTick = 101,
    }));
    assert(queue.size() == 2);

    xziel::GameplayEvent event{};
    assert(queue.pop(event));
    assert(event.type == xziel::GameplayEventType::DoorOpened);
    assert(event.subjectId == 7);
    assert(queue.pop(event));
    assert(event.type == xziel::GameplayEventType::ZombieKilled);
    assert(queue.empty());

    for (std::size_t i = 0; i < xziel::kGameplayEventCapacity; ++i) {
        assert(queue.push({
            .type = xziel::GameplayEventType::ScriptSignal,
            .subjectId = static_cast<std::uint32_t>(i + 1),
        }));
    }
    assert(!queue.push({
        .type = xziel::GameplayEventType::ScriptSignal,
        .subjectId = 999,
    }));
    assert(queue.droppedCount() == 1);

    return 0;
}
