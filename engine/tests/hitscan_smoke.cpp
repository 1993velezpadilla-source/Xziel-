#include "xziel/hitscan.hpp"

#include <cassert>
#include <cmath>

int main() {
    const xziel::Aabb target{
        .minimum = {
            -0.5f,
            -0.5f,
            4.0f,
        },
        .maximum = {
            0.5f,
            0.5f,
            5.0f,
        },
    };

    const auto forward =
        xziel::makeViewRay(
            {},
            0.0f,
            0.0f);

    const auto hit =
        xziel::raycastAabb(
            forward,
            target,
            20.0f);

    assert(hit.hit);
    assert(
        std::fabs(
            hit.distance -
            4.0f) <
        0.001f);
    assert(
        hit.normal.z <
        -0.9f);

    const auto right =
        xziel::makeViewRay(
            {},
            90.0f,
            0.0f);

    assert(
        !xziel::raycastAabb(
             right,
             target,
             20.0f).hit);

    const xziel::Aabb elevated{
        .minimum = {
            -0.5f,
            0.7f,
            4.0f,
        },
        .maximum = {
            0.5f,
            1.7f,
            5.0f,
        },
    };

    // Negative pitch means looking upward in the player convention.
    const auto upward =
        xziel::makeViewRay(
            {},
            0.0f,
            -14.0f);

    assert(
        xziel::raycastAabb(
            upward,
            elevated,
            20.0f).hit);

    return 0;
}
