#include "xziel/nacht_reference.hpp"

#include <algorithm>

namespace xziel {

namespace {

// Persisted metadata source:
// experiments/bo3_nacht_reference/xziel_reference_package
// Purchase calibration: 3 authored anchors + 6 geometry-derived slots,
// RMSE 3.642585764715487 cm.
//
// The package stores XZIEL coordinates as X(horizontal), Y(horizontal),
// Z(up). The native engine uses X(horizontal), Y(up), Z(horizontal), so each
// position below is {package.x, package.z, package.y}.

constexpr NachtReferenceProfile kProfile{
    .zombieSpawns = {{
        {"zspawn_zombiespawner10", {12.877046f, 0.001000f, -2.727291f}, NachtZone::Start, true, true},
        {"zspawn_zombiespawner11", {14.172050f, 0.125601f, 6.879191f}, NachtZone::Box, false, true},
        {"zspawn_zombiespawner12", {20.629141f, 0.168620f, 10.613967f}, NachtZone::Box, false, true},
        {"zspawn_zombiespawner13", {15.286886f, -0.120566f, 33.425278f}, NachtZone::Box, false, false},
        {"zspawn_zombiespawner14", {38.909851f, -0.648941f, 15.198732f}, NachtZone::Box, false, true},
        {"zspawn_zombiespawner15", {37.457021f, -0.498080f, 16.985983f}, NachtZone::Box, false, true},
        {"zspawn_zombiespawner16", {14.516221f, -0.038027f, -0.836329f}, NachtZone::Upstairs, false, true},
        {"zspawn_zombiespawner17", {12.062819f, -0.095225f, -6.670211f}, NachtZone::Upstairs, false, true},
        {"zspawn_zombiespawner18", {10.492319f, 3.810003f, 40.282625f}, NachtZone::Upstairs, false, true},
        {"zspawn_zombiespawner19", {10.631847f, 3.810002f, 28.723784f}, NachtZone::Upstairs, false, true},
        {"zspawn_zombiespawner20", {15.181989f, 3.903218f, 27.959873f}, NachtZone::Upstairs, false, true},
        {"zspawn_zombiespawner21", {25.405664f, 3.408246f, 38.515093f}, NachtZone::Upstairs, false, true},
        {"zspawn_zombiespawner2_20", {-14.535648f, -0.271532f, 4.694192f}, NachtZone::Start, true, true},
        {"zspawn_zombiespawner3_23", {-15.354806f, -0.333972f, -0.237418f}, NachtZone::Start, true, true},
        {"zspawn_zombiespawner4", {-7.490383f, -0.129635f, -15.384512f}, NachtZone::Start, true, true},
        {"zspawn_zombiespawner5", {-15.101215f, -0.774332f, -22.086555f}, NachtZone::Start, true, true},
        {"zspawn_zombiespawner6", {-14.392579f, -0.474903f, -11.247102f}, NachtZone::Start, true, true},
        {"zspawn_zombiespawner7", {10.037568f, 0.230940f, -33.212349f}, NachtZone::Start, true, true},
        {"zspawn_zombiespawner8", {8.901859f, 0.020444f, -25.665203f}, NachtZone::Start, true, true},
        {"zspawn_zombiespawner9", {12.994844f, -0.221694f, -12.927321f}, NachtZone::Start, true, true},
        {"zspawn_zombiespawner_16", {-16.258293f, -0.130339f, 16.088809f}, NachtZone::Start, true, false},
    }},
    .purchases = {{
        {"purchase_arak", "KN-44", "ar_standard", PurchaseKind::WallWeapon, 1400U, {-5.709419f, 4.990672f, 26.457163f}, 1.5f, true},
        {"purchase_argus", "Argus", "shotgun_precision", PurchaseKind::WallWeapon, 1100U, {18.624508f, 5.707007f, 25.683310f}, 1.5f, true},
        {"purchase_frag", "Fragmentation Grenades", "frag_grenade", PurchaseKind::Equipment, 250U, {-3.960460f, 5.046703f, -3.098613f}, 1.5f, true},
        {"purchase_krm", "KRM-262", "shotgun_pump", PurchaseKind::WallWeapon, 750U, {26.352487f, 1.440421f, 19.632632f}, 1.5f, true},
        {"purchase_kuda", "Kuda", "smg_standard", PurchaseKind::WallWeapon, 1250U, {24.049902f, 1.360282f, 25.628601f}, 1.5f, true},
        {"purchase_locus_decal", "Locus", "sniper_fastbolt", PurchaseKind::WeaponCabinet, 5000U, {14.256981f, 4.376229f, 22.525286f}, 1.5f, true},
        {"purchase_pharaoh", "Pharo", "smg_burst", PurchaseKind::WallWeapon, 700U, {5.424384f, 5.046703f, 11.316592f}, 1.5f, true},
        {"purchase_shiva", "Sheiva", "ar_marksman", PurchaseKind::WallWeapon, 500U, {-5.232187f, 1.440421f, 6.058283f}, 1.5f, true},
        {"purchase_triton", "RK5", "pistol_burst", PurchaseKind::WallWeapon, 500U, {-2.489199f, 1.411515f, -10.343102f}, 1.5f, true},
    }},
    .doors = {{
        // Canonical Nacht progression has three 1000-point routes.
        // Transforms are mapped from the Pavlov port actors by DoorFlag
        // topology; the 10000-point unflagged port actor is intentionally
        // excluded from the BO3 reference profile.
        {"door_start_to_box", {4.343400f, 1.244600f, 14.884401f}, 1000U, 1.6f, kNachtStartZoneMask, kNachtBoxZoneMask, true},
        {"door_start_to_upstairs", {4.290648f, 4.073596f, 2.219196f}, 1000U, 1.6f, kNachtStartZoneMask, kNachtUpstairsZoneMask, true},
        {"door_box_to_upstairs", {-1.153160f, 4.003040f, 26.810671f}, 1000U, 1.6f, kNachtBoxZoneMask, kNachtUpstairsZoneMask, true},
    }},
};

constexpr NachtZoneMask zoneBit(
    NachtZone zone) noexcept {
    return static_cast<NachtZoneMask>(
        1U <<
        static_cast<std::uint8_t>(
            zone));
}

} // namespace

const NachtReferenceProfile&
nachtReferenceProfile() noexcept {
    return kProfile;
}

std::size_t collectNachtSpawnPoints(
    NachtZoneMask activeZones,
    std::span<Vec3> destination) noexcept {
    std::size_t count = 0;

    for (const auto& spawn :
         kProfile.zombieSpawns) {
        if ((activeZones &
             zoneBit(spawn.zone)) == 0U) {
            continue;
        }

        if (count >=
            destination.size()) {
            break;
        }

        destination[count++] =
            spawn.position;
    }

    return count;
}

HordeConfig makeNachtHordeConfig(
    NachtZoneMask activeZones) noexcept {
    HordeConfig config{};
    config.maxActive = 24U;
    config.spawnIntervalSeconds = 0.65f;
    config.interRoundDelaySeconds = 4.5f;
    config.minimumSpawnDistanceFromPlayer = 4.0f;

    config.arenaMinimumX = -18.0f;
    config.arenaMaximumX = 41.0f;
    config.arenaMinimumZ = -35.0f;
    config.arenaMaximumZ = 42.0f;

    const std::size_t count =
        collectNachtSpawnPoints(
            activeZones,
            std::span<Vec3>(
                config.spawnPoints.data(),
                config.spawnPoints.size()));

    config.spawnPointCount =
        static_cast<std::uint32_t>(
            std::max<std::size_t>(
                count,
                1U));

    return config;
}

} // namespace xziel
