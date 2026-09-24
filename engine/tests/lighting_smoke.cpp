#include "xziel/lighting.hpp"

#include <cassert>
#include <cmath>

int main() {
    xziel::HorrorLightingDirector director{};

    xziel::HorrorFrame horror{};
    horror.tension = 0.8f;
    horror.exposureBiasEv = -0.2f;

    xziel::EnvironmentFrame environment{};
    environment.fogDensity = 0.10f;
    environment.lightningFlash = 0.0f;

    xziel::LocalLightInput lights[3]{};

    lights[0].id = 1U;
    lights[0].enabled = true;
    lights[0].position = {0.0f, 1.8f, 2.0f};
    lights[0].colorLinear = {1.0f, 0.35f, 0.08f};
    lights[0].intensity = 2.4f;
    lights[0].rangeMeters = 7.0f;
    lights[0].importance = 1.0f;
    lights[0].flickerAmount = 0.3f;
    lights[0].flickerHz = 2.1f;

    lights[1].id = 2U;
    lights[1].enabled = true;
    lights[1].position = {80.0f, 0.0f, 0.0f};
    lights[1].intensity = 1.0f;
    lights[1].rangeMeters = 4.0f;
    lights[1].importance = 1.0f;

    lights[2].id = 3U;
    lights[2].enabled = true;
    lights[2].type = xziel::LightType::Spot;
    lights[2].position = {1.0f, 2.0f, -1.0f};
    lights[2].direction = {-0.2f, -0.8f, 0.3f};
    lights[2].colorLinear = {0.18f, 0.32f, 1.0f};
    lights[2].intensity = 1.6f;
    lights[2].rangeMeters = 12.0f;
    lights[2].importance = 0.9f;
    lights[2].innerConeDegrees = 18.0f;
    lights[2].outerConeDegrees = 34.0f;

    const auto frame =
        director.advance(
            horror,
            environment,
            {0.0f, 1.6f, 0.0f},
            lights,
            3U,
            xziel::RenderQuality::High,
            3.25f);

    assert(frame.localLightCount == 2U);
    assert(frame.localLights[0].id == 1U);
    assert(frame.localLights[1].id == 3U);
    assert(frame.fogDensity > environment.fogDensity);
    assert(frame.exposureEv < -0.4f);
    assert(frame.exposureScale > 0.0f);
    assert(frame.exposureScale < 1.0f);
    assert(frame.saturation < 0.9f);
    assert(frame.keyIntensity > 0.0f);

    const auto sameFrame =
        director.advance(
            horror,
            environment,
            {0.0f, 1.6f, 0.0f},
            lights,
            3U,
            xziel::RenderQuality::High,
            3.25f);

    assert(
        std::fabs(
            sameFrame.localLights[0].intensity -
            frame.localLights[0].intensity) <
        0.000001f);

    const auto lowFrame =
        director.advance(
            horror,
            environment,
            {0.0f, 1.6f, 0.0f},
            lights,
            3U,
            xziel::RenderQuality::Low,
            3.25f);

    assert(lowFrame.localLightCount == 2U);

    environment.lightningFlash = 1.0f;
    const auto lightningFrame =
        director.advance(
            horror,
            environment,
            {0.0f, 1.6f, 0.0f},
            nullptr,
            0U,
            xziel::RenderQuality::High,
            3.25f);

    assert(lightningFrame.keyIntensity > frame.keyIntensity);
    assert(lightningFrame.localLightCount == 0U);

    return 0;
}
