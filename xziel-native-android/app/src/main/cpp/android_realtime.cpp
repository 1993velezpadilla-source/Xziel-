#include "android_realtime.hpp"

#include <algorithm>
#include <cstring>

namespace xziel::android {

bool AndroidRealtimeBridge::initialize(
    JNIEnv* env,
    jobject activity) noexcept {
    reset();

    if (env == nullptr ||
        activity == nullptr) {
        return false;
    }

    jclass activityClass =
        env->GetObjectClass(activity);

    if (activityClass == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }
        return false;
    }

    baseUrlMethod_ =
        env->GetMethodID(
            activityClass,
            "getXzielMultiplayerBaseUrl",
            "()Ljava/lang/String;");

    testKeyMethod_ =
        env->GetMethodID(
            activityClass,
            "getXzielMultiplayerTestKey",
            "()Ljava/lang/String;");

    defaultRoomMethod_ =
        env->GetMethodID(
            activityClass,
            "getXzielMultiplayerDefaultRoom",
            "()Ljava/lang/String;");

    displayNameMethod_ =
        env->GetMethodID(
            activityClass,
            "getXzielMultiplayerDisplayName",
            "()Ljava/lang/String;");

    connectMethod_ =
        env->GetMethodID(
            activityClass,
            "connectXzielRealtime",
            "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;)Z");

    disconnectMethod_ =
        env->GetMethodID(
            activityClass,
            "disconnectXzielRealtime",
            "()V");

    sendMethod_ =
        env->GetMethodID(
            activityClass,
            "sendXzielRealtime",
            "([B)Z");

    pollMethod_ =
        env->GetMethodID(
            activityClass,
            "pollXzielRealtime",
            "()[B");

    stateMethod_ =
        env->GetMethodID(
            activityClass,
            "getXzielRealtimeState",
            "()I");

    env->DeleteLocalRef(activityClass);

    if (env->ExceptionCheck()) {
        env->ExceptionClear();
        reset();
        return false;
    }

    if (baseUrlMethod_ == nullptr ||
        testKeyMethod_ == nullptr ||
        defaultRoomMethod_ == nullptr ||
        displayNameMethod_ == nullptr ||
        connectMethod_ == nullptr ||
        disconnectMethod_ == nullptr ||
        sendMethod_ == nullptr ||
        pollMethod_ == nullptr ||
        stateMethod_ == nullptr) {
        reset();
        return false;
    }

    env_ = env;
    activity_ = activity;
    return true;
}

void AndroidRealtimeBridge::reset() noexcept {
    env_ = nullptr;
    activity_ = nullptr;
    baseUrlMethod_ = nullptr;
    testKeyMethod_ = nullptr;
    defaultRoomMethod_ = nullptr;
    displayNameMethod_ = nullptr;
    connectMethod_ = nullptr;
    disconnectMethod_ = nullptr;
    sendMethod_ = nullptr;
    pollMethod_ = nullptr;
    stateMethod_ = nullptr;
}

std::string AndroidRealtimeBridge::callString(
    jmethodID method) noexcept {
    if (env_ == nullptr ||
        activity_ == nullptr ||
        method == nullptr) {
        return {};
    }

    auto value =
        static_cast<jstring>(
            env_->CallObjectMethod(
                activity_,
                method));

    if (env_->ExceptionCheck()) {
        env_->ExceptionClear();
        return {};
    }

    if (value == nullptr) {
        return {};
    }

    const char* chars =
        env_->GetStringUTFChars(
            value,
            nullptr);

    if (chars == nullptr) {
        env_->DeleteLocalRef(value);
        if (env_->ExceptionCheck()) {
            env_->ExceptionClear();
        }
        return {};
    }

    std::string result(chars);

    env_->ReleaseStringUTFChars(
        value,
        chars);
    env_->DeleteLocalRef(value);

    return result;
}

std::string AndroidRealtimeBridge::configuredBaseUrl() noexcept {
    return callString(baseUrlMethod_);
}

std::string AndroidRealtimeBridge::configuredTestKey() noexcept {
    return callString(testKeyMethod_);
}

std::string AndroidRealtimeBridge::configuredDefaultRoom() noexcept {
    return callString(defaultRoomMethod_);
}

std::string AndroidRealtimeBridge::configuredDisplayName() noexcept {
    return callString(displayNameMethod_);
}

bool AndroidRealtimeBridge::connect(
    const std::string& baseUrl,
    const std::string& roomCode,
    const std::string& displayName,
    const std::string& testKey) noexcept {
    if (env_ == nullptr ||
        activity_ == nullptr ||
        connectMethod_ == nullptr ||
        baseUrl.empty() ||
        roomCode.empty()) {
        return false;
    }

    jstring base =
        env_->NewStringUTF(
            baseUrl.c_str());
    jstring room =
        env_->NewStringUTF(
            roomCode.c_str());
    jstring name =
        env_->NewStringUTF(
            displayName.c_str());
    jstring key =
        env_->NewStringUTF(
            testKey.c_str());

    if (base == nullptr ||
        room == nullptr ||
        name == nullptr ||
        key == nullptr) {
        if (base != nullptr) env_->DeleteLocalRef(base);
        if (room != nullptr) env_->DeleteLocalRef(room);
        if (name != nullptr) env_->DeleteLocalRef(name);
        if (key != nullptr) env_->DeleteLocalRef(key);
        if (env_->ExceptionCheck()) {
            env_->ExceptionClear();
        }
        return false;
    }

    const jboolean connected =
        env_->CallBooleanMethod(
            activity_,
            connectMethod_,
            base,
            room,
            name,
            key);

    env_->DeleteLocalRef(base);
    env_->DeleteLocalRef(room);
    env_->DeleteLocalRef(name);
    env_->DeleteLocalRef(key);

    if (env_->ExceptionCheck()) {
        env_->ExceptionClear();
        return false;
    }

    return connected == JNI_TRUE;
}

void AndroidRealtimeBridge::disconnect() noexcept {
    if (env_ == nullptr ||
        activity_ == nullptr ||
        disconnectMethod_ == nullptr) {
        return;
    }

    env_->CallVoidMethod(
        activity_,
        disconnectMethod_);

    if (env_->ExceptionCheck()) {
        env_->ExceptionClear();
    }
}

bool AndroidRealtimeBridge::send(
    std::span<const std::byte> payload) noexcept {
    if (env_ == nullptr ||
        activity_ == nullptr ||
        sendMethod_ == nullptr ||
        payload.empty() ||
        payload.size() > 1200U) {
        return false;
    }

    jbyteArray array =
        env_->NewByteArray(
            static_cast<jsize>(
                payload.size()));

    if (array == nullptr) {
        if (env_->ExceptionCheck()) {
            env_->ExceptionClear();
        }
        return false;
    }

    env_->SetByteArrayRegion(
        array,
        0,
        static_cast<jsize>(
            payload.size()),
        reinterpret_cast<const jbyte*>(
            payload.data()));

    if (env_->ExceptionCheck()) {
        env_->ExceptionClear();
        env_->DeleteLocalRef(array);
        return false;
    }

    const jboolean result =
        env_->CallBooleanMethod(
            activity_,
            sendMethod_,
            array);

    env_->DeleteLocalRef(array);

    if (env_->ExceptionCheck()) {
        env_->ExceptionClear();
        return false;
    }

    return result == JNI_TRUE;
}

bool AndroidRealtimeBridge::poll(
    std::span<std::byte> destination,
    std::size_t& written) noexcept {
    written = 0U;

    if (env_ == nullptr ||
        activity_ == nullptr ||
        pollMethod_ == nullptr ||
        destination.empty()) {
        return false;
    }

    auto array =
        static_cast<jbyteArray>(
            env_->CallObjectMethod(
                activity_,
                pollMethod_));

    if (env_->ExceptionCheck()) {
        env_->ExceptionClear();
        return false;
    }

    if (array == nullptr) {
        return false;
    }

    const jsize length =
        env_->GetArrayLength(array);

    if (length <= 0 ||
        static_cast<std::size_t>(length) >
            destination.size()) {
        env_->DeleteLocalRef(array);
        return false;
    }

    env_->GetByteArrayRegion(
        array,
        0,
        length,
        reinterpret_cast<jbyte*>(
            destination.data()));

    env_->DeleteLocalRef(array);

    if (env_->ExceptionCheck()) {
        env_->ExceptionClear();
        return false;
    }

    written =
        static_cast<std::size_t>(
            length);
    return true;
}

int AndroidRealtimeBridge::state() noexcept {
    if (env_ == nullptr ||
        activity_ == nullptr ||
        stateMethod_ == nullptr) {
        return 0;
    }

    const jint result =
        env_->CallIntMethod(
            activity_,
            stateMethod_);

    if (env_->ExceptionCheck()) {
        env_->ExceptionClear();
        return 0;
    }

    return static_cast<int>(result);
}

} // namespace xziel::android
