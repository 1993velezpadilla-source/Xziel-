#include "xziel/nacht_reference.hpp"

#include <array>
#include <cassert>
#include <cstddef>
#include <string_view>

int main() {
    const auto& profile =
        xziel::nachtReferenceProfile();

    assert(profile.zombieSpawns.size() == 21U);
    assert(profile.purchases.size() == 9U);
    assert(profile.doors.size() == 3U);

    std::size_t start = 0;
    std::size_t box = 0;
    std::size_t upstairs = 0;

    for (const auto& spawn :
         profile.zombieSpawns) {
        switch (spawn.zone) {
            case xziel::NachtZone::Start:
                ++start;
                break;
            case xziel::NachtZone::Box:
                ++box;
                break;
            case xziel::NachtZone::Upstairs:
                ++upstairs;
                break;
        }
    }

    assert(start == 10U);
    assert(box == 5U);
    assert(upstairs == 6U);

    assert(
        profile.purchases[0].displayName ==
        std::string_view("KN-44"));
    assert(profile.purchases[0].price == 1400U);
    assert(profile.purchases[1].price == 1100U);
    assert(profile.purchases[2].price == 250U);
    assert(profile.purchases[3].price == 750U);
    assert(profile.purchases[4].price == 1250U);
    assert(profile.purchases[5].price == 5000U);
    assert(profile.purchases[6].price == 700U);
    assert(profile.purchases[7].price == 500U);
    assert(profile.purchases[8].price == 500U);

    assert(profile.doors[0].price == 1000U);
    assert(profile.doors[1].price == 1000U);
    assert(profile.doors[2].price == 1000U);

    const auto startConfig =
        xziel::makeNachtHordeConfig();

    assert(startConfig.spawnPointCount == 10U);
    assert(startConfig.maxActive == 24U);

    const auto allConfig =
        xziel::makeNachtHordeConfig(
            xziel::kNachtAllZonesMask);

    assert(allConfig.spawnPointCount == 21U);

    xziel::HordeDirector horde(
        startConfig);

    std::array<xziel::Vec3, 21> allPoints{};
    const std::size_t allCount =
        xziel::collectNachtSpawnPoints(
            xziel::kNachtAllZonesMask,
            allPoints);

    assert(allCount == 21U);

    assert(
        horde.replaceSpawnPoints(
            std::span<const xziel::Vec3>(
                allPoints.data(),
                allCount)));

    assert(
        horde.config().spawnPointCount ==
        21U);

    return 0;
}
