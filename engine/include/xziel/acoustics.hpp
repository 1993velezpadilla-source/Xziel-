#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace xziel {

constexpr std::size_t kMaxAcousticRooms = 64;
constexpr std::size_t kMaxAcousticPortals = 128;

enum class ReverbPreset : std::uint8_t {
    Dry,
    SmallRoom,
    ConcreteRoom,
    Hall,
    Tunnel,
    Exterior,
    Sewer,
    MetalChamber,
};

struct AcousticRoom {
    std::uint32_t id = 0;
    ReverbPreset preset = ReverbPreset::Dry;

    float reverbAmount = 0.0f;
    float damping = 0.5f;
    float occlusionAbsorption = 0.5f;
};

struct AcousticPortal {
    std::uint32_t id = 0;
    std::uint32_t roomA = 0;
    std::uint32_t roomB = 0;

    // 0 = closed/blocked, 1 = fully open.
    float openness = 1.0f;

    // Extra material loss such as a door/wall.
    float absorption = 0.0f;
};

struct AcousticQuery {
    std::uint32_t sourceRoom = 0;
    std::uint32_t listenerRoom = 0;

    float directDistanceMeters = 0.0f;
    float sourceImportance = 1.0f;
};

struct AcousticResult {
    bool connected = false;

    float transmission = 0.0f;
    float occlusion = 1.0f;
    float lowPassHz = 2200.0f;

    float sourceRoomReverbSend = 0.0f;
    float listenerRoomReverbSend = 0.0f;

    ReverbPreset listenerPreset = ReverbPreset::Dry;

    std::uint8_t portalHops = 0;
};

class AcousticGraph final {
public:
    void reset() noexcept;

    [[nodiscard]] bool addRoom(
        const AcousticRoom& room) noexcept;

    [[nodiscard]] bool addPortal(
        const AcousticPortal& portal) noexcept;

    [[nodiscard]] bool setPortalOpenness(
        std::uint32_t portalId,
        float openness) noexcept;

    [[nodiscard]] AcousticResult query(
        const AcousticQuery& query) const noexcept;

    [[nodiscard]] std::size_t roomCount() const noexcept;
    [[nodiscard]] std::size_t portalCount() const noexcept;

private:
    [[nodiscard]] int roomIndex(
        std::uint32_t roomId) const noexcept;

    std::array<AcousticRoom, kMaxAcousticRooms> rooms_{};
    std::array<AcousticPortal, kMaxAcousticPortals> portals_{};

    std::size_t roomCount_ = 0;
    std::size_t portalCount_ = 0;
};

} // namespace xziel
