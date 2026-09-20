#include "xziel/environment.hpp"

#include <cassert>

int main() {
    xziel::WeatherConfig storm{};
    storm.rainIntensity = 1.0f;
    storm.wetnessRisePerSecond = 0.5f;
    storm.lightningIntervalSeconds = 1.0f;
    storm.lightningDurationSeconds = 0.20f;
    storm.lightningIntensity = 3.0f;
    storm.fogDensity = 0.08f;
    storm.windMetersPerSecond = {4.0f, 0.0f, 1.0f};

    xziel::EnvironmentSystem environment(
        storm,
        xziel::RenderQuality::High);

    auto frame = environment.advance(0.10f);
    assert(frame.rainParticleBudget == 1536);
    assert(frame.splashParticleBudget == 256);
    assert(frame.wetness > 0.0f);
    assert(frame.lightningFlash > 0.0f);
    assert(frame.requirePrecipitationOcclusion);
    assert(frame.wetSurfaceResponse);

    for (int i = 0; i < 20; ++i) {
        frame = environment.advance(0.05f);
    }
    assert(frame.wetness > 0.25f);

    storm.rainIntensity = 0.0f;
    environment.setWeather(storm);
    const float beforeDry = frame.wetness;
    frame = environment.advance(0.10f);
    assert(frame.wetness < beforeDry);
    assert(frame.rainParticleBudget == 0);

    environment.setQuality(xziel::RenderQuality::Low);
    storm.rainIntensity = 1.0f;
    environment.setWeather(storm);
    frame = environment.advance(0.05f);
    assert(frame.rainParticleBudget == 384);

    return 0;
}
