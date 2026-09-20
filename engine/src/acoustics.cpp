#include "xziel/acoustics.hpp"

#include <algorithm>
#include <array>
#include <cmath>

namespace xziel {

namespace {

float clamp01(float value) noexcept {
    if (!std::isfinite(value)) {
        return 0.0f;
    }
    return std::clamp(value, 0.0f, 1.0f);
}

float distanceAttenuation(float meters) noexcept {
    const float d = std::max(0.0f, meters);
    return 1.0f / (1.0f + 0.055f * d + 0.010f * d * d);
}

} // namespace

void AcousticGraph::reset() noexcept {
    rooms_ = {};
    portals_ = {};
    roomCount_ = 0;
    portalCount_ = 0;
}

bool AcousticGraph::addRoom(
    const AcousticRoom& room) noexcept {
    if (room.id == 0 ||
        roomCount_ >= rooms_.size() ||
        roomIndex(room.id) >= 0) {
        return false;
    }

    rooms_[roomCount_++] = room;
    return true;
}

bool AcousticGraph::addPortal(
    const AcousticPortal& portal) noexcept {
    if (portal.id == 0 ||
        portalCount_ >= portals_.size() ||
        roomIndex(portal.roomA) < 0 ||
        roomIndex(portal.roomB) < 0 ||
        portal.roomA == portal.roomB) {
        return false;
    }

    for (std::size_t i = 0; i < portalCount_; ++i) {
        if (portals_[i].id == portal.id) {
            return false;
        }
    }

    portals_[portalCount_] = portal;
    portals_[portalCount_].openness =
        clamp01(portal.openness);
    portals_[portalCount_].absorption =
        clamp01(portal.absorption);

    ++portalCount_;
    return true;
}

bool AcousticGraph::setPortalOpenness(
    std::uint32_t portalId,
    float openness) noexcept {
    for (std::size_t i = 0; i < portalCount_; ++i) {
        if (portals_[i].id == portalId) {
            portals_[i].openness =
                clamp01(openness);
            return true;
        }
    }
    return false;
}

AcousticResult AcousticGraph::query(
    const AcousticQuery& query) const noexcept {
    AcousticResult out{};

    const int sourceIndex =
        roomIndex(query.sourceRoom);
    const int listenerIndex =
        roomIndex(query.listenerRoom);

    if (sourceIndex < 0 || listenerIndex < 0) {
        return out;
    }

    const auto& sourceRoom =
        rooms_[static_cast<std::size_t>(sourceIndex)];
    const auto& listenerRoom =
        rooms_[static_cast<std::size_t>(listenerIndex)];

    out.listenerPreset =
        listenerRoom.preset;
    out.sourceRoomReverbSend =
        clamp01(sourceRoom.reverbAmount);
    out.listenerRoomReverbSend =
        clamp01(listenerRoom.reverbAmount);

    if (sourceIndex == listenerIndex) {
        out.connected = true;
        out.transmission =
            distanceAttenuation(query.directDistanceMeters);
        out.occlusion = 0.0f;
        out.lowPassHz = 20000.0f;
        out.portalHops = 0;
        return out;
    }

    // Best-transmission search. Graph is intentionally bounded and small.
    std::array<float, kMaxAcousticRooms> bestTransmission{};
    std::array<std::uint8_t, kMaxAcousticRooms> bestHops{};
    std::array<bool, kMaxAcousticRooms> visited{};

    bestTransmission[
        static_cast<std::size_t>(sourceIndex)] = 1.0f;

    for (std::size_t iteration = 0;
         iteration < roomCount_;
         ++iteration) {
        int current = -1;
        float currentTransmission = -1.0f;

        for (std::size_t r = 0;
             r < roomCount_;
             ++r) {
            if (!visited[r] &&
                bestTransmission[r] >
                    currentTransmission) {
                current =
                    static_cast<int>(r);
                currentTransmission =
                    bestTransmission[r];
            }
        }

        if (current < 0 ||
            currentTransmission <= 0.0f) {
            break;
        }

        if (current == listenerIndex) {
            break;
        }

        visited[
            static_cast<std::size_t>(current)] = true;

        const std::uint32_t currentRoomId =
            rooms_[
                static_cast<std::size_t>(current)].id;

        for (std::size_t p = 0;
             p < portalCount_;
             ++p) {
            const auto& portal = portals_[p];

            std::uint32_t neighborId = 0;
            if (portal.roomA == currentRoomId) {
                neighborId = portal.roomB;
            } else if (
                portal.roomB == currentRoomId) {
                neighborId = portal.roomA;
            } else {
                continue;
            }

            const int neighbor =
                roomIndex(neighborId);
            if (neighbor < 0) {
                continue;
            }

            const float opening =
                clamp01(portal.openness);
            const float material =
                1.0f -
                clamp01(portal.absorption) *
                0.75f;

            const float roomLoss =
                1.0f -
                clamp01(
                    rooms_[
                        static_cast<std::size_t>(neighbor)]
                        .occlusionAbsorption) *
                0.12f;

            const float edgeTransmission =
                opening * material * roomLoss;

            const float candidate =
                currentTransmission *
                edgeTransmission;

            const auto neighborIndex =
                static_cast<std::size_t>(neighbor);

            if (candidate >
                bestTransmission[neighborIndex]) {
                bestTransmission[neighborIndex] =
                    candidate;
                bestHops[neighborIndex] =
                    static_cast<std::uint8_t>(
                        std::min<int>(
                            255,
                            static_cast<int>(
                                bestHops[
                                    static_cast<std::size_t>(
                                        current)]) +
                            1));
            }
        }
    }

    const auto listener =
        static_cast<std::size_t>(listenerIndex);
    const float pathTransmission =
        clamp01(bestTransmission[listener]);

    if (pathTransmission <= 0.0001f) {
        out.connected = false;
        out.transmission = 0.0f;
        out.occlusion = 1.0f;
        out.lowPassHz = 1200.0f;
        return out;
    }

    out.connected = true;
    out.portalHops = bestHops[listener];

    const float direct =
        distanceAttenuation(
            query.directDistanceMeters);

    out.transmission =
        clamp01(pathTransmission * direct);

    // Portal occlusion shapes timbre separately from distance attenuation.
    out.occlusion =
        clamp01(1.0f - pathTransmission);

    const float minimumHz = 1600.0f;
    const float maximumHz = 20000.0f;

    out.lowPassHz =
        minimumHz +
        (maximumHz - minimumHz) *
        (1.0f - out.occlusion) *
        (1.0f - out.occlusion);

    return out;
}

std::size_t AcousticGraph::roomCount() const noexcept {
    return roomCount_;
}

std::size_t AcousticGraph::portalCount() const noexcept {
    return portalCount_;
}

int AcousticGraph::roomIndex(
    std::uint32_t roomId) const noexcept {
    for (std::size_t i = 0; i < roomCount_; ++i) {
        if (rooms_[i].id == roomId) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

} // namespace xziel
