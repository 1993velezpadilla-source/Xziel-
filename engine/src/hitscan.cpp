#include "xziel/hitscan.hpp"

#include <algorithm>
#include <cmath>
#include <limits>

namespace xziel {

namespace {

constexpr float kPi =
    3.14159265358979323846f;

constexpr float kDegreesToRadians =
    kPi / 180.0f;

float component(
    const Vec3& value,
    int axis) noexcept {
    if (axis == 0) {
        return value.x;
    }

    if (axis == 1) {
        return value.y;
    }

    return value.z;
}

void setComponent(
    Vec3& value,
    int axis,
    float componentValue) noexcept {
    if (axis == 0) {
        value.x = componentValue;
    } else if (axis == 1) {
        value.y = componentValue;
    } else {
        value.z = componentValue;
    }
}

Vec3 normalizedOrForward(
    Vec3 direction) noexcept {
    const float lengthSquared =
        direction.x * direction.x +
        direction.y * direction.y +
        direction.z * direction.z;

    if (!std::isfinite(lengthSquared) ||
        lengthSquared <= 1.0e-12f) {
        return {
            0.0f,
            0.0f,
            1.0f,
        };
    }

    const float inverseLength =
        1.0f /
        std::sqrt(lengthSquared);

    direction.x *= inverseLength;
    direction.y *= inverseLength;
    direction.z *= inverseLength;

    return direction;
}

} // namespace

Ray makeViewRay(
    Vec3 origin,
    float yawDegrees,
    float pitchDegrees) noexcept {
    const float yaw =
        std::isfinite(yawDegrees)
        ? yawDegrees *
            kDegreesToRadians
        : 0.0f;

    const float pitch =
        std::isfinite(pitchDegrees)
        ? pitchDegrees *
            kDegreesToRadians
        : 0.0f;

    const float cosPitch =
        std::cos(pitch);

    Ray ray{};
    ray.origin = origin;
    ray.direction =
        normalizedOrForward(
            {
                std::sin(yaw) *
                    cosPitch,
                -std::sin(pitch),
                std::cos(yaw) *
                    cosPitch,
            });

    return ray;
}

HitscanResult raycastAabb(
    const Ray& ray,
    const Aabb& box,
    float maximumDistance) noexcept {
    HitscanResult result{};

    const float maxDistance =
        (!std::isfinite(maximumDistance) ||
         maximumDistance <= 0.0f)
        ? 0.0f
        : maximumDistance;

    if (maxDistance <= 0.0f) {
        return result;
    }

    const Vec3 direction =
        normalizedOrForward(
            ray.direction);

    float nearDistance = 0.0f;
    float farDistance = maxDistance;

    Vec3 nearNormal{};

    for (int axis = 0;
         axis < 3;
         ++axis) {
        const float origin =
            component(
                ray.origin,
                axis);

        const float directionValue =
            component(
                direction,
                axis);

        const float minimum =
            component(
                box.minimum,
                axis);

        const float maximum =
            component(
                box.maximum,
                axis);

        if (minimum > maximum) {
            return result;
        }

        if (std::fabs(directionValue) <
            1.0e-7f) {
            if (origin < minimum ||
                origin > maximum) {
                return result;
            }

            continue;
        }

        const float inverseDirection =
            1.0f /
            directionValue;

        float t0 =
            (minimum - origin) *
            inverseDirection;

        float t1 =
            (maximum - origin) *
            inverseDirection;

        float normalSign = -1.0f;

        if (t0 > t1) {
            std::swap(
                t0,
                t1);
            normalSign = 1.0f;
        }

        if (t0 > nearDistance) {
            nearDistance = t0;
            nearNormal = {};
            setComponent(
                nearNormal,
                axis,
                normalSign);
        }

        farDistance =
            std::min(
                farDistance,
                t1);

        if (nearDistance >
            farDistance) {
            return result;
        }
    }

    if (nearDistance < 0.0f ||
        nearDistance > maxDistance) {
        return result;
    }

    result.hit = true;
    result.distance = nearDistance;
    result.point = {
        ray.origin.x +
            direction.x *
            nearDistance,
        ray.origin.y +
            direction.y *
            nearDistance,
        ray.origin.z +
            direction.z *
            nearDistance,
    };
    result.normal = nearNormal;

    return result;
}

} // namespace xziel
