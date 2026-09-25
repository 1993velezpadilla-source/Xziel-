#pragma once

#include <android/sensor.h>
#include <game-activity/native_app_glue/android_native_app_glue.h>

#include "xziel/engine.hpp"
#include "xziel/fixed_tick_input_latch.hpp"
#include "xziel/mobile_controls.hpp"

#include <array>
#include <cstdint>

namespace xziel::android {

struct AndroidInputSnapshot {
    xziel::InputState input{};
    xziel::MobileMovementButtons movementButtons{};

    xziel::Vec2 moveAnchorNormalized{
        0.17f,
        0.74f,
    };

    bool moveActive = false;
    bool firePressed = false;
    bool restartPressed = false;
    bool gyroAvailable = false;
};

class AndroidInputAdapter final {
public:
    AndroidInputAdapter() = default;
    ~AndroidInputAdapter();

    AndroidInputAdapter(const AndroidInputAdapter&) = delete;
    AndroidInputAdapter& operator=(const AndroidInputAdapter&) = delete;

    [[nodiscard]] bool initialize(
        android_app* app,
        const char* packageName) noexcept;

    void shutdown() noexcept;

    void onResume() noexcept;
    void onPause() noexcept;

    // Android Surface rotation constants: 0, 1, 2, 3 correspond to
    // ROTATION_0/90/180/270. Gyro device axes are remapped into current screen
    // axes before entering the engine input snapshot.
    void setDisplayRotation(int rotation) noexcept;

    void beginFrame(float deltaSeconds) noexcept;

    void setInteractAvailable(
        bool available) noexcept;

    void setRestartAvailable(
        bool available) noexcept;

    // One-shot touch actions survive render frames with zero fixed simulation
    // ticks. Call this only after at least one fixed tick had a chance to
    // consume the current snapshot.
    void acknowledgeFixedTickActions() noexcept;

    void handleLooperIdentifier(int identifier) noexcept;

    void consumeInputBuffer(
        android_app* app,
        int viewportWidth,
        int viewportHeight) noexcept;

    [[nodiscard]] const AndroidInputSnapshot&
    snapshot() const noexcept;

    [[nodiscard]] static int sensorLooperIdentifier() noexcept;

private:
    enum class TouchRole : std::uint8_t {
        None,
        Move,
        Look,
        Fire,
        Aim,
        Reload,
        Interact,
        Jump,
        Stance,
        Restart,
    };

    struct TouchPointer {
        int32_t id = -1;
        float x = 0.0f;
        float y = 0.0f;
        float previousX = 0.0f;
        float previousY = 0.0f;
        float anchorX = 0.0f;
        float anchorY = 0.0f;

        TouchRole role = TouchRole::None;
        bool down = false;
    };

    [[nodiscard]] TouchPointer* findPointer(
        int32_t id) noexcept;

    [[nodiscard]] const TouchPointer* findPointer(
        int32_t id) const noexcept;

    [[nodiscard]] TouchPointer* acquirePointer(
        int32_t id) noexcept;

    void releasePointer(int32_t id) noexcept;
    void releaseAllPointers() noexcept;

    [[nodiscard]] TouchRole chooseRole(
        float x,
        float y,
        int width,
        int height) const noexcept;

    void updateDerivedState(
        int width,
        int height) noexcept;

    void processMotionEvent(
        const GameActivityMotionEvent& event,
        int width,
        int height) noexcept;

    [[nodiscard]] static bool insideButton(
        float x,
        float y,
        int width,
        int height,
        float normalizedCenterX,
        float normalizedCenterY,
        float normalizedRadius) noexcept;

    ASensorManager* sensorManager_ = nullptr;
    const ASensor* gyroscope_ = nullptr;
    ASensorEventQueue* sensorQueue_ = nullptr;

    std::array<TouchPointer, 8> pointers_{};

    AndroidInputSnapshot snapshot_{};

    bool sensorsEnabled_ = false;
    xziel::FixedTickInputPulseLatch fixedTickPulses_{};
    bool aimToggled_ = false;
    bool restartPressedThisFrame_ = false;

    float stanceHeldSeconds_ = 0.0f;
    int displayRotation_ = 0;
    bool interactAvailable_ = false;
    bool restartAvailable_ = false;
};

} // namespace xziel::android
