#pragma once

#include <jni.h>

#include "xziel/haptics.hpp"

namespace xziel::android {

class AndroidHapticsBridge final {
public:
    AndroidHapticsBridge() = default;

    [[nodiscard]] bool initialize(
        JNIEnv* env,
        jobject activity) noexcept;

    void reset() noexcept;

    [[nodiscard]] const HapticCapabilities&
    capabilities() const noexcept;

    void play(
        const HapticCommand& command) noexcept;

private:
    JNIEnv* env_ = nullptr;
    jobject activity_ = nullptr;

    jmethodID playMethod_ = nullptr;

    HapticCapabilities capabilities_{};
};

} // namespace xziel::android
