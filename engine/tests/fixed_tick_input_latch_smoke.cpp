#include "xziel/fixed_tick_input_latch.hpp"

#include <cassert>

int main() {
    xziel::FixedTickInputPulseLatch latch;

    assert(!latch.any());

    latch.capture({
        .fire = true,
        .jump = true,
    });

    assert(latch.any());
    assert(latch.pending().fire);
    assert(latch.pending().jump);
    assert(!latch.pending().reload);

    // A render frame with zero fixed ticks performs no acknowledge. Capturing
    // later input must preserve the earlier tap instead of replacing it.
    latch.capture({
        .reload = true,
    });

    assert(latch.pending().fire);
    assert(latch.pending().jump);
    assert(latch.pending().reload);

    // The first frame that actually advances fixed simulation consumes the
    // complete accumulated pulse set exactly once.
    latch.acknowledge();

    assert(!latch.any());
    assert(!latch.pending().fire);
    assert(!latch.pending().jump);
    assert(!latch.pending().reload);

    latch.capture({
        .interact = true,
        .stance = true,
    });

    assert(latch.pending().interact);
    assert(latch.pending().stance);

    latch.reset();

    assert(!latch.any());

    return 0;
}
