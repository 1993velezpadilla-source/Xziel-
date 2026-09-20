#include "xziel/scene_fx.hpp"

#include <algorithm>
#include <cmath>

namespace xziel {

namespace {

float clamp01(float value) noexcept {
    if (!std::isfinite(value)) {
        return 0.0f;
    }
    return std::clamp(value, 0.0f, 1.0f);
}

} // namespace

DecalPool::DecalPool(std::uint32_t capacity)
    : slots_(std::max<std::uint32_t>(1U, capacity)) {}

void DecalPool::reset() noexcept {
    for (auto& slot : slots_) {
        slot = {};
    }
    nextId_ = 1;
    overwriteCursor_ = 0;
    alive_ = 0;
}

std::uint64_t DecalPool::spawn(
    const DecalDesc& desc) noexcept {
    std::uint32_t index = static_cast<std::uint32_t>(slots_.size());

    for (std::uint32_t i = 0;
         i < static_cast<std::uint32_t>(slots_.size());
         ++i) {
        if (!slots_[i].alive) {
            index = i;
            break;
        }
    }

    if (index >= slots_.size()) {
        // Full pool: overwrite a non-persistent decal using a bounded rotating
        // cursor. Persistent authored marks are protected where possible.
        for (std::uint32_t attempt = 0;
             attempt < static_cast<std::uint32_t>(slots_.size());
             ++attempt) {
            const std::uint32_t candidate =
                (overwriteCursor_ + attempt) %
                static_cast<std::uint32_t>(slots_.size());
            if (!slots_[candidate].item.desc.persistent) {
                index = candidate;
                overwriteCursor_ =
                    (candidate + 1U) %
                    static_cast<std::uint32_t>(slots_.size());
                break;
            }
        }
    }

    if (index >= slots_.size()) {
        return 0;
    }

    const bool wasAlive = slots_[index].alive;
    auto& slot = slots_[index];
    slot.alive = true;
    slot.item = {
        .id = nextId_++,
        .desc = desc,
        .ageSeconds = 0.0f,
    };

    if (!wasAlive) {
        ++alive_;
    }

    return slot.item.id;
}

void DecalPool::advance(float deltaSeconds) noexcept {
    const float dt =
        (!std::isfinite(deltaSeconds) || deltaSeconds <= 0.0f)
        ? 0.0f
        : std::min(deltaSeconds, 0.10f);

    for (auto& slot : slots_) {
        if (!slot.alive) {
            continue;
        }

        slot.item.ageSeconds += dt;

        const auto& desc = slot.item.desc;
        if (!desc.persistent &&
            desc.lifetimeSeconds > 0.0f &&
            slot.item.ageSeconds >= desc.lifetimeSeconds) {
            slot.alive = false;
            if (alive_ > 0) {
                --alive_;
            }
        }
    }
}

std::size_t DecalPool::buildVisibleList(
    const Vec3& cameraPosition,
    float maxDistanceMeters,
    DecalItem* destination,
    std::size_t destinationCapacity) const noexcept {
    if (destination == nullptr || destinationCapacity == 0) {
        return 0;
    }

    const float maxDistance =
        std::max(0.1f, maxDistanceMeters);
    const float maxDistanceSq =
        maxDistance * maxDistance;

    std::size_t written = 0;
    for (const auto& slot : slots_) {
        if (!slot.alive ||
            written >= destinationCapacity) {
            continue;
        }

        if (distanceSquared(
                slot.item.desc.position,
                cameraPosition) > maxDistanceSq) {
            continue;
        }

        destination[written++] = slot.item;
    }

    return written;
}

std::uint32_t DecalPool::aliveCount() const noexcept {
    return alive_;
}

std::uint32_t DecalPool::capacity() const noexcept {
    return static_cast<std::uint32_t>(slots_.size());
}

float DecalPool::distanceSquared(
    const Vec3& a,
    const Vec3& b) noexcept {
    const float dx = a.x - b.x;
    const float dy = a.y - b.y;
    const float dz = a.z - b.z;
    return dx * dx + dy * dy + dz * dz;
}

PostProcessPlan PostProcessPlanner::plan(
    const RenderWorkload& workload,
    const HorrorFrame& horror,
    bool cameraCut,
    bool playerUnderwater) const noexcept {
    PostProcessPlan out{};

    out.exposureBiasEv =
        std::clamp(horror.exposureBiasEv, -1.5f, 1.0f);
    out.vignetteStrength =
        std::clamp(horror.vignetteStrength, 0.0f, 0.35f);

    switch (workload.quality) {
        case RenderQuality::Low:
            out.bloomStrength = 0.18f;
            out.bloomResolutionScale = 0.25f;
            out.filmGrainStrength = 0.010f;
            out.chromaticAberrationStrength = 0.0f;
            out.sharpenStrength = 0.20f;

            out.ambientOcclusionEnabled = false;
            out.ambientOcclusionResolutionScale = 0.0f;
            out.ambientOcclusionSampleBudget = 0;

            out.volumetricFogEnabled = false;
            break;

        case RenderQuality::Medium:
            out.bloomStrength = 0.24f;
            out.bloomResolutionScale = 0.33f;
            out.filmGrainStrength = 0.014f;
            out.chromaticAberrationStrength = 0.002f;
            out.sharpenStrength = 0.18f;

            out.ambientOcclusionEnabled = true;
            out.ambientOcclusionResolutionScale = 0.33f;
            out.ambientOcclusionSampleBudget = 6;

            out.volumetricFogEnabled = true;
            break;

        case RenderQuality::High:
            out.bloomStrength = 0.30f;
            out.bloomResolutionScale = 0.50f;
            out.filmGrainStrength = 0.018f;
            out.chromaticAberrationStrength = 0.003f;
            out.sharpenStrength = 0.14f;

            out.ambientOcclusionEnabled = true;
            out.ambientOcclusionResolutionScale = 0.50f;
            out.ambientOcclusionSampleBudget = 12;

            out.volumetricFogEnabled = true;
            break;

        case RenderQuality::Ultra:
            out.bloomStrength = 0.34f;
            out.bloomResolutionScale = 0.50f;
            out.filmGrainStrength = 0.020f;
            out.chromaticAberrationStrength = 0.004f;
            out.sharpenStrength = 0.10f;

            out.ambientOcclusionEnabled = true;
            out.ambientOcclusionResolutionScale = 0.50f;
            out.ambientOcclusionSampleBudget = 16;

            out.volumetricFogEnabled = true;
            break;
    }

    // Horror intensity subtly changes presentation; it does not stack effects
    // until the image becomes unreadable.
    out.bloomStrength += horror.adrenaline * 0.04f;
    out.filmGrainStrength += horror.tension * 0.012f;
    out.chromaticAberrationStrength += horror.adrenaline * 0.003f;

    out.bloomStrength = clamp01(out.bloomStrength);
    out.filmGrainStrength =
        std::clamp(out.filmGrainStrength, 0.0f, 0.05f);
    out.chromaticAberrationStrength =
        std::clamp(
            out.chromaticAberrationStrength,
            0.0f,
            0.012f);

    if (playerUnderwater) {
        out.colorGradeStrength = 0.82f;
        out.chromaticAberrationStrength =
            std::max(out.chromaticAberrationStrength, 0.006f);
        out.sharpenStrength *= 0.45f;
    }

    out.temporalHistoryValid = !cameraCut;
    return out;
}

} // namespace xziel
