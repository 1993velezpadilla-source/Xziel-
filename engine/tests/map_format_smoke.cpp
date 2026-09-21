#include "xziel/map_format.hpp"

#include <cassert>
#include <string_view>

int main() {
    constexpr std::string_view mapText = R"MAP(
# Minimal authored Xziel map
xziel_map 1
box 1 0 -1.58 0 3.15 0.09 3.75 0 1 0 0
box 2 0 -0.30 0 0.58 1.27 0.60 1 0 1 1
door 100 750 0 -0.8 -1.6 1.0 0.8 1.0 1.2 0 -0.4 0.9 1.75 0.1 1.2 0.15
window 200 -0.7 -1.6 2.0 0.7 0.9 2.2 6 0.9 0.68 10 60 0 -0.2 1.9 1.5 0.1 1.1
interaction 300 switch -1 -0.3 0 1.4 0.2 1 0.25 0 1
interaction 301 weapon 1 -0.3 0 1.4 0.2 1 0.20 500 1
)MAP";

    xziel::MapDefinition map{};
    xziel::MapParseError error{};

    assert(
        xziel::parseMapText(
            mapText,
            map,
            error));

    assert(error.code == xziel::MapParseErrorCode::None);
    assert(map.boxCount == 2);
    assert(map.doorCount == 1);
    assert(map.windowCount == 1);
    assert(map.interactionCount == 2);
    assert(map.doors[0].door.cost == 750);
    assert(map.windows[0].window.barricade.maximumPlanks == 6);
    assert(
        map.interactions[1].kind ==
        xziel::InteractionKind::WeaponBuy);

    constexpr std::string_view invalid = R"MAP(
xziel_map 2
)MAP";

    assert(
        !xziel::parseMapText(
            invalid,
            map,
            error));

    assert(
        error.code ==
        xziel::MapParseErrorCode::UnsupportedVersion);

    return 0;
}
