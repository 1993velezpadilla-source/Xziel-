#include "android_haptics.hpp"

#include <algorithm>
#include <cmath>

namespace xziel::android {

bool AndroidHapticsBridge::initialize(
    JNIEnv* env,
    jobject activity) noexcept {
    reset();

    if (env == nullptr ||
        activity == nullptr) {
        return false;
    }

    jclass activityClass =
        env->GetObjectClass(
            activity);

    if (activityClass == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }
        return false;
    }

    const jmethodID hasVibratorMethod =
        env->GetMethodID(
            activityClass,
            "hasXzielVibrator",
            "()Z");

    const jmethodID hasAmplitudeMethod =
        env->GetMethodID(
            activityClass,
            "hasXzielAmplitudeControl",
            "()Z");

    playMethod_ =
        env->GetMethodID(
            activityClass,
            "playXzielHaptic",
            "(FF)V");

    if (env->ExceptionCheck()) {
        env->ExceptionClear();
        env->DeleteLocalRef(
            activityClass);
        reset();
        return false;
    }

    if (hasVibratorMethod == nullptr ||
        hasAmplitudeMethod == nullptr ||
        playMethod_ == nullptr) {
        env->DeleteLocalRef(
            activityClass);
        reset();
        return false;
    }

    const jboolean hasVibrator =
        env->CallBooleanMethod(
            activity,
            hasVibratorMethod);

    const jboolean hasAmplitude =
        env->CallBooleanMethod(
            activity,
            hasAmplitudeMethod);

    if (env->ExceptionCheck()) {
        env->ExceptionClear();
        env->DeleteLocalRef(
            activityClass);
        reset();
        return false;
    }

    env->DeleteLocalRef(
        activityClass);

    env_ = env;
    activity_ = activity;

    capabilities_.hasVibrator =
        hasVibrator == JNI_TRUE;

    capabilities_.hasAmplitudeControl =
        hasAmplitude == JNI_TRUE;

    // The prototype intentionally uses the portable one-shot path. Rich
    // Android compositions/envelopes can be enabled later after per-device
    // capability probing is in place.
    capabilities_.hasCompositionPrimitives = false;
    capabilities_.hasEnvelopeEffects = false;

    return true;
}

void AndroidHapticsBridge::reset() noexcept {
    env_ = nullptr;
    activity_ = nullptr;
    playMethod_ = nullptr;
    capabilities_ = {};
    capabilities_.hasVibrator = false;
}

const HapticCapabilities&
AndroidHapticsBridge::capabilities() const noexcept {
    return capabilities_;
}

void AndroidHapticsBridge::play(
    const HapticCommand& command) noexcept {
    if (!command.play ||
        !capabilities_.hasVibrator ||
        env_ == nullptr ||
        activity_ == nullptr ||
        playMethod_ == nullptr) {
        return;
    }

    const float amplitude =
        std::clamp(
            std::isfinite(command.amplitude)
                ? command.amplitude
                : 0.0f,
            0.0f,
            1.0f);

    const float durationMs =
        std::clamp(
            std::isfinite(
                command.durationSeconds)
                ? command.durationSeconds *
                    1000.0f
                : 0.0f,
            1.0f,
            120.0f);

    jvalue arguments[2]{};
    arguments[0].f = amplitude;
    arguments[1].f = durationMs;

    env_->CallVoidMethodA(
        activity_,
        playMethod_,
        arguments);

    if (env_->ExceptionCheck()) {
        env_->ExceptionClear();
    }
}

} // namespace xziel::android
