#include "xziel/frame_graph.hpp"

#include <cassert>

int main() {
    xziel::FrameGraph graph;

    // slot 0 scene color, slot 1 reflection temp, slot 2 bloom temp,
    // slot 3 external swapchain.
    assert(graph.addResource({
        .id = 1,
        .bytes = 8 * 1024 * 1024,
        .transient = true,
    }));
    assert(graph.addResource({
        .id = 2,
        .bytes = 4 * 1024 * 1024,
        .transient = true,
    }));
    assert(graph.addResource({
        .id = 3,
        .bytes = 4 * 1024 * 1024,
        .transient = true,
    }));
    assert(graph.addResource({
        .id = 4,
        .bytes = 8 * 1024 * 1024,
        .transient = false,
        .external = true,
    }));

    // Reflection temp is used and dies before bloom temp begins, allowing alias.
    assert(graph.addPass({
        .id = 10,
        .writes = 1ULL << 1,
    }));
    assert(graph.addPass({
        .id = 11,
        .reads = 1ULL << 1,
        .writes = 1ULL << 0,
    }));
    assert(graph.addPass({
        .id = 12,
        .reads = 1ULL << 0,
        .writes = 1ULL << 2,
    }));
    assert(graph.addPass({
        .id = 13,
        .reads = (1ULL << 0) | (1ULL << 2),
        .writes = 1ULL << 3,
    }));

    const auto compiled = graph.compile();
    assert(compiled.valid);
    assert(!compiled.readBeforeWrite);
    assert(compiled.enabledPassCount == 4);
    assert(compiled.usedResourceCount == 4);
    assert(compiled.aliasedTransientBytes <
           compiled.unaliasedTransientBytes);

    // Non-external read-before-write must be rejected.
    xziel::FrameGraph bad;
    assert(bad.addResource({
        .id = 1,
        .bytes = 1024,
        .transient = true,
    }));
    assert(bad.addPass({
        .id = 1,
        .reads = 1ULL,
    }));
    assert(!bad.compile().valid);

    return 0;
}
