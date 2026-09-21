#include "android_audio.hpp"

#include <algorithm>
#include <cmath>

namespace xziel::android {

namespace {

constexpr float kPi =
    3.14159265358979323846f;

struct CueProfile {
    float frequency = 220.0f;
    float duration = 0.10f;
    float toneMix = 0.7f;
    float noiseMix = 0.3f;
    float pitchFall = 0.0f;
};

CueProfile profileFor(
    AndroidAudioCue cue) noexcept {
    switch (cue) {
        case AndroidAudioCue::Fire:
            return {118.0f, 0.075f, 0.36f, 0.88f, 0.72f};
        case AndroidAudioCue::Hit:
            return {760.0f, 0.055f, 0.92f, 0.08f, 0.18f};
        case AndroidAudioCue::CriticalHit:
            return {1180.0f, 0.085f, 0.92f, 0.12f, 0.24f};
        case AndroidAudioCue::PlayerHit:
            return {92.0f, 0.16f, 0.28f, 0.82f, 0.42f};
        case AndroidAudioCue::ZombieAttack:
            return {74.0f, 0.24f, 0.56f, 0.58f, 0.30f};
        case AndroidAudioCue::Reload:
            return {430.0f, 0.075f, 0.62f, 0.50f, 0.08f};
        case AndroidAudioCue::UiConfirm:
            return {660.0f, 0.075f, 0.94f, 0.02f, 0.0f};
        case AndroidAudioCue::UiError:
            return {170.0f, 0.14f, 0.88f, 0.05f, 0.22f};
        case AndroidAudioCue::Door:
            return {82.0f, 0.26f, 0.32f, 0.76f, 0.34f};
        case AndroidAudioCue::BarricadeBreak:
            return {145.0f, 0.12f, 0.22f, 0.92f, 0.24f};
        case AndroidAudioCue::BarricadeRebuild:
            return {260.0f, 0.10f, 0.45f, 0.68f, 0.08f};
        case AndroidAudioCue::RoundStart:
            return {196.0f, 0.42f, 0.90f, 0.10f, -0.18f};
        case AndroidAudioCue::HorrorStinger:
            return {56.0f, 0.58f, 0.72f, 0.48f, 0.48f};
        case AndroidAudioCue::Thunder:
            return {48.0f, 0.70f, 0.20f, 0.96f, 0.55f};
    }

    return {};
}

float clampSample(float value) noexcept {
    return std::clamp(value, -0.95f, 0.95f);
}

} // namespace

AndroidAudioEngine::~AndroidAudioEngine() {
    shutdown();
}

bool AndroidAudioEngine::initialize() noexcept {
    shutdown();
    disconnected_.store(false, std::memory_order_release);
    return openStream();
}

void AndroidAudioEngine::shutdown() noexcept {
    ready_.store(false, std::memory_order_release);

    if (stream_ != nullptr) {
        (void) AAudioStream_requestStop(stream_);
        (void) AAudioStream_close(stream_);
        stream_ = nullptr;
    }

    for (auto& voice : voices_) {
        voice = {};
    }
}

void AndroidAudioEngine::play(
    AndroidAudioCue cue,
    float gain) noexcept {
    Command command{
        .cue = cue,
        .gain = std::clamp(
            std::isfinite(gain) ? gain : 1.0f,
            0.0f,
            1.5f),
    };

    if (!commands_.tryPush(command)) {
        dropped_.fetch_add(1U, std::memory_order_relaxed);
    }
}

void AndroidAudioEngine::service() noexcept {
    if (!disconnected_.exchange(
            false,
            std::memory_order_acq_rel)) {
        return;
    }

    shutdown();
    (void) openStream();
}

bool AndroidAudioEngine::ready() const noexcept {
    return ready_.load(std::memory_order_acquire);
}

std::uint64_t AndroidAudioEngine::droppedCueCount() const noexcept {
    return dropped_.load(std::memory_order_relaxed);
}

bool AndroidAudioEngine::openStream() noexcept {
    AAudioStreamBuilder* builder = nullptr;

    if (AAudio_createStreamBuilder(&builder) != AAUDIO_OK ||
        builder == nullptr) {
        return false;
    }

    AAudioStreamBuilder_setDirection(
        builder,
        AAUDIO_DIRECTION_OUTPUT);
    AAudioStreamBuilder_setFormat(
        builder,
        AAUDIO_FORMAT_PCM_FLOAT);
    AAudioStreamBuilder_setChannelCount(
        builder,
        2);
    AAudioStreamBuilder_setPerformanceMode(
        builder,
        AAUDIO_PERFORMANCE_MODE_LOW_LATENCY);
    AAudioStreamBuilder_setSharingMode(
        builder,
        AAUDIO_SHARING_MODE_SHARED);
    AAudioStreamBuilder_setUsage(
        builder,
        AAUDIO_USAGE_GAME);
    AAudioStreamBuilder_setContentType(
        builder,
        AAUDIO_CONTENT_TYPE_SONIFICATION);
    AAudioStreamBuilder_setDataCallback(
        builder,
        &AndroidAudioEngine::dataCallback,
        this);
    AAudioStreamBuilder_setErrorCallback(
        builder,
        &AndroidAudioEngine::errorCallback,
        this);

    const aaudio_result_t openResult =
        AAudioStreamBuilder_openStream(
            builder,
            &stream_);

    AAudioStreamBuilder_delete(
        builder);

    if (openResult != AAUDIO_OK ||
        stream_ == nullptr) {
        stream_ = nullptr;
        return false;
    }

    const std::int32_t rate =
        AAudioStream_getSampleRate(
            stream_);

    sampleRate_ =
        rate > 8000
        ? static_cast<float>(rate)
        : 48000.0f;

    const aaudio_result_t startResult =
        AAudioStream_requestStart(
            stream_);

    if (startResult != AAUDIO_OK) {
        (void) AAudioStream_close(stream_);
        stream_ = nullptr;
        return false;
    }

    ready_.store(true, std::memory_order_release);
    return true;
}

void AndroidAudioEngine::startVoice(
    const Command& command) noexcept {
    Voice* slot = nullptr;

    for (auto& voice : voices_) {
        if (!voice.active) {
            slot = &voice;
            break;
        }
    }

    if (slot == nullptr) {
        // Deterministic voice stealing: replace the voice closest to its end.
        slot = &voices_[0];
        float oldestRatio = -1.0f;

        for (auto& voice : voices_) {
            const float ratio =
                voice.durationSeconds > 0.0f
                ? voice.ageSeconds / voice.durationSeconds
                : 1.0f;

            if (ratio > oldestRatio) {
                oldestRatio = ratio;
                slot = &voice;
            }
        }
    }

    const CueProfile profile =
        profileFor(command.cue);

    *slot = {};
    slot->active = true;
    slot->cue = command.cue;
    slot->gain = command.gain;
    slot->durationSeconds =
        std::max(profile.duration, 0.01f);
    slot->phaseIncrement =
        2.0f * kPi *
        profile.frequency /
        std::max(sampleRate_, 8000.0f);
    slot->noiseState =
        0x9E3779B9U ^
        (static_cast<std::uint32_t>(
             command.cue) + 1U) *
            0x85EBCA6BU;
}

float AndroidAudioEngine::renderVoice(
    Voice& voice,
    float sampleRate) noexcept {
    if (!voice.active) {
        return 0.0f;
    }

    const CueProfile profile =
        profileFor(voice.cue);

    const float progress =
        std::clamp(
            voice.ageSeconds /
                std::max(
                    voice.durationSeconds,
                    0.001f),
            0.0f,
            1.0f);

    const float envelope =
        (1.0f - progress) *
        std::min(
            voice.ageSeconds * 220.0f,
            1.0f);

    voice.noiseState =
        voice.noiseState *
            1664525U +
        1013904223U;

    const float noise =
        static_cast<float>(
            static_cast<std::int32_t>(
                voice.noiseState >> 9U) -
            4194304) /
        4194304.0f;

    const float tone =
        std::sin(
            voice.phase);

    const float pitchMultiplier =
        std::max(
            0.12f,
            1.0f -
                profile.pitchFall *
                    progress);

    voice.phase +=
        voice.phaseIncrement *
        pitchMultiplier;

    if (voice.phase > 2.0f * kPi) {
        voice.phase -= 2.0f * kPi;
    }

    voice.ageSeconds +=
        1.0f /
        std::max(
            sampleRate,
            8000.0f);

    if (voice.ageSeconds >=
        voice.durationSeconds) {
        voice.active = false;
    }

    return (
        tone * profile.toneMix +
        noise * profile.noiseMix) *
        envelope *
        voice.gain *
        0.34f;
}

aaudio_data_callback_result_t
AndroidAudioEngine::dataCallback(
    AAudioStream*,
    void* userData,
    void* audioData,
    std::int32_t numFrames) noexcept {
    auto* engine =
        static_cast<AndroidAudioEngine*>(
            userData);

    if (engine == nullptr ||
        audioData == nullptr ||
        numFrames <= 0) {
        return AAUDIO_CALLBACK_RESULT_CONTINUE;
    }

    return engine->render(
        static_cast<float*>(
            audioData),
        numFrames);
}

void AndroidAudioEngine::errorCallback(
    AAudioStream*,
    void* userData,
    aaudio_result_t error) noexcept {
    auto* engine =
        static_cast<AndroidAudioEngine*>(
            userData);

    if (engine == nullptr) {
        return;
    }

    if (error == AAUDIO_ERROR_DISCONNECTED) {
        engine->ready_.store(
            false,
            std::memory_order_release);
        engine->disconnected_.store(
            true,
            std::memory_order_release);
    }
}

aaudio_data_callback_result_t
AndroidAudioEngine::render(
    float* output,
    std::int32_t numFrames) noexcept {
    Command command{};

    while (commands_.tryPop(command)) {
        startVoice(command);
    }

    for (std::int32_t frame = 0;
         frame < numFrames;
         ++frame) {
        float mixed = 0.0f;

        for (auto& voice : voices_) {
            mixed +=
                renderVoice(
                    voice,
                    sampleRate_);
        }

        const float sample =
            clampSample(mixed);

        output[frame * 2] = sample;
        output[frame * 2 + 1] = sample;
    }

    return AAUDIO_CALLBACK_RESULT_CONTINUE;
}

} // namespace xziel::android
