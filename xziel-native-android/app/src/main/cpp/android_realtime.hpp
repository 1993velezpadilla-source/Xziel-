#pragma once

#include <jni.h>

#include <cstddef>
#include <span>
#include <string>

namespace xziel::android {

class AndroidRealtimeBridge final {
public:
    [[nodiscard]] bool initialize(
        JNIEnv* env,
        jobject activity) noexcept;

    void reset() noexcept;

    [[nodiscard]] std::string configuredBaseUrl() noexcept;
    [[nodiscard]] std::string configuredTestKey() noexcept;
    [[nodiscard]] std::string configuredDefaultRoom() noexcept;
    [[nodiscard]] std::string configuredDisplayName() noexcept;

    [[nodiscard]] bool connect(
        const std::string& baseUrl,
        const std::string& roomCode,
        const std::string& displayName,
        const std::string& testKey) noexcept;

    void disconnect() noexcept;

    [[nodiscard]] bool send(
        std::span<const std::byte> payload) noexcept;

    [[nodiscard]] bool poll(
        std::span<std::byte> destination,
        std::size_t& written) noexcept;

    [[nodiscard]] int state() noexcept;

private:
    [[nodiscard]] std::string callString(
        jmethodID method) noexcept;

    JNIEnv* env_ = nullptr;
    jobject activity_ = nullptr;

    jmethodID baseUrlMethod_ = nullptr;
    jmethodID testKeyMethod_ = nullptr;
    jmethodID defaultRoomMethod_ = nullptr;
    jmethodID displayNameMethod_ = nullptr;
    jmethodID connectMethod_ = nullptr;
    jmethodID disconnectMethod_ = nullptr;
    jmethodID sendMethod_ = nullptr;
    jmethodID pollMethod_ = nullptr;
    jmethodID stateMethod_ = nullptr;
};

} // namespace xziel::android
