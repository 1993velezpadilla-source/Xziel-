#pragma once

#include "xziel/engine.hpp"

namespace xziel {

struct Ray {
    Vec3 origin{};
    Vec3 direction{
        0.0f,
        0.0f,
        1.0f,
    };
};

struct Aabb {
    Vec3 minimum{};
    Vec3 maximum{};
};

struct HitscanResult {
    bool hit = false;
    float distance = 0.0f;
    Vec3 point{};
    Vec3 normal{};
};

[[nodiscard]] Ray makeViewRay(
    Vec3 origin,
    float yawDegrees,
    float pitchDegrees) noexcept;

[[nodiscard]] HitscanResult raycastAabb(
    const Ray& ray,
    const Aabb& box,
    float maximumDistance = 1000.0f) noexcept;

} // namespace xziel
