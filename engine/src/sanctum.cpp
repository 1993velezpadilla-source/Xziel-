#include "xziel/sanctum.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

constexpr std::size_t presenceIndex(
    SanctumPresenceKind kind) noexcept {
    return static_cast<std::size_t>(kind);
}

float clamp01(float value) noexcept {
    if (!std::isfinite(value)) {
        return 0.0f;
    }
    return std::clamp(value, 0.0f, 1.0f);
}

float distanceMeters(
    const SanctumPoint& a,
    const SanctumPoint& b) noexcept {
    const float dx = a.x - b.x;
    const float dy = a.y - b.y;
    const float dz = a.z - b.z;
    return std::sqrt(dx * dx + dy * dy + dz * dz);
}

float passiveRadius(
    SanctumPresenceKind kind) noexcept {
    switch (kind) {
        case SanctumPresenceKind::Llorona:
            return 58.0f;
        case SanctumPresenceKind::Nun:
            return 46.0f;
    }
    return 40.0f;
}

float passiveBedGain(
    SanctumPresenceKind kind,
    bool hostile,
    float intensity) noexcept {
    const float shaped =
        0.70f + 0.30f * clamp01(intensity);

    switch (kind) {
        case SanctumPresenceKind::Llorona:
            return (hostile ? 0.86f : 0.62f) * shaped;
        case SanctumPresenceKind::Nun:
            return (hostile ? 0.66f : 0.42f) * shaped;
    }
    return 0.0f;
}

float eventDistanceGain(
    float distance,
    float radius) noexcept {
    if (radius <= 0.0f || distance >= radius) {
        return 0.0f;
    }

    const float normalized =
        clamp01(distance / radius);

    // Keep distant passive sounds barely present, but never let them become
    // louder than a nearby source. The final mixer still applies occlusion.
    const float shaped =
        1.0f - normalized * normalized;

    return 0.08f + 0.92f * shaped;
}

SanctumPassiveCue chooseCue(
    SanctumPresenceKind kind,
    std::uint32_t state) noexcept {
    const bool alternate = (state & 1U) != 0U;

    if (kind == SanctumPresenceKind::Llorona) {
        return alternate
            ? SanctumPassiveCue::LloronaBreath
            : SanctumPassiveCue::LloronaDistantCry;
    }

    return alternate
        ? SanctumPassiveCue::NunWhisper
        : SanctumPassiveCue::NunPrayer;
}

bool addRoom(
    AcousticGraph& graph,
    SanctumZone zone,
    ReverbPreset preset,
    float reverb,
    float damping,
    float absorption) noexcept {
    return graph.addRoom({
        .id = static_cast<std::uint32_t>(zone),
        .preset = preset,
        .reverbAmount = reverb,
        .damping = damping,
        .occlusionAbsorption = absorption,
    });
}

bool addPortal(
    AcousticGraph& graph,
    std::uint32_t id,
    SanctumZone a,
    SanctumZone b,
    float openness,
    float absorption) noexcept {
    return graph.addPortal({
        .id = id,
        .roomA = static_cast<std::uint32_t>(a),
        .roomB = static_cast<std::uint32_t>(b),
        .openness = openness,
        .absorption = absorption,
    });
}

} // namespace

void SanctumAtmosphere::reset(
    std::uint32_t seed) noexcept {
    randomState_ =
        seed != 0U
        ? seed
        : 0x53A7C7U;

    initialized_ = true;

    cueCountdown_[
        presenceIndex(
            SanctumPresenceKind::Llorona)] =
        5.0f + random01() * 5.0f;

    cueCountdown_[
        presenceIndex(
            SanctumPresenceKind::Nun)] =
        8.0f + random01() * 6.0f;
}

bool SanctumAtmosphere::configureAcoustics(
    AcousticGraph& graph) noexcept {
    graph.reset();

    const bool roomsReady =
        addRoom(
            graph,
            SanctumZone::Courtyard,
            ReverbPreset::Exterior,
            0.12f,
            0.22f,
            0.18f) &&
        addRoom(
            graph,
            SanctumZone::Nave,
            ReverbPreset::Hall,
            0.76f,
            0.34f,
            0.30f) &&
        addRoom(
            graph,
            SanctumZone::Office,
            ReverbPreset::SmallRoom,
            0.30f,
            0.48f,
            0.48f) &&
        addRoom(
            graph,
            SanctumZone::OfficeCorridor,
            ReverbPreset::ConcreteRoom,
            0.38f,
            0.48f,
            0.52f) &&
        addRoom(
            graph,
            SanctumZone::BoilerRoom,
            ReverbPreset::MetalChamber,
            0.54f,
            0.42f,
            0.58f) &&
        addRoom(
            graph,
            SanctumZone::TowerStairs,
            ReverbPreset::Tunnel,
            0.48f,
            0.44f,
            0.52f) &&
        addRoom(
            graph,
            SanctumZone::RingingChamber,
            ReverbPreset::Hall,
            0.82f,
            0.30f,
            0.32f) &&
        addRoom(
            graph,
            SanctumZone::ClockChamber,
            ReverbPreset::MetalChamber,
            0.62f,
            0.38f,
            0.44f) &&
        addRoom(
            graph,
            SanctumZone::RoofChamber,
            ReverbPreset::ConcreteRoom,
            0.34f,
            0.40f,
            0.38f) &&
        addRoom(
            graph,
            SanctumZone::TowerTop,
            ReverbPreset::Exterior,
            0.18f,
            0.18f,
            0.16f);

    if (!roomsReady) {
        graph.reset();
        return false;
    }

    const bool portalsReady =
        addPortal(
            graph, 1001U,
            SanctumZone::Courtyard,
            SanctumZone::Nave,
            1.0f, 0.10f) &&
        addPortal(
            graph, 1002U,
            SanctumZone::Nave,
            SanctumZone::Office,
            0.92f, 0.18f) &&
        addPortal(
            graph, 1003U,
            SanctumZone::Office,
            SanctumZone::OfficeCorridor,
            0.92f, 0.16f) &&
        addPortal(
            graph, 1004U,
            SanctumZone::OfficeCorridor,
            SanctumZone::BoilerRoom,
            0.84f, 0.22f) &&
        addPortal(
            graph, 1005U,
            SanctumZone::Nave,
            SanctumZone::TowerStairs,
            0.84f, 0.20f) &&
        addPortal(
            graph, 1006U,
            SanctumZone::TowerStairs,
            SanctumZone::RingingChamber,
            0.88f, 0.18f) &&
        addPortal(
            graph, 1007U,
            SanctumZone::RingingChamber,
            SanctumZone::ClockChamber,
            0.86f, 0.16f) &&
        addPortal(
            graph, 1008U,
            SanctumZone::ClockChamber,
            SanctumZone::RoofChamber,
            0.82f, 0.20f) &&
        addPortal(
            graph, 1009U,
            SanctumZone::RoofChamber,
            SanctumZone::TowerTop,
            0.94f, 0.08f);

    if (!portalsReady) {
        graph.reset();
        return false;
    }

    return true;
}

SanctumAtmosphereFrame SanctumAtmosphere::advance(
    float deltaSeconds,
    const SanctumListener& listener,
    const SanctumPresence* presences,
    std::size_t presenceCount,
    const AcousticGraph& acoustics) noexcept {
    SanctumAtmosphereFrame frame{};

    if (!initialized_) {
        reset();
    }

    const float dt =
        std::clamp(
            std::isfinite(deltaSeconds)
                ? deltaSeconds
                : 0.0f,
            0.0f,
            0.25f);

    for (std::size_t i = 0;
         i < cueCountdown_.size();
         ++i) {
        cueCountdown_[i] =
            std::max(
                0.0f,
                cueCountdown_[i] - dt);
    }

    if (presences == nullptr) {
        return frame;
    }

    for (std::size_t i = 0;
         i < presenceCount;
         ++i) {
        const auto& presence = presences[i];

        if (!presence.active ||
            presence.id == 0U ||
            presence.zone == SanctumZone::Unknown) {
            continue;
        }

        const float distance =
            distanceMeters(
                listener.position,
                presence.position);

        const float radius =
            passiveRadius(
                presence.kind);

        if (distance > radius) {
            continue;
        }

        const auto acoustic =
            acoustics.query({
                .sourceRoom =
                    static_cast<std::uint32_t>(
                        presence.zone),
                .listenerRoom =
                    static_cast<std::uint32_t>(
                        listener.zone),
                .directDistanceMeters =
                    distance,
                .sourceImportance =
                    1.0f,
            });

        if (!acoustic.connected) {
            continue;
        }

        if (frame.passiveBedCount <
            frame.passiveBeds.size()) {
            auto& bed =
                frame.passiveBeds[
                    frame.passiveBedCount++];

            bed.id =
                presence.id ^
                0xA51E000000000000ULL;
            bed.kind =
                AudioSourceKind::Ambience;
            bed.distanceMeters =
                distance;
            bed.baseGain =
                passiveBedGain(
                    presence.kind,
                    presence.hostile,
                    presence.intensity);
            bed.importance =
                presence.hostile
                ? 0.90f
                : 0.42f;
            bed.occlusion =
                acoustic.occlusion;
            bed.reverbZoneSend =
                std::max(
                    acoustic.sourceRoomReverbSend,
                    acoustic.listenerRoomReverbSend);
            bed.looping = true;
            bed.critical = false;
        }

        const std::size_t slot =
            presenceIndex(
                presence.kind);

        if (slot >= cueCountdown_.size() ||
            cueCountdown_[slot] > 0.0f ||
            frame.cueEventCount >=
                frame.cueEvents.size()) {
            continue;
        }

        const float occlusionGain =
            1.0f -
            clamp01(
                acoustic.occlusion) *
                0.62f;

        auto& event =
            frame.cueEvents[
                frame.cueEventCount++];

        event.sourceId =
            presence.id;
        event.presence =
            presence.kind;
        event.cue =
            chooseCue(
                presence.kind,
                randomState_);
        event.distanceMeters =
            distance;
        event.gain =
            passiveBedGain(
                presence.kind,
                presence.hostile,
                presence.intensity) *
            eventDistanceGain(
                distance,
                radius) *
            occlusionGain;
        event.lowPassHz =
            acoustic.lowPassHz;
        event.reverbSend =
            std::max(
                acoustic.sourceRoomReverbSend,
                acoustic.listenerRoomReverbSend);

        cueCountdown_[slot] =
            nextDelay(
                presence.kind,
                presence.hostile);
    }

    return frame;
}

float SanctumAtmosphere::random01() noexcept {
    std::uint32_t x =
        randomState_;

    x ^= x << 13U;
    x ^= x >> 17U;
    x ^= x << 5U;

    randomState_ =
        x != 0U
        ? x
        : 0x53A7C7U;

    return static_cast<float>(
        randomState_ & 0x00FFFFFFU) /
        static_cast<float>(
            0x01000000U);
}

float SanctumAtmosphere::nextDelay(
    SanctumPresenceKind kind,
    bool hostile) noexcept {
    const float t =
        random01();

    if (kind ==
        SanctumPresenceKind::Llorona) {
        return hostile
            ? 5.0f + t * 4.0f
            : 12.0f + t * 10.0f;
    }

    return hostile
        ? 7.0f + t * 5.0f
        : 18.0f + t * 14.0f;
}

const char* sanctumZoneName(
    SanctumZone zone) noexcept {
    switch (zone) {
        case SanctumZone::Courtyard:
            return "Fallen Courtyard";
        case SanctumZone::Nave:
            return "Nave";
        case SanctumZone::Office:
            return "Office";
        case SanctumZone::OfficeCorridor:
            return "Office Corridor";
        case SanctumZone::BoilerRoom:
            return "Boiler Room";
        case SanctumZone::TowerStairs:
            return "Tower Stairs";
        case SanctumZone::RingingChamber:
            return "Ringing Chamber";
        case SanctumZone::ClockChamber:
            return "Clock Chamber";
        case SanctumZone::RoofChamber:
            return "Roof Chamber";
        case SanctumZone::TowerTop:
            return "Tower Top";
        case SanctumZone::Unknown:
            break;
    }

    return "Unknown";
}

} // namespace xziel
