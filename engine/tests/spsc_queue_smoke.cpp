#include "xziel/spsc_queue.hpp"

#include <cassert>
#include <cstdint>

struct Command {
    std::uint32_t type = 0;
    std::uint32_t value = 0;
};

int main() {
    xziel::SpscQueue<Command, 8> queue;

    assert(queue.empty());
    assert(queue.usableCapacity() == 7);

    for (std::uint32_t i = 0; i < 7; ++i) {
        assert(queue.tryPush({
            .type = 1,
            .value = i,
        }));
    }

    // Bounded queue refuses overflow rather than allocating or blocking.
    assert(!queue.tryPush({
        .type = 1,
        .value = 99,
    }));

    for (std::uint32_t i = 0; i < 7; ++i) {
        Command command{};
        assert(queue.tryPop(command));
        assert(command.value == i);
    }

    assert(queue.empty());

    Command command{};
    assert(!queue.tryPop(command));

    return 0;
}
