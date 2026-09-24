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

    constexpr std::string_view nativeMap = R"MAP(
xziel_map 2
player_spawn 12.5 -1.58 -8.25 37.0
arena -42.0 41.0 -38.0 44.0
floor 1000 -5.0 -1.78 -5.0 5.0 -1.58 5.0
zombie_spawn -12.0 -1.58 6.0
zombie_spawn 14.0 -1.58 9.0
box 10 0 -1.70 0 30 0.10 25 0 0 1 1
)MAP";

    assert(
        xziel::parseMapText(
            nativeMap,
            map,
            error));
    assert(map.hasPlayerSpawn);
    assert(map.playerSpawnFeet.x == 12.5f);
    assert(map.playerSpawnFeet.y == -1.58f);
    assert(map.playerSpawnYawDegrees == 37.0f);
    assert(map.hasArenaBounds);
    assert(map.floorCount == 1);
    assert(map.floors[0].id == 1000U);
    assert(map.floors[0].bounds.maximum.y == -1.58f);
    assert(map.arenaMinimumX == -42.0f);
    assert(map.arenaMaximumZ == 44.0f);
    assert(map.zombieSpawnCount == 2);
    assert(map.zombieSpawns[1].x == 14.0f);

    constexpr std::string_view lightingMap = R"MAP(
xziel_map 3
player_spawn 0 -1.58 0 0
arena -12 12 -14 14
light 9001 point 0 2.5 1 0 -1 0 1 0.35 0.08 7.5 8.0 24 42 1.25 0.25 1.8 1 1 1
light 9002 spot 3 3 -4 -0.2 -0.8 0.4 0.16 0.28 0.9 9.0 12.0 18 36 1.0 0.0 0.0 1 1 1
)MAP";

    assert(
        xziel::parseMapText(
            lightingMap,
            map,
            error));
    assert(map.lightCount == 2U);
    assert(map.lights[0].id == 9001U);
    assert(map.lights[0].type == xziel::MapLightType::Point);
    assert(map.lights[0].castsShadows);
    assert(map.lights[0].volumetric);
    assert(map.lights[1].type == xziel::MapLightType::Spot);
    assert(map.lights[1].innerConeDegrees == 18.0f);
    assert(map.lights[1].outerConeDegrees == 36.0f);

    constexpr std::string_view invalid = R"MAP(
xziel_map 4
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
