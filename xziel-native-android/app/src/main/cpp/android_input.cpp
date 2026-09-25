#include "android_input.hpp"

#include <android/input.h>
#include <android/log.h>
#include <android/looper.h>

#include <algorithm>
#include <cmath>
#include <cstring>

namespace xziel::android {

namespace {

constexpr const char* kTag = "XzielInput";
constexpr int kSensorLooperId = LOOPER_ID_USER + 37;

float clamp01(float value) noexcept {
    if (!std::isfinite(value)) {
        return 0.0f;
    }
    return std::clamp(value, 0.0f, 1.0f);
}

float length(float x, float y) noexcept {
    return std::sqrt(x * x + y * y);
}

float pointerX(const GameActivityPointerAxes& pointer) noexcept {
    return GameActivityPointerAxes_getAxisValue(
        &pointer,
        AMOTION_EVENT_AXIS_X);
}

float pointerY(const GameActivityPointerAxes& pointer) noexcept {
    return GameActivityPointerAxes_getAxisValue(
        &pointer,
        AMOTION_EVENT_AXIS_Y);
}

} // namespace

AndroidInputAdapter::~AndroidInputAdapter() {
    shutdown();
}

bool AndroidInputAdapter::initialize(
    android_app* app,
    const char* packageName) noexcept {
    shutdown();

    if (app == nullptr ||
        app->looper == nullptr ||
        packageName == nullptr ||
        packageName[0] == '\0') {
        return false;
    }

    android_app_set_motion_event_filter(
        app,
        nullptr);
    android_app_set_key_event_filter(
        app,
        nullptr);

    sensorManager_ =
        ASensorManager_getInstanceForPackage(
            packageName);

    if (sensorManager_ == nullptr) {
        __android_log_print(
            ANDROID_LOG_INFO,
            kTag,
            "%s",
            "No sensor manager; touch remains available");
        return true;
    }

    gyroscope_ =
        ASensorManager_getDefaultSensor(
            sensorManager_,
            ASENSOR_TYPE_GYROSCOPE);

    if (gyroscope_ == nullptr) {
        __android_log_print(
            ANDROID_LOG_INFO,
            kTag,
            "%s",
            "No gyroscope; touch remains available");
        return true;
    }

    sensorQueue_ =
        ASensorManager_createEventQueue(
            sensorManager_,
            app->looper,
            kSensorLooperId,
            nullptr,
            nullptr);

    if (sensorQueue_ == nullptr) {
        gyroscope_ = nullptr;
        __android_log_print(
            ANDROID_LOG_INFO,
            kTag,
            "%s",
            "Unable to create gyro event queue");
        return true;
    }

    snapshot_.gyroAvailable = true;

    __android_log_print(
        ANDROID_LOG_INFO,
        kTag,
        "%s",
        "XZIEL_GYRO_AVAILABLE");

    return true;
}

void AndroidInputAdapter::shutdown() noexcept {
    onPause();

    if (sensorQueue_ != nullptr &&
        sensorManager_ != nullptr) {
        ASensorManager_destroyEventQueue(
            sensorManager_,
            sensorQueue_);
    }

    sensorQueue_ = nullptr;
    gyroscope_ = nullptr;
    sensorManager_ = nullptr;

    releaseAllPointers();
    snapshot_ = {};
    stanceHeldSeconds_ = 0.0f;
    aimToggled_ = false;
    restartAvailable_ = false;
    restartPressedThisFrame_ = false;
}

void AndroidInputAdapter::onResume() noexcept {
    if (sensorQueue_ == nullptr ||
        gyroscope_ == nullptr ||
        sensorsEnabled_) {
        return;
    }

    if (ASensorEventQueue_enableSensor(
            sensorQueue_,
            gyroscope_) < 0) {
        return;
    }

    const int minimumDelayUs =
        std::max(
            0,
            ASensor_getMinDelay(
                gyroscope_));

    // Request about 120 Hz where the sensor supports it, without asking for a
    // rate faster than the sensor's own advertised minimum delay.
    const int requestedDelayUs =
        std::max(
            minimumDelayUs,
            8333);

    (void) ASensorEventQueue_setEventRate(
        sensorQueue_,
        gyroscope_,
        requestedDelayUs);

    sensorsEnabled_ = true;
}

void AndroidInputAdapter::onPause() noexcept {
    if (sensorQueue_ != nullptr &&
        gyroscope_ != nullptr &&
        sensorsEnabled_) {
        (void) ASensorEventQueue_disableSensor(
            sensorQueue_,
            gyroscope_);
    }

    sensorsEnabled_ = false;
    snapshot_.input.gyroRadiansPerSecond = {};
}

void AndroidInputAdapter::setDisplayRotation(
    int rotation) noexcept {
    const int clampedRotation =
        std::clamp(rotation, 0, 3);

    if (displayRotation_ ==
        clampedRotation) {
        return;
    }

    displayRotation_ =
        clampedRotation;

    // Motion-event coordinates are expressed in the current surface
    // orientation. Any fingers that were already down before an orientation
    // change still carry anchors from the old coordinate system, which makes
    // the joystick/buttons jump or become effectively untouchable. Drop those
    // pointers and let the next touch acquire a fresh role/anchor.
    releaseAllPointers();

    stanceHeldSeconds_ = 0.0f;
    firePressedThisFrame_ = false;
    aimPressedThisFrame_ = false;
    aimToggled_ = false;
    reloadPressedThisFrame_ = false;
    interactPressedThisFrame_ = false;
    jumpPressedThisFrame_ = false;
    stancePressedThisFrame_ = false;

    snapshot_.input.move = {};
    snapshot_.input.look = {};
    snapshot_.input.fire = false;
    snapshot_.input.aim = false;
    snapshot_.input.reload = false;
    snapshot_.input.interact = false;
    snapshot_.input.jump = false;
    snapshot_.input.crouch = false;
    snapshot_.moveActive = false;
}

void AndroidInputAdapter::beginFrame(
    float deltaSeconds) noexcept {
    const float dt =
        (!std::isfinite(deltaSeconds) ||
         deltaSeconds < 0.0f)
        ? 0.0f
        : std::min(deltaSeconds, 0.10f);

    firePressedThisFrame_ = false;
    aimPressedThisFrame_ = false;
    reloadPressedThisFrame_ = false;
    interactPressedThisFrame_ = false;
    jumpPressedThisFrame_ = false;
    stancePressedThisFrame_ = false;
    restartPressedThisFrame_ = false;

    snapshot_.input.look = {};

    bool stanceDown = false;
    for (const auto& pointer : pointers_) {
        if (pointer.down &&
            pointer.role == TouchRole::Stance) {
            stanceDown = true;
            break;
        }
    }

    if (stanceDown) {
        stanceHeldSeconds_ += dt;
    } else {
        stanceHeldSeconds_ = 0.0f;
    }
}

void AndroidInputAdapter::setInteractAvailable(
    bool available) noexcept {
    interactAvailable_ = available;
}

void AndroidInputAdapter::setRestartAvailable(
    bool available) noexcept {
    if (restartAvailable_ == available) {
        return;
    }

    restartAvailable_ = available;
    releaseAllPointers();

    if (available) {
        aimToggled_ = false;
        stanceHeldSeconds_ = 0.0f;
        snapshot_.input = {};
        snapshot_.movementButtons = {};
        snapshot_.moveActive = false;
    }
}

void AndroidInputAdapter::handleLooperIdentifier(
    int identifier) noexcept {
    if (identifier != kSensorLooperId ||
        sensorQueue_ == nullptr) {
        return;
    }

    ASensorEvent events[16]{};

    while (true) {
        const ssize_t count =
            ASensorEventQueue_getEvents(
                sensorQueue_,
                events,
                16);

        if (count <= 0) {
            break;
        }

        for (ssize_t i = 0;
             i < count;
             ++i) {
            const auto& event = events[i];

            if (event.type !=
                ASENSOR_TYPE_GYROSCOPE) {
                continue;
            }

            const float x = event.vector.x;
            const float y = event.vector.y;
            const float z = event.vector.z;

            // Remap Android's fixed device coordinates into the active screen
            // coordinates. This keeps gyro aim consistent in landscape-left,
            // landscape-right and 180-degree device rotation.
            switch (displayRotation_) {
                case 1: // ROTATION_90
                    snapshot_.input.gyroRadiansPerSecond = {
                        y,
                        -x,
                        z,
                    };
                    break;

                case 2: // ROTATION_180
                    snapshot_.input.gyroRadiansPerSecond = {
                        -x,
                        -y,
                        z,
                    };
                    break;

                case 3: // ROTATION_270
                    snapshot_.input.gyroRadiansPerSecond = {
                        -y,
                        x,
                        z,
                    };
                    break;

                case 0:
                default:
                    snapshot_.input.gyroRadiansPerSecond = {
                        x,
                        y,
                        z,
                    };
                    break;
            }

            // Android's gyro pitch sign is opposite to XZIEL's touch-look
            // convention on the tested handset: tilting the phone upward was
            // pitching the camera downward. Keep yaw unchanged and make gyro
            // vertical motion agree with drag-look.
            snapshot_.input.gyroRadiansPerSecond.x =
                -snapshot_.input.gyroRadiansPerSecond.x;
        }
    }
}

void AndroidInputAdapter::consumeInputBuffer(
    android_app* app,
    int viewportWidth,
    int viewportHeight) noexcept {
    if (app == nullptr) {
        return;
    }

    android_input_buffer* buffer =
        android_app_swap_input_buffers(
            app);

    if (buffer == nullptr) {
        updateDerivedState(
            viewportWidth,
            viewportHeight);
        return;
    }

    for (uint64_t i = 0;
         i < buffer->motionEventsCount;
         ++i) {
        processMotionEvent(
            buffer->motionEvents[i],
            viewportWidth,
            viewportHeight);
    }

    if (buffer->motionEventsCount > 0) {
        android_app_clear_motion_events(
            buffer);
    }

    if (buffer->keyEventsCount > 0) {
        android_app_clear_key_events(
            buffer);
    }

    updateDerivedState(
        viewportWidth,
        viewportHeight);
}

const AndroidInputSnapshot&
AndroidInputAdapter::snapshot() const noexcept {
    return snapshot_;
}

int AndroidInputAdapter::sensorLooperIdentifier() noexcept {
    return kSensorLooperId;
}

AndroidInputAdapter::TouchPointer*
AndroidInputAdapter::findPointer(
    int32_t id) noexcept {
    for (auto& pointer : pointers_) {
        if (pointer.down &&
            pointer.id == id) {
            return &pointer;
        }
    }

    return nullptr;
}

const AndroidInputAdapter::TouchPointer*
AndroidInputAdapter::findPointer(
    int32_t id) const noexcept {
    for (const auto& pointer : pointers_) {
        if (pointer.down &&
            pointer.id == id) {
            return &pointer;
        }
    }

    return nullptr;
}

AndroidInputAdapter::TouchPointer*
AndroidInputAdapter::acquirePointer(
    int32_t id) noexcept {
    if (auto* existing =
            findPointer(id)) {
        return existing;
    }

    for (auto& pointer : pointers_) {
        if (!pointer.down) {
            pointer = {};
            pointer.id = id;
            pointer.down = true;
            return &pointer;
        }
    }

    return nullptr;
}

void AndroidInputAdapter::releasePointer(
    int32_t id) noexcept {
    if (auto* pointer =
            findPointer(id)) {
        *pointer = {};
        pointer->id = -1;
    }
}

void AndroidInputAdapter::releaseAllPointers() noexcept {
    for (auto& pointer : pointers_) {
        pointer = {};
        pointer.id = -1;
    }
}

AndroidInputAdapter::TouchRole
AndroidInputAdapter::chooseRole(
    float x,
    float y,
    int width,
    int height) const noexcept {
    if (width <= 0 || height <= 0) {
        return TouchRole::None;
    }

    if (restartAvailable_) {
        return insideButton(
                   x, y, width, height,
                   0.50f, 0.62f, 0.16f)
            ? TouchRole::Restart
            : TouchRole::None;
    }

    // Four familiar action areas, but only two are movement-specific:
    // Jump/Mantle and Stance. Fire/ADS remain weapon controls rather than
    // creating separate buttons for slide, dive, sprint, wall-run, etc.
    if (insideButton(
            x, y, width, height,
            0.695f, 0.790f, 0.044f)) {
        return TouchRole::Jump;
    }

    if (insideButton(
            x, y, width, height,
            0.915f, 0.800f, 0.044f)) {
        return TouchRole::Stance;
    }

    if (insideButton(
            x, y, width, height,
            0.885f, 0.585f, 0.073f)) {
        return TouchRole::Fire;
    }

    if (insideButton(
            x, y, width, height,
            0.695f, 0.575f, 0.047f)) {
        return TouchRole::Aim;
    }

    if (insideButton(
            x, y, width, height,
            0.805f, 0.785f, 0.044f)) {
        return TouchRole::Reload;
    }

    if (interactAvailable_ &&
        insideButton(
            x, y, width, height,
            0.605f, 0.675f, 0.050f)) {
        return TouchRole::Interact;
    }

    bool moveAssigned = false;
    bool lookAssigned = false;

    for (const auto& pointer : pointers_) {
        if (!pointer.down) {
            continue;
        }

        moveAssigned =
            moveAssigned ||
            pointer.role == TouchRole::Move;

        lookAssigned =
            lookAssigned ||
            pointer.role == TouchRole::Look;
    }

    // Match the proven NZ:P mobile acquisition zone: the whole lower-left
    // quadrant can acquire movement, while the actual joystick remains fixed
    // at its visual home. This makes thumb acquisition forgiving without
    // making movement direction itself float.
    if (x <
            static_cast<float>(width) *
                0.45f &&
        y >
            static_cast<float>(height) *
                0.30f) {
        return moveAssigned
            ? TouchRole::None
            : TouchRole::Move;
    }

    if (x <
        static_cast<float>(width) *
        0.45f) {
        return TouchRole::None;
    }

    return lookAssigned
        ? TouchRole::None
        : TouchRole::Look;
}

void AndroidInputAdapter::updateDerivedState(
    int width,
    int height) noexcept {
    snapshot_.input.move = {};
    snapshot_.input.fire =
        firePressedThisFrame_;
    snapshot_.input.aim =
        aimToggled_;
    snapshot_.input.reload =
        reloadPressedThisFrame_;
    snapshot_.input.interact =
        interactPressedThisFrame_;
    snapshot_.input.jump =
        jumpPressedThisFrame_;
    snapshot_.input.crouch =
        stancePressedThisFrame_;
    snapshot_.firePressed =
        firePressedThisFrame_;
    snapshot_.restartPressed =
        restartPressedThisFrame_;
    snapshot_.moveActive = false;
    snapshot_.moveAnchorNormalized = {
        0.17f,
        0.74f,
    };

    snapshot_.movementButtons.jumpPressed =
        jumpPressedThisFrame_;
    snapshot_.movementButtons.stancePressed =
        stancePressedThisFrame_;
    snapshot_.movementButtons.jumpHeld = false;
    snapshot_.movementButtons.stanceHeld = false;
    snapshot_.movementButtons.stanceHeldSeconds =
        stanceHeldSeconds_;
    snapshot_.movementButtons.movementCancelGesture =
        false;

    if (restartAvailable_) {
        snapshot_.input = {};
        snapshot_.movementButtons = {};
        snapshot_.moveActive = false;
        return;
    }

    if (width <= 0 || height <= 0) {
        return;
    }

    const float minDimension =
        static_cast<float>(
            std::min(width, height));

    // Proven NZ:P physical stick radius. 0.16 of the short dimension keeps
    // walk/sprint travel progressive instead of hitting 100% too early.
    const float joystickRadius =
        std::max(
            48.0f,
            minDimension * 0.16f);

    for (const auto& pointer : pointers_) {
        if (!pointer.down) {
            continue;
        }

        switch (pointer.role) {
            case TouchRole::Move: {
                snapshot_.moveActive = true;
                constexpr float kMoveDeadzone = 0.10f;

                snapshot_.moveAnchorNormalized = {
                    std::clamp(
                        pointer.anchorX /
                            static_cast<float>(width),
                        0.0f,
                        1.0f),
                    std::clamp(
                        pointer.anchorY /
                            static_cast<float>(height),
                        0.0f,
                        1.0f),
                };

                snapshot_.input.move =
                    xziel::resolveMobileJoystick(
                        pointer.x,
                        pointer.y,
                        pointer.anchorX,
                        pointer.anchorY,
                        joystickRadius,
                        kMoveDeadzone);
                break;
            }

            case TouchRole::Look:
                break;

            case TouchRole::Fire:
                snapshot_.input.fire = true;
                break;

            case TouchRole::Aim:
                break;

            case TouchRole::Reload:
                snapshot_.input.reload = true;
                break;

            case TouchRole::Interact:
                snapshot_.input.interact = true;
                break;

            case TouchRole::Jump:
                snapshot_.input.jump = true;
                snapshot_.movementButtons.jumpHeld =
                    true;
                break;

            case TouchRole::Stance:
                snapshot_.input.crouch = true;
                snapshot_.movementButtons.stanceHeld =
                    true;
                break;

            case TouchRole::Restart:
                break;

            case TouchRole::None:
                break;
        }
    }
}

void AndroidInputAdapter::processMotionEvent(
    const GameActivityMotionEvent& event,
    int width,
    int height) noexcept {
    const int action =
        event.action &
        AMOTION_EVENT_ACTION_MASK;

    if (action ==
        AMOTION_EVENT_ACTION_CANCEL) {
        releaseAllPointers();
        return;
    }

    std::uint32_t actionIndex = 0;

    if (action ==
            AMOTION_EVENT_ACTION_POINTER_DOWN ||
        action ==
            AMOTION_EVENT_ACTION_POINTER_UP) {
        actionIndex =
            static_cast<std::uint32_t>(
                (event.action &
                 AMOTION_EVENT_ACTION_POINTER_INDEX_MASK) >>
                AMOTION_EVENT_ACTION_POINTER_INDEX_SHIFT);
    }

    if (actionIndex >=
        event.pointerCount) {
        actionIndex = 0;
    }

    if (action ==
            AMOTION_EVENT_ACTION_DOWN ||
        action ==
            AMOTION_EVENT_ACTION_POINTER_DOWN) {
        const auto& source =
            event.pointers[actionIndex];

        auto* pointer =
            acquirePointer(source.id);

        if (pointer != nullptr) {
            pointer->x = pointerX(source);
            pointer->y = pointerY(source);
            pointer->previousX = pointerX(source);
            pointer->previousY = pointerY(source);
            pointer->anchorX = pointerX(source);
            pointer->anchorY = pointerY(source);
            pointer->role =
                chooseRole(
                    pointerX(source),
                    pointerY(source),
                    width,
                    height);

            if (pointer->role ==
                    TouchRole::Move &&
                width > 0 &&
                height > 0) {
                constexpr float kMoveCenterX = 0.17f;
                constexpr float kMoveCenterY = 0.74f;

                const float minDimension =
                    static_cast<float>(
                        std::min(width, height));

                const float fixedCenterX =
                    kMoveCenterX *
                    static_cast<float>(width);

                const float fixedCenterY =
                    kMoveCenterY *
                    static_cast<float>(height);

                const float fromHomeX =
                    pointer->x -
                    fixedCenterX;

                const float fromHomeY =
                    pointer->y -
                    fixedCenterY;

                // Inside/near the visible home pad, preserve the familiar
                // fixed joystick. A forgiving lower-left acquisition touch
                // farther away becomes a floating stick anchored under the
                // thumb, so movement starts at zero instead of jumping.
                const float fixedAcquireRadius =
                    std::max(
                        52.0f,
                        minDimension *
                            0.115f);

                const bool useFixedHome =
                    fromHomeX * fromHomeX +
                        fromHomeY * fromHomeY <=
                    fixedAcquireRadius *
                        fixedAcquireRadius;

                if (useFixedHome) {
                    pointer->anchorX =
                        fixedCenterX;
                    pointer->anchorY =
                        fixedCenterY;
                }

                __android_log_print(
                    ANDROID_LOG_INFO,
                    kTag,
                    "XZIEL_MOVE_ANCHOR mode=%s x=%.3f y=%.3f",
                    useFixedHome
                        ? "fixed"
                        : "floating",
                    static_cast<double>(
                        pointer->anchorX /
                        static_cast<float>(width)),
                    static_cast<double>(
                        pointer->anchorY /
                        static_cast<float>(height)));
            }

            if (pointer->role ==
                TouchRole::Fire) {
                firePressedThisFrame_ = true;
            } else if (
                pointer->role ==
                TouchRole::Aim) {
                aimPressedThisFrame_ = true;
                aimToggled_ = !aimToggled_;
                __android_log_print(
                    ANDROID_LOG_INFO,
                    kTag,
                    "XZIEL_ADS_TOGGLE state=%d",
                    aimToggled_ ? 1 : 0);
            } else if (
                pointer->role ==
                TouchRole::Reload) {
                reloadPressedThisFrame_ = true;
            } else if (
                pointer->role ==
                TouchRole::Interact) {
                interactPressedThisFrame_ = true;
            } else if (
                pointer->role ==
                TouchRole::Jump) {
                jumpPressedThisFrame_ = true;
            } else if (
                pointer->role ==
                TouchRole::Stance) {
                stancePressedThisFrame_ = true;
                stanceHeldSeconds_ = 0.0f;
            } else if (
                pointer->role ==
                TouchRole::Restart) {
                restartPressedThisFrame_ = true;
                __android_log_print(
                    ANDROID_LOG_INFO,
                    kTag,
                    "XZIEL_RESTART_PRESSED");
            }
        }
    }

    if (action ==
        AMOTION_EVENT_ACTION_MOVE) {
        for (std::uint32_t i = 0;
             i < event.pointerCount;
             ++i) {
            const auto& source =
                event.pointers[i];

            auto* pointer =
                findPointer(source.id);

            if (pointer == nullptr) {
                continue;
            }

            const float oldX =
                pointer->x;
            const float oldY =
                pointer->y;

            pointer->previousX = oldX;
            pointer->previousY = oldY;
            pointer->x = pointerX(source);
            pointer->y = pointerY(source);

            if ((pointer->role ==
                     TouchRole::Look ||
                 pointer->role ==
                     TouchRole::Fire) &&
                width > 0 &&
                height > 0) {
                // NZ:P proven mobile behavior: dragging the FIRE control keeps
                // rotating the camera while fire remains held. ADS uses the
                // same 0.62 camera multiplier as the established port.
                const float lookScale =
                    aimToggled_
                    ? 0.62f
                    : 1.0f;

                snapshot_.input.look.x +=
                    (pointer->x - oldX) /
                    static_cast<float>(
                        width) *
                    lookScale;

                snapshot_.input.look.y +=
                    (pointer->y - oldY) /
                    static_cast<float>(
                        height) *
                    lookScale;
            }
        }
    }

    if (action ==
            AMOTION_EVENT_ACTION_UP ||
        action ==
            AMOTION_EVENT_ACTION_POINTER_UP) {
        if (event.pointerCount > 0) {
            releasePointer(
                event.pointers[
                    actionIndex].id);
        }
    }
}

bool AndroidInputAdapter::insideButton(
    float x,
    float y,
    int width,
    int height,
    float normalizedCenterX,
    float normalizedCenterY,
    float normalizedRadius) noexcept {
    if (width <= 0 || height <= 0) {
        return false;
    }

    const float centerX =
        normalizedCenterX *
        static_cast<float>(width);

    const float centerY =
        normalizedCenterY *
        static_cast<float>(height);

    const float radius =
        normalizedRadius *
        static_cast<float>(
            std::min(width, height));

    const float dx = x - centerX;
    const float dy = y - centerY;

    return dx * dx + dy * dy <=
        radius * radius;
}

} // namespace xziel::android
