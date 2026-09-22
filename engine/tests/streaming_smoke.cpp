#include "xziel/streaming.hpp"

#include <array>
#include <cassert>

int main() {
    xziel::ResidencyManager manager(8);

    assert(manager.registerResource(
        {.id = 1, .kind = xziel::StreamResourceKind::Texture, .bytes = 64, .pinned = true},
        1));
    assert(manager.registerResource(
        {.id = 2, .kind = xziel::StreamResourceKind::Texture, .bytes = 128},
        2));
    assert(manager.registerResource(
        {.id = 3, .kind = xziel::StreamResourceKind::Mesh, .bytes = 96},
        20));
    assert(manager.registerResource(
        {.id = 4, .kind = xziel::StreamResourceKind::AudioBank, .bytes = 80},
        3));

    const auto before = manager.stats();
    assert(before.residentCount == 4);
    assert(before.textureBytes == 192);

    std::array<xziel::EvictionCandidate, 4> evictions{};
    const auto count = manager.planEvictions(
        160,
        100,
        10,
        evictions.data(),
        evictions.size());

    assert(count >= 2);

    // Resource 1 is pinned and may never be selected.
    for (std::size_t i = 0; i < count; ++i) {
        assert(evictions[i].id != 1);
        manager.setResident(evictions[i].id, false, 100);
    }

    const auto after = manager.stats();
    assert(after.residentCount < before.residentCount);

    return 0;
}
