#include "android_haptics.hpp"
#include "android_audio.hpp"
#include "android_input.hpp"
#include "vulkan_clear_renderer.hpp"

#include <android/log.h>
#include <android/native_window.h>
#include <game-activity/native_app_glue/android_native_app_glue.h>

#include "xziel/android_runtime.hpp"
#include "xziel/camera_rig.hpp"
#include "xziel/engine.hpp"
#include "xziel/door.hpp"
#include "xziel/environment.hpp"
#include "xziel/fps_player.hpp"
#include "xziel/gameplay_events.hpp"
#include "xziel/hitscan.hpp"
#include "xziel/horde_director.hpp"
#include "xziel/haptics.hpp"
#include "xziel/horror.hpp"
#include "xziel/interaction.hpp"
#include "xziel/map_runtime.hpp"
#include "xziel/player_vitals.hpp"
#include "xziel/quest_runtime.hpp"
#include "xziel/performance.hpp"
#include "xziel/render_features.hpp"
#include "xziel/renderer_watchdog.hpp"
#include "xziel/runtime_policy.hpp"
#include "xziel/score.hpp"
#include "xziel/weapon.hpp"
#include "xziel/weapon_catalog.hpp"
#include "xziel/zombie_actor.hpp"
#include "xziel/zombie_hit_regions.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>

namespace {

constexpr const char* kTag = "XzielNative";
constexpr const char* kPackageName =
    "com.xziel.engineprototype";

constexpr float kPi =
    3.14159265358979323846f;

constexpr float kDegreesToRadians =
    kPi / 180.0f;

constexpr std::uint32_t kPrototypePowerSwitchId =
    1001U;

constexpr xziel::Vec3 kPrototypePowerSwitchPosition{
    -2.05f,
    -0.60f,
    0.45f,
};

constexpr std::uint32_t kPrototypeDoorId =
    1002U;

constexpr std::uint32_t kPrototypeDoorCost =
    500U;

constexpr xziel::Vec3 kPrototypeDoorInteractionPosition{
    0.0f,
    -0.45f,
    1.34f,
};

constexpr std::uint32_t kPrototypeWindowId =
    1004U;

constexpr xziel::Vec3 kPrototypeWindowInteractionPosition{
    0.0f,
    -0.30f,
    2.48f,
};

const xziel::Aabb kPrototypeWindowObstacle{
    .minimum = {
        -0.82f,
        -1.58f,
        2.62f,
    },
    .maximum = {
        0.82f,
        1.02f,
        2.84f,
    },
};

constexpr std::uint32_t kPrototypeWeaponBuyId =
    1003U;

constexpr std::uint32_t kPrototypeWeaponBuyCost =
    750U;

constexpr xziel::Vec3 kPrototypeWeaponBuyPosition{
    2.25f,
    -0.58f,
    -0.80f,
};

const xziel::Aabb kPrototypeCenterObstacle{
    .minimum = {
        -0.58f,
        -1.60f,
        -0.25f,
    },
    .maximum = {
        0.58f,
        0.95f,
        0.95f,
    },
};

const xziel::Aabb kPrototypeDoorObstacle{
    .minimum = {
        -2.72f,
        -1.60f,
        1.46f,
    },
    .maximum = {
        2.72f,
        1.05f,
        1.68f,
    },
};

struct NativeAppState {
    xziel::AndroidRuntimeStateMachine runtime{};
    xziel::RendererWatchdog watchdog{};
    xziel::Engine engine{};
    xziel::FpsPlayerController player{};

    xziel::WeaponProfile weaponProfile =
        xziel::makeWeaponProfile(
            xziel::WeaponArchetype::Sidearm);

    xziel::WeaponController weapon{
        weaponProfile.controller};

    xziel::HordeDirector horde{};
    xziel::ScoreSystem score{
        xziel::ScoreConfig{
            .startingPoints = 500U,
        }};

    xziel::InteractionSystem interaction{};
    xziel::InteractionFrame interactionFrame{};
    xziel::MapRuntime mapRuntime{};
    xziel::MapDefinition mapDefinition{};
    xziel::GameplayEventQueue gameplayEvents{};
    xziel::QuestRuntime questRuntime{};

    xziel::PlayerVitals vitals{};
    xziel::HorrorDirector horror{};
    xziel::HorrorFrame horrorFrame{};

    xziel::EnvironmentSystem environment{};
    xziel::EnvironmentFrame environmentFrame{};

    xziel::WaterSystem water{};
    xziel::WaterSurfaceState waterFrame{};

    xziel::WeatherConfig stormWeather{};
    xziel::WeatherConfig calmWeather{};
    bool stormEnabled = true;

    bool prototypeWeaponBuyPurchased = false;

    float prototypeDoorOpenAlpha = 0.0f;
    float purchaseDeniedSeconds = 0.0f;

    xziel::PerformanceGovernor performance{};
    xziel::RenderWorkload renderWorkload{};
    xziel::ReflectionPlanner reflectionPlanner{};
    std::uint64_t reflectionPlannerFrame = 0;
    xziel::RuntimePolicyPlanner runtimePolicyPlanner{};

    xziel::CameraRig cameraRig{};
    xziel::HapticsPlanner haptics{};
    xziel::android::AndroidHapticsBridge hapticsBridge{};
    xziel::android::AndroidAudioEngine audio{};
    xziel::android::AndroidInputAdapter input{};
    xziel::android::VulkanClearRenderer renderer{};

    bool hasWindow = false;

    JNIEnv* jniEnv = nullptr;
    jobject javaActivity = nullptr;
    JavaVM* javaVm = nullptr;
    bool attachedToJvm = false;

    std::chrono::steady_clock::time_point start =
        std::chrono::steady_clock::now();

    std::chrono::steady_clock::time_point lastFrame =
        std::chrono::steady_clock::now();

    bool hasLastFrame = false;
    float stridePhase = 0.0f;

    float pendingRecoilPitch = 0.0f;
    float pendingRecoilYaw = 0.0f;

    float hitMarkerSeconds = 0.0f;
    float criticalHitSeconds = 0.0f;
    float impactFxSeconds = 0.0f;
    xziel::Vec3 impactPoint{};

    float decapFxSeconds = 0.0f;
    xziel::Vec3 decapOrigin{};
    xziel::Vec3 decapDirection{};

    float muzzleFlashSeconds = 0.0f;
    float zombieAttackFlashSeconds = 0.0f;
    float scorePulseSeconds = 0.0f;
    float hapticElapsedSeconds = 1.0f;

    xziel::ThermalLevel thermalLevel =
        xziel::ThermalLevel::Nominal;

    bool batterySaver = false;
    float displayRefreshHz = 60.0f;

    xziel::MemoryPressure memoryPressure =
        xziel::MemoryPressure::Normal;

    float memoryPressureSeconds = 0.0f;
    float thermalPollSeconds = 1.0f;
};

void configurePrototypeMap(
    NativeAppState& state) noexcept {
    auto& map = state.mapDefinition;
    map = {};

    const auto addVisualBox =
        [&](std::uint32_t id,
            xziel::Vec3 center,
            xziel::Vec3 halfExtents,
            std::uint32_t materialId) noexcept {
            if (map.boxCount >= map.boxes.size()) {
                return;
            }

            map.boxes[map.boxCount++] = {
                .id = id,
                .center = center,
                .halfExtents = halfExtents,
                .materialId = materialId,
                .visible = true,
                .blocksPlayer = false,
                .blocksZombies = false,
            };
        };

    // Prototype room content now lives in the same authored map definition
    // consumed by gameplay and, progressively, the renderer. The dimensions
    // match the existing procedural room exactly.
    addVisualBox(
        1U,
        {0.0f, -1.58f, 0.0f},
        {3.15f, 0.09f, 3.75f},
        0U);

    addVisualBox(
        2U,
        {-3.15f, 0.05f, 0.0f},
        {0.09f, 1.65f, 3.75f},
        1U);

    addVisualBox(
        3U,
        {3.15f, 0.05f, 0.0f},
        {0.09f, 1.65f, 3.75f},
        1U);

    addVisualBox(
        4U,
        {0.0f, 0.05f, 3.85f},
        {3.15f, 1.65f, 0.09f},
        2U);

    addVisualBox(
        5U,
        {0.0f, 2.02f, 0.0f},
        {3.15f, 0.075f, 3.75f},
        2U);

    addVisualBox(
        6U,
        {-1.70f, -1.505f, -0.25f},
        {0.825f, 0.01875f, 1.0875f},
        13U);

    addVisualBox(
        7U,
        {3.00f, 0.15f, -0.65f},
        {0.01875f, 0.7875f, 0.825f},
        14U);

    map.boxes[map.boxCount++] = {
        .id = 8U,
        .center = {
            (kPrototypeCenterObstacle.minimum.x +
             kPrototypeCenterObstacle.maximum.x) * 0.5f,
            (kPrototypeCenterObstacle.minimum.y +
             kPrototypeCenterObstacle.maximum.y) * 0.5f,
            (kPrototypeCenterObstacle.minimum.z +
             kPrototypeCenterObstacle.maximum.z) * 0.5f,
        },
        .halfExtents = {
            (kPrototypeCenterObstacle.maximum.x -
             kPrototypeCenterObstacle.minimum.x) * 0.5f,
            (kPrototypeCenterObstacle.maximum.y -
             kPrototypeCenterObstacle.minimum.y) * 0.5f,
            (kPrototypeCenterObstacle.maximum.z -
             kPrototypeCenterObstacle.minimum.z) * 0.5f,
        },
        .materialId = 1U,
        .visible = false,
        .blocksPlayer = true,
        .blocksZombies = true,
    };

    map.doors[0] = {
        .door = {
            .id = kPrototypeDoorId,
            .blocker = kPrototypeDoorObstacle,
            .cost = kPrototypeDoorCost,
            .startsOpen = false,
        },
        .interaction = {
            .id = kPrototypeDoorId,
            .kind = xziel::InteractionKind::Door,
            .position = kPrototypeDoorInteractionPosition,
            .maximumDistance = 1.75f,
            .minimumFacingDot = 0.10f,
            .priority = 1.35f,
            .holdSeconds = 0.18f,
            .cost = kPrototypeDoorCost,
            .enabled = true,
        },
    };
    map.doorCount = 1;

    map.windows[0] = {
        .window = {
            .id = kPrototypeWindowId,
            .blocker = kPrototypeWindowObstacle,
            .barricade = {
                .maximumPlanks = 6,
                .zombieTearSeconds = 0.92f,
                .rebuildSeconds = 0.68f,
                .rebuildPointsPerPlank = 10U,
                .maximumRebuildPointsPerRound = 60U,
            },
        },
        .interaction = {
            .id = kPrototypeWindowId,
            .kind = xziel::InteractionKind::Use,
            .position = kPrototypeWindowInteractionPosition,
            .maximumDistance = 1.65f,
            .minimumFacingDot = 0.08f,
            .priority = 1.30f,
            .holdSeconds = 0.0f,
            .cost = 0U,
            .enabled = true,
        },
    };
    map.windowCount = 1;

    map.interactions[0] = {
        .id = kPrototypePowerSwitchId,
        .kind = xziel::InteractionKind::Switch,
        .position = kPrototypePowerSwitchPosition,
        .maximumDistance = 1.65f,
        .minimumFacingDot = 0.20f,
        .priority = 1.0f,
        .holdSeconds = 0.32f,
        .cost = 0,
        .enabled = true,
    };

    map.interactions[1] = {
        .id = kPrototypeWeaponBuyId,
        .kind = xziel::InteractionKind::WeaponBuy,
        .position = kPrototypeWeaponBuyPosition,
        .maximumDistance = 1.55f,
        .minimumFacingDot = 0.18f,
        .priority = 1.20f,
        .holdSeconds = 0.20f,
        .cost = kPrototypeWeaponBuyCost,
        .enabled = true,
    };
    map.interactionCount = 2;
}

void configurePrototypeQuest(
    NativeAppState& state) noexcept {
    xziel::QuestDefinition quest{};
    quest.id = 9001U;

    quest.steps[0] = {
        .id = 1U,
        .requiredEvent =
            xziel::GameplayEventType::PowerStateChanged,
        .subjectId = kPrototypePowerSwitchId,
        .requiredCount = 1U,
    };

    quest.steps[1] = {
        .id = 2U,
        .requiredEvent =
            xziel::GameplayEventType::DoorOpened,
        .subjectId = kPrototypeDoorId,
        .requiredCount = 1U,
    };

    quest.steps[2] = {
        .id = 3U,
        .requiredEvent =
            xziel::GameplayEventType::PurchaseCompleted,
        .subjectId = kPrototypeWeaponBuyId,
        .requiredCount = 1U,
    };

    quest.stepCount = 3U;
    (void) state.questRuntime.load(
        quest);
}

void logInfo(const char* message) noexcept {
    __android_log_print(
        ANDROID_LOG_INFO,
        kTag,
        "%s",
        message);
}

void logError(const char* message) noexcept {
    __android_log_print(
        ANDROID_LOG_ERROR,
        kTag,
        "%s",
        message);
}

void requestHaptic(
    NativeAppState& state,
    xziel::HapticEvent event) noexcept {
    const auto command =
        state.haptics.request(
            event,
            state.hapticsBridge.capabilities(),
            state.hapticElapsedSeconds);

    state.hapticElapsedSeconds = 0.0f;

    state.hapticsBridge.play(
        command);
}


xziel::ThermalLevel queryThermalLevel(
    NativeAppState& state) noexcept {
    if (state.jniEnv == nullptr ||
        state.javaActivity == nullptr) {
        return xziel::ThermalLevel::Nominal;
    }

    JNIEnv* env = state.jniEnv;

    jclass activityClass =
        env->GetObjectClass(
            state.javaActivity);

    if (activityClass == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }

        return xziel::ThermalLevel::Nominal;
    }

    jmethodID method =
        env->GetMethodID(
            activityClass,
            "getXzielThermalStatus",
            "()I");

    if (method == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }

        env->DeleteLocalRef(
            activityClass);

        return xziel::ThermalLevel::Nominal;
    }

    const jint status =
        env->CallIntMethod(
            state.javaActivity,
            method);

    if (env->ExceptionCheck()) {
        env->ExceptionClear();

        env->DeleteLocalRef(
            activityClass);

        return xziel::ThermalLevel::Nominal;
    }

    env->DeleteLocalRef(
        activityClass);

    if (status <= 0) {
        return xziel::ThermalLevel::Nominal;
    }

    if (status == 1) {
        return xziel::ThermalLevel::Light;
    }

    if (status == 2) {
        return xziel::ThermalLevel::Moderate;
    }

    if (status == 3) {
        return xziel::ThermalLevel::Severe;
    }

    return xziel::ThermalLevel::Critical;
}

bool queryPowerSaveMode(
    NativeAppState& state) noexcept {
    if (state.jniEnv == nullptr ||
        state.javaActivity == nullptr) {
        return false;
    }

    JNIEnv* env = state.jniEnv;
    jclass activityClass =
        env->GetObjectClass(
            state.javaActivity);

    if (activityClass == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }
        return false;
    }

    jmethodID method =
        env->GetMethodID(
            activityClass,
            "isXzielPowerSaveMode",
            "()Z");

    if (method == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }

        env->DeleteLocalRef(
            activityClass);
        return false;
    }

    const jboolean value =
        env->CallBooleanMethod(
            state.javaActivity,
            method);

    if (env->ExceptionCheck()) {
        env->ExceptionClear();
        env->DeleteLocalRef(
            activityClass);
        return false;
    }

    env->DeleteLocalRef(
        activityClass);

    return value == JNI_TRUE;
}

float queryRefreshRate(
    NativeAppState& state) noexcept {
    if (state.jniEnv == nullptr ||
        state.javaActivity == nullptr) {
        return 60.0f;
    }

    JNIEnv* env = state.jniEnv;
    jclass activityClass =
        env->GetObjectClass(
            state.javaActivity);

    if (activityClass == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }
        return 60.0f;
    }

    jmethodID method =
        env->GetMethodID(
            activityClass,
            "getXzielRefreshRate",
            "()F");

    if (method == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }

        env->DeleteLocalRef(
            activityClass);
        return 60.0f;
    }

    const jfloat value =
        env->CallFloatMethod(
            state.javaActivity,
            method);

    if (env->ExceptionCheck()) {
        env->ExceptionClear();
        env->DeleteLocalRef(
            activityClass);
        return 60.0f;
    }

    env->DeleteLocalRef(
        activityClass);

    return std::clamp(
        static_cast<float>(value),
        30.0f,
        240.0f);
}

int queryDisplayRotation(
    NativeAppState& state) noexcept {
    if (state.jniEnv == nullptr ||
        state.javaActivity == nullptr) {
        return 0;
    }

    JNIEnv* env =
        state.jniEnv;

    jclass activityClass =
        env->GetObjectClass(
            state.javaActivity);

    if (activityClass == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }
        return 0;
    }

    jmethodID method =
        env->GetMethodID(
            activityClass,
            "getXzielDisplayRotation",
            "()I");

    if (method == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }

        env->DeleteLocalRef(
            activityClass);

        return 0;
    }

    const jint value =
        env->CallIntMethod(
            state.javaActivity,
            method);

    if (env->ExceptionCheck()) {
        env->ExceptionClear();
        env->DeleteLocalRef(
            activityClass);
        return 0;
    }

    env->DeleteLocalRef(
        activityClass);

    return std::clamp(
        static_cast<int>(value),
        0,
        3);
}

void refreshDisplayRotation(
    NativeAppState& state) noexcept {
    state.input.setDisplayRotation(
        queryDisplayRotation(
            state));
}

void handleCommand(
    android_app* app,
    int32_t command) {
    auto* state =
        static_cast<NativeAppState*>(
            app->userData);

    if (state == nullptr) {
        return;
    }

    switch (command) {
        case APP_CMD_START:
            state->runtime.onEvent(
                xziel::AndroidLifecycleEvent::Start);
            break;

        case APP_CMD_RESUME:
            state->runtime.onEvent(
                xziel::AndroidLifecycleEvent::Resume);
            refreshDisplayRotation(
                *state);
            state->input.onResume();
            state->lastFrame =
                std::chrono::steady_clock::now();
            state->hasLastFrame = false;
            break;

        case APP_CMD_PAUSE:
            state->input.onPause();
            state->runtime.onEvent(
                xziel::AndroidLifecycleEvent::Pause);
            state->hasLastFrame = false;
            break;

        case APP_CMD_STOP:
            state->input.onPause();
            state->runtime.onEvent(
                xziel::AndroidLifecycleEvent::Stop);
            state->hasLastFrame = false;
            break;

        case APP_CMD_GAINED_FOCUS:
            state->runtime.onEvent(
                xziel::AndroidLifecycleEvent::FocusGained);
            refreshDisplayRotation(
                *state);
            break;

        case APP_CMD_LOST_FOCUS:
            state->runtime.onEvent(
                xziel::AndroidLifecycleEvent::FocusLost);
            break;

        case APP_CMD_LOW_MEMORY:
            state->runtime.onEvent(
                xziel::AndroidLifecycleEvent::LowMemory);

            state->memoryPressure =
                xziel::MemoryPressure::Critical;

            state->memoryPressureSeconds =
                15.0f;

            logInfo("LOW_MEMORY");
            break;

        case APP_CMD_INIT_WINDOW:
            if (app->window != nullptr) {
                state->runtime.onEvent(
                    xziel::AndroidLifecycleEvent::SurfaceCreated);

                refreshDisplayRotation(
                    *state);

                state->renderer.shutdown();

                if (state->renderer.initialize(
                        app->window,
                        app->activity->assetManager,
                        state->jniEnv,
                        state->javaActivity)) {
                    state->hasWindow = true;
                    state->watchdog.reset();
                    state->lastFrame =
                        std::chrono::steady_clock::now();
                    state->hasLastFrame = false;
                    logInfo("XZIEL_VULKAN_READY");
                } else {
                    state->hasWindow = false;

                    const auto recovery =
                        state->watchdog.report(
                            {
                                .fault =
                                    xziel::RendererFault::DeviceInitFailed,
                                .frameIndex = 0,
                                .code = 0,
                            },
                            xziel::RendererBackend::Vulkan,
                            false);

                    if (recovery.recommendedAction ==
                        xziel::RendererRecoveryAction::ExitCleanly) {
                        logError(
                            "Vulkan init failed; clean exit requested");
                    }
                }
            }
            break;

        case APP_CMD_TERM_WINDOW:
            state->hasWindow = false;
            state->renderer.shutdown();
            state->runtime.onEvent(
                xziel::AndroidLifecycleEvent::SurfaceDestroyed);
            state->hasLastFrame = false;
            logInfo("SURFACE_DESTROYED");
            break;

        case APP_CMD_DESTROY:
            state->input.onPause();
            state->runtime.onEvent(
                xziel::AndroidLifecycleEvent::Destroy);
            break;

        default:
            break;
    }
}

float computeFrameDelta(
    NativeAppState& state,
    std::chrono::steady_clock::time_point now) noexcept {
    if (!state.hasLastFrame) {
        state.lastFrame = now;
        state.hasLastFrame = true;
        return 1.0f / 60.0f;
    }

    const float raw =
        std::chrono::duration<float>(
            now - state.lastFrame).count();

    state.lastFrame = now;

    if (!std::isfinite(raw) ||
        raw <= 0.0f) {
        return 1.0f / 60.0f;
    }

    return std::clamp(
        raw,
        1.0f / 1000.0f,
        0.100f);
}

void advancePlayer(
    NativeAppState& state,
    const xziel::android::AndroidInputSnapshot& input,
    const xziel::FrameStats& stats) noexcept {
    state.player.sampleViewInput(
        input.input,
        static_cast<float>(
            stats.clampedFrameDeltaSeconds));

    if (stats.ticksThisFrame == 0) {
        return;
    }

    const float fixedDelta =
        static_cast<float>(
            1.0 /
            state.engine.config().
                fixedTickHz);

    for (std::uint32_t tick = 0;
         tick < stats.ticksThisFrame;
         ++tick) {
        const auto vitalsFrame =
            state.vitals.step(
                fixedDelta);

        if (vitalsFrame.respawnedThisTick) {
            state.player.reset();
            state.weapon.reset();
            state.horde.reset();
            state.interaction.reset();
            state.pendingRecoilPitch = 0.0f;
            state.pendingRecoilYaw = 0.0f;
        }

        xziel::MobileMovementButtons buttons =
            input.movementButtons;

        if (tick > 0) {
            buttons.jumpPressed = false;
            buttons.stancePressed = false;
            buttons.movementCancelGesture = false;
        }

        const auto playerFrame =
            state.vitals.frame().alive
            ? state.player.fixedStep(
                  input.input.move,
                  buttons,
                  fixedDelta)
            : state.player.frame();

        const float interactionYaw =
            playerFrame.yawDegrees *
            kDegreesToRadians;

        const xziel::Vec3 interactionView{
            std::sin(
                interactionYaw),
            0.0f,
            std::cos(
                interactionYaw),
        };

        state.interactionFrame =
            state.interaction.step(
                playerFrame.cameraPosition,
                interactionView,
                {
                    .held =
                        state.vitals.frame().alive &&
                        input.input.interact,
                },
                fixedDelta);

        if (state.interactionFrame.
                activatedThisTick) {
            if (state.interactionFrame.targetId ==
                kPrototypePowerSwitchId) {
                state.stormEnabled =
                    !state.stormEnabled;

                state.environment.setWeather(
                    state.stormEnabled
                        ? state.stormWeather
                        : state.calmWeather);

                (void) state.gameplayEvents.push(
                    {
                        .type =
                            xziel::GameplayEventType::
                                PowerStateChanged,
                        .subjectId =
                            kPrototypePowerSwitchId,
                        .amount = 1U,
                        .value =
                            state.stormEnabled
                            ? 1.0f
                            : 0.0f,
                        .simulationTick =
                            state.engine.simulationTick(),
                    });

                state.audio.play(
                    xziel::android::AndroidAudioCue::UiConfirm,
                    0.72f);

                requestHaptic(
                    state,
                    xziel::HapticEvent::UiConfirm);
            } else if (
                state.interactionFrame.targetId ==
                    kPrototypeDoorId) {
                const auto doorFrame =
                    state.mapRuntime.activateDoor(
                        kPrototypeDoorId,
                        state.player,
                        state.horde,
                        state.interaction,
                        state.score);

                if (doorFrame.openedThisTick) {
                    (void) state.interaction.
                        setTargetEnabled(
                            kPrototypeDoorId,
                            false);

                    state.scorePulseSeconds =
                        0.38f;

                    (void) state.gameplayEvents.push(
                        {
                            .type =
                                xziel::GameplayEventType::
                                    DoorOpened,
                            .subjectId =
                                kPrototypeDoorId,
                            .amount = 1U,
                            .simulationTick =
                                state.engine.simulationTick(),
                        });

                    state.audio.play(
                        xziel::android::AndroidAudioCue::Door,
                        0.92f);

                    requestHaptic(
                        state,
                        xziel::HapticEvent::UiConfirm);
                } else if (
                    doorFrame.insufficientFundsThisTick) {
                    state.purchaseDeniedSeconds =
                        0.42f;

                    state.audio.play(
                        xziel::android::AndroidAudioCue::UiError,
                        0.78f);

                    requestHaptic(
                        state,
                        xziel::HapticEvent::UiError);
                }
            } else if (
                state.interactionFrame.targetId ==
                    kPrototypeWeaponBuyId &&
                !state.prototypeWeaponBuyPurchased) {
                if (state.score.trySpend(
                        kPrototypeWeaponBuyCost)) {
                    state.weaponProfile =
                        xziel::makeWeaponProfile(
                            xziel::WeaponArchetype::
                                AssaultRifle);

                    state.weapon.equip(
                        state.weaponProfile.
                            controller);

                    state.prototypeWeaponBuyPurchased =
                        true;

                    (void) state.interaction.
                        setTargetEnabled(
                            kPrototypeWeaponBuyId,
                            false);

                    state.scorePulseSeconds =
                        0.38f;

                    (void) state.gameplayEvents.push(
                        {
                            .type =
                                xziel::GameplayEventType::
                                    PurchaseCompleted,
                            .subjectId =
                                kPrototypeWeaponBuyId,
                            .amount = 1U,
                            .simulationTick =
                                state.engine.simulationTick(),
                        });

                    state.audio.play(
                        xziel::android::AndroidAudioCue::UiConfirm,
                        0.80f);

                    requestHaptic(
                        state,
                        xziel::HapticEvent::UiConfirm);
                } else {
                    state.purchaseDeniedSeconds =
                        0.42f;

                    state.audio.play(
                        xziel::android::AndroidAudioCue::UiError,
                        0.78f);

                    requestHaptic(
                        state,
                        xziel::HapticEvent::UiError);
                }
            }
        }

        const auto hordeFrame =
            state.horde.step(
                playerFrame.feetPosition,
                fixedDelta);

        const bool rebuildingPrototypeWindow =
            state.vitals.frame().alive &&
            state.interactionFrame.promptVisible &&
            state.interactionFrame.targetId ==
                kPrototypeWindowId &&
            input.input.interact;

        const auto prototypeWindowFrame =
            state.mapRuntime.stepWindow(
                kPrototypeWindowId,
                rebuildingPrototypeWindow,
                fixedDelta,
                state.player,
                state.horde,
                state.score);

        if (prototypeWindowFrame.
                barricade.pointsAwardedThisTick > 0U) {
            state.scorePulseSeconds = 0.24f;

            state.audio.play(
                xziel::android::AndroidAudioCue::
                    BarricadeRebuild,
                0.70f);

            (void) state.gameplayEvents.push(
                {
                    .type =
                        xziel::GameplayEventType::
                            PlankRebuilt,
                    .subjectId =
                        kPrototypeWindowId,
                    .amount = 1U,
                    .value =
                        static_cast<float>(
                            prototypeWindowFrame.
                                barricade.intactPlanks),
                    .simulationTick =
                        state.engine.simulationTick(),
                });
        }

        if (prototypeWindowFrame.
                barricade.plankRemovedThisTick) {
            state.audio.play(
                xziel::android::AndroidAudioCue::
                    BarricadeBreak,
                0.76f);
        }

        if (prototypeWindowFrame.
                barricade.breachedThisTick) {
            (void) state.gameplayEvents.push(
                {
                    .type =
                        xziel::GameplayEventType::
                            WindowBreached,
                    .subjectId =
                        kPrototypeWindowId,
                    .amount = 1U,
                    .simulationTick =
                        state.engine.simulationTick(),
                });
        }

        if (prototypeWindowFrame.
                barricade.fullyRebuiltThisTick) {
            (void) state.gameplayEvents.push(
                {
                    .type =
                        xziel::GameplayEventType::
                            WindowFullyRebuilt,
                    .subjectId =
                        kPrototypeWindowId,
                    .amount = 1U,
                    .simulationTick =
                        state.engine.simulationTick(),
                });
        }

        if (hordeFrame.roundStartedThisTick) {
            state.mapRuntime.beginRound();

            state.audio.play(
                xziel::android::AndroidAudioCue::RoundStart,
                0.78f);

            (void) state.gameplayEvents.push(
                {
                    .type =
                        xziel::GameplayEventType::
                            RoundStarted,
                    .subjectId =
                        hordeFrame.round,
                    .amount = 1U,
                    .simulationTick =
                        state.engine.simulationTick(),
                });
        }

        if (hordeFrame.roundStartedThisTick &&
            hordeFrame.round > 1U) {
            (void) state.gameplayEvents.push(
                {
                    .type =
                        xziel::GameplayEventType::
                            RoundCompleted,
                    .subjectId =
                        hordeFrame.round - 1U,
                    .amount = 1U,
                    .simulationTick =
                        state.engine.simulationTick(),
                });
            (void) state.score.awardRoundClear(
                hordeFrame.round - 1U);

            state.scorePulseSeconds =
                0.38f;
        }

        bool damagedByZombie = false;

        for (std::size_t slot = 0;
             slot < state.horde.capacity();
             ++slot) {
            const auto* zombie =
                state.horde.zombie(
                    slot);

            if (zombie == nullptr ||
                !zombie->frame().
                    attackThisTick ||
                state.horde.zombieDynamicBlockerTarget(slot) != 0U ||
                !state.vitals.frame().
                    alive) {
                continue;
            }

            if (state.vitals.applyDamage(
                    zombie->config().
                        attackDamage)) {
                damagedByZombie = true;

                (void) state.gameplayEvents.push(
                    {
                        .type =
                            state.vitals.frame().alive
                            ? xziel::GameplayEventType::
                                  PlayerDamaged
                            : xziel::GameplayEventType::
                                  PlayerDowned,
                        .subjectId = 1U,
                        .actorId =
                            static_cast<std::uint32_t>(
                                slot + 1U),
                        .value =
                            zombie->config().
                                attackDamage,
                        .simulationTick =
                            state.engine.simulationTick(),
                    });
            }
        }

        if (damagedByZombie) {
            state.zombieAttackFlashSeconds =
                0.22f;

            state.audio.play(
                xziel::android::AndroidAudioCue::PlayerHit,
                0.90f);

            requestHaptic(
                state,
                xziel::HapticEvent::PlayerHit);
        }

        const auto weaponFrame =
            state.weapon.step(
                {
                    .fireHeld =
                        state.vitals.frame().alive &&
                        input.input.fire &&
                        playerFrame.movement.canFire,
                    .firePressed =
                        tick == 0U &&
                        state.vitals.frame().alive &&
                        input.firePressed &&
                        playerFrame.movement.canFire,
                    .reloadPressed =
                        state.vitals.frame().alive &&
                        input.input.reload &&
                        playerFrame.movement.canReload,
                    .aimHeld =
                        state.vitals.frame().alive &&
                        input.input.aim &&
                        playerFrame.movement.canAim,
                },
                fixedDelta);

        if (weaponFrame.reloadCompletedThisTick) {
            state.audio.play(
                xziel::android::AndroidAudioCue::Reload,
                0.68f);

            requestHaptic(
                state,
                xziel::HapticEvent::ReloadComplete);
        }

        if (playerFrame.movement.cue ==
            xziel::MovementCue::MantleStart) {
            requestHaptic(
                state,
                xziel::HapticEvent::MantleContact);
        }

        if (playerFrame.movement.cue ==
            xziel::MovementCue::SlideStart) {
            requestHaptic(
                state,
                xziel::HapticEvent::SlideImpact);
        }

        if (weaponFrame.firedThisTick) {
            state.muzzleFlashSeconds =
                0.055f;

            state.audio.play(
                xziel::android::AndroidAudioCue::Fire,
                0.92f);

            requestHaptic(
                state,
                xziel::HapticEvent::FireLight);

            state.pendingRecoilPitch +=
                weaponFrame.recoilPitchImpulse;
            state.pendingRecoilYaw +=
                weaponFrame.recoilYawImpulse;

            const auto ray =
                xziel::makeViewRay(
                    playerFrame.cameraPosition,
                    playerFrame.yawDegrees,
                    playerFrame.pitchDegrees);

            std::size_t nearestSlot =
                state.horde.capacity();

            const float maximumWeaponRange =
                std::max(
                    state.weaponProfile.
                        maximumRangeMeters,
                    0.1f);

            xziel::ZombieHitResult nearestHit{};
            nearestHit.distance =
                maximumWeaponRange;

            for (std::size_t slot = 0;
                 slot < state.horde.capacity();
                 ++slot) {
                const auto* zombie =
                    state.horde.zombie(
                        slot);

                if (zombie == nullptr ||
                    zombie->frame().state ==
                        xziel::ZombieState::Dead) {
                    continue;
                }

                const auto hit =
                    xziel::raycastZombie(
                        ray,
                        *zombie,
                        nearestHit.hit
                            ? nearestHit.distance
                            : maximumWeaponRange);

                if (!hit.hit ||
                    (nearestHit.hit &&
                     hit.distance >
                         nearestHit.distance)) {
                    continue;
                }

                nearestHit = hit;
                nearestSlot = slot;
            }

            if (nearestSlot <
                    state.horde.capacity() &&
                nearestHit.hit) {
                const float damage =
                    xziel::weaponDamageAtDistance(
                        state.weaponProfile,
                        nearestHit.distance) *
                    nearestHit.damageMultiplier;

                if (state.horde.damageZombie(
                        nearestSlot,
                        damage)) {
                    state.audio.play(
                        nearestHit.region ==
                                xziel::ZombieHitRegion::Head
                            ? xziel::android::AndroidAudioCue::
                                  CriticalHit
                            : xziel::android::AndroidAudioCue::
                                  Hit,
                        0.74f);

                    const auto* damagedZombie =
                        state.horde.zombie(
                            nearestSlot);

                    const bool killed =
                        damagedZombie != nullptr &&
                        damagedZombie->frame().state ==
                            xziel::ZombieState::Dead;

                    (void) state.score.awardHit(
                        nearestHit.region,
                        killed);

                    if (killed) {
                        (void) state.gameplayEvents.push(
                            {
                                .type =
                                    nearestHit.region ==
                                        xziel::ZombieHitRegion::Head
                                    ? xziel::GameplayEventType::
                                          ZombieHeadshot
                                    : xziel::GameplayEventType::
                                          ZombieKilled,
                                .subjectId =
                                    static_cast<std::uint32_t>(
                                        nearestSlot + 1U),
                                .actorId = 1U,
                                .amount = 1U,
                                .simulationTick =
                                    state.engine.simulationTick(),
                            });
                    }

                    if (killed &&
                        nearestHit.region ==
                            xziel::ZombieHitRegion::Head) {
                        state.decapFxSeconds =
                            0.80f;

                        state.decapOrigin =
                            nearestHit.point;

                        state.decapDirection =
                            ray.direction;
                    }

                    state.scorePulseSeconds =
                        0.24f;

                    state.hitMarkerSeconds =
                        0.12f;

                    state.criticalHitSeconds =
                        nearestHit.region ==
                            xziel::ZombieHitRegion::Head
                        ? 0.18f
                        : 0.0f;

                    state.impactFxSeconds =
                        0.10f;

                    state.impactPoint =
                        nearestHit.point;
                }
            }
        }

        xziel::GameplayEvent gameplayEvent{};
        while (state.gameplayEvents.pop(
                   gameplayEvent)) {
            const auto questFrame =
                state.questRuntime.consume(
                    gameplayEvent);

            if (questFrame.stepCompletedThisTick ||
                questFrame.questCompletedThisTick) {
                state.scorePulseSeconds =
                    std::max(
                        state.scorePulseSeconds,
                        0.32f);

                requestHaptic(
                    state,
                    xziel::HapticEvent::UiConfirm);
            }
        }
    }
}

xziel::CameraRigFrame advanceCameraRig(
    NativeAppState& state,
    const xziel::android::AndroidInputSnapshot& input,
    float frameDeltaSeconds) noexcept {
    const auto& player =
        state.player.frame();

    const float horizontalSpeed =
        std::sqrt(
            player.movement.velocity.x *
                player.movement.velocity.x +
            player.movement.velocity.z *
                player.movement.velocity.z);

    const float speedNormalized =
        std::clamp(
            horizontalSpeed / 7.2f,
            0.0f,
            1.0f);

    state.stridePhase =
        std::fmod(
            state.stridePhase +
                speedNormalized *
                std::max(
                    frameDeltaSeconds,
                    0.0f) *
                1.85f,
            1.0f);

    float nearestZombieDistance =
        999.0f;

    std::uint32_t aliveZombies = 0;

    for (std::size_t slot = 0;
         slot < state.horde.capacity();
         ++slot) {
        const auto* zombie =
            state.horde.zombie(
                slot);

        if (zombie == nullptr ||
            zombie->frame().state ==
                xziel::ZombieState::Dead) {
            continue;
        }

        ++aliveZombies;

        const float dx =
            zombie->frame().position.x -
            player.feetPosition.x;

        const float dz =
            zombie->frame().position.z -
            player.feetPosition.z;

        nearestZombieDistance =
            std::min(
                nearestZombieDistance,
                std::sqrt(
                    dx * dx +
                    dz * dz));
    }

    const float threat =
        aliveZombies == 0
        ? 0.0f
        : 1.0f -
            std::clamp(
                nearestZombieDistance / 8.0f,
                0.0f,
                1.0f);

    const float magazineRatio =
        static_cast<float>(
            state.weapon.frame().magazine) /
        static_cast<float>(
            std::max<std::uint32_t>(
                state.weapon.config().
                    magazineSize,
                1U));

    state.horrorFrame =
        state.horror.advance(
            {
                .threatProximity =
                    threat,
                .hordePressure =
                    std::clamp(
                        static_cast<float>(
                            aliveZombies) /
                        static_cast<float>(
                            std::max<std::uint32_t>(
                                state.horde.config().
                                    maxActive,
                                1U)),
                        0.0f,
                        1.0f),
                .recentDamage =
                    state.vitals.frame().
                        damageFlash,
                .darkness = 0.82f,
                .isolation = 0.76f,
                .lowAmmoPressure =
                    1.0f -
                    magazineRatio,
                .lowHealthPressure =
                    1.0f -
                    state.vitals.frame().
                        healthRatio,
                .beingChased =
                    aliveZombies > 0,
                .safeRoom = false,
                .scriptedScareWindow =
                    false,
            },
            frameDeltaSeconds);

    const float recoilPitch =
        state.pendingRecoilPitch;

    const float recoilYaw =
        state.pendingRecoilYaw;

    state.pendingRecoilPitch = 0.0f;
    state.pendingRecoilYaw = 0.0f;

    return state.cameraRig.advance(
        {
            .moveSpeedNormalized =
                speedNormalized,
            .stridePhase =
                state.stridePhase,
            .aiming =
                state.weapon.frame().adsAlpha >
                0.5f,
            .reducedMotion =
                false,
            .weaponRecoilPitchImpulse =
                recoilPitch,
            .weaponRecoilYawImpulse =
                recoilYaw,
            .landingImpact =
                player.movement.cue ==
                    xziel::MovementCue::Land
                ? 1.0f
                : 0.0f,
        },
        player.movement,
        state.horrorFrame,
        frameDeltaSeconds);
}

xziel::android::VulkanHudState makeHudState(
    const NativeAppState& state,
    const xziel::android::AndroidInputSnapshot& input) noexcept {
    xziel::android::VulkanHudState hud{};

    hud.moveX =
        input.input.move.x;
    hud.moveY =
        input.input.move.y;

    hud.moveAnchorX =
        input.moveAnchorNormalized.x;
    hud.moveAnchorY =
        input.moveAnchorNormalized.y;

    hud.moveActive =
        input.moveActive;
    hud.fire =
        input.input.fire;
    hud.aim =
        input.input.aim;
    hud.reload =
        input.input.reload;
    hud.jump =
        input.movementButtons.jumpHeld ||
        input.movementButtons.jumpPressed;
    hud.stance =
        input.movementButtons.stanceHeld ||
        input.movementButtons.stancePressed;
    hud.gyroAvailable =
        input.gyroAvailable;

    hud.interactAvailable =
        state.interactionFrame.
            promptVisible;

    hud.interactHeld =
        input.input.interact;

    hud.interactProgress =
        state.interactionFrame.
            holdAlpha;

    hud.interactionCost =
        state.interactionFrame.
            cost;

    hud.interactionAffordable =
        state.interactionFrame.cost == 0U ||
        state.score.frame().total >=
            static_cast<std::uint64_t>(
                state.interactionFrame.cost);

    hud.interactionDeniedAlpha =
        std::clamp(
            state.purchaseDeniedSeconds /
                0.42f,
            0.0f,
            1.0f);

    hud.hitMarkerAlpha =
        std::clamp(
            state.hitMarkerSeconds /
                0.12f,
            0.0f,
            1.0f);

    hud.criticalHitAlpha =
        std::clamp(
            state.criticalHitSeconds /
                0.18f,
            0.0f,
            1.0f);

    hud.targetAlive =
        state.horde.frame().alive > 0;

    hud.weaponAdsAlpha =
        state.weapon.frame().adsAlpha;

    hud.weaponReloadAlpha =
        state.weapon.frame().reloadAlpha;

    hud.weaponFireAlpha =
        std::clamp(
            state.muzzleFlashSeconds /
                0.055f,
            0.0f,
            1.0f);

    hud.weaponMagazineRatio =
        static_cast<float>(
            state.weapon.frame().magazine) /
        static_cast<float>(
            std::max<std::uint32_t>(
                state.weapon.config().magazineSize,
                1U));

    hud.viewmodelLowering =
        state.player.frame().
            movement.viewmodelLowering;

    hud.playerHealthRatio =
        state.vitals.frame().
            healthRatio;

    hud.damageFlashAlpha =
        std::max(
            state.vitals.frame().
                damageFlash,
            std::clamp(
                state.zombieAttackFlashSeconds /
                    0.22f,
                0.0f,
                1.0f));

    hud.deathAlpha =
        state.vitals.frame().
            deathAlpha;

    hud.horrorVignette =
        state.horrorFrame.
            vignetteStrength;

    hud.scoreTotal =
        state.score.frame().
            total;

    hud.scorePulseAlpha =
        std::clamp(
            state.scorePulseSeconds /
                0.38f,
            0.0f,
            1.0f);

    return hud;
}

xziel::android::VulkanEnvironmentState makeEnvironmentState(
    NativeAppState& state) noexcept {
    xziel::android::VulkanEnvironmentState environment{};

    environment.rainIntensity =
        state.environmentFrame.
            rainIntensity;

    environment.fogDensity =
        state.environmentFrame.
            fogDensity +
        state.horrorFrame.
            fogDensityBoost;

    environment.lightningFlash =
        state.environmentFrame.
            lightningFlash;

    environment.wetness =
        state.environmentFrame.
            wetness;

    environment.windX =
        state.environmentFrame.
            windMetersPerSecond.x;

    environment.windZ =
        state.environmentFrame.
            windMetersPerSecond.z;

    environment.particleDensityScale =
        state.renderWorkload.
            particleDensityScale;

    environment.fogQualityScale =
        state.renderWorkload.
            fogQualityScale;

    environment.postProcessScale =
        state.renderWorkload.
            postProcessScale;

    environment.maxPlanarReflectionPasses =
        state.renderWorkload.
            maxPlanarReflectionPasses;

    environment.planarReflectionScale =
        state.renderWorkload.
            planarReflectionScale;

    environment.reflectionDistanceMeters =
        state.renderWorkload.
            reflectionDistanceMeters;

    environment.ssrEnabled =
        state.renderWorkload.
            ssrEnabled;

    environment.ssrResolutionScale =
        state.renderWorkload.
            ssrResolutionScale;

    environment.ssrMaxSteps =
        state.renderWorkload.
            ssrMaxSteps;

    // Feed authored candidate surfaces through the engine ReflectionPlanner
    // instead of hardcoding Vulkan to the prototype water plane. This is the
    // Android bridge that lets mirrors/water compete for the bounded planar
    // budget using the same policy as production map content.
    constexpr float kWaterFocusX = 0.0f;
    constexpr float kWaterFocusZ = 1.0f;
    constexpr float kMirrorFocusX = 3.2f;
    constexpr float kMirrorFocusZ = 2.2f;

    const auto& playerFrame = state.player.frame();
    const float cameraX = playerFrame.cameraPosition.x;
    const float cameraZ = playerFrame.cameraPosition.z;
    const float forwardX = std::sin(playerFrame.yawDegrees * kDegreesToRadians);
    const float forwardZ = std::cos(playerFrame.yawDegrees * kDegreesToRadians);

    auto makeCandidate = [&](std::uint32_t id,
                             xziel::ReflectionSurfaceKind kind,
                             float focusX,
                             float focusZ,
                             float coverageBase,
                             float importance,
                             float roughness,
                             float nx,
                             float ny,
                             float nz,
                             float d) noexcept {
        xziel::ReflectionSurface surface{};
        surface.id = id;
        surface.kind = kind;
        const float dx = focusX - cameraX;
        const float dz = focusZ - cameraZ;
        surface.distanceMeters = std::sqrt(dx * dx + dz * dz);
        const float safeDistance = std::max(surface.distanceMeters, 0.001f);
        const float facing = std::clamp(
            forwardX * (dx / safeDistance) +
            forwardZ * (dz / safeDistance), -1.0f, 1.0f);
        const float facingWeight = std::clamp((facing + 0.18f) / 0.58f, 0.0f, 1.0f);
        surface.visible =
            surface.distanceMeters <= state.renderWorkload.reflectionDistanceMeters &&
            facingWeight > 0.01f;
        surface.screenCoverage = surface.visible
            ? std::clamp(coverageBase / (1.0f + surface.distanceMeters * 0.08f) * facingWeight,
                         0.0f, coverageBase)
            : 0.0f;
        surface.importance = importance;
        surface.roughness = roughness;
        surface.planarEligible = true;
        surface.hasStaticProbe = true;
        surface.animated = kind == xziel::ReflectionSurfaceKind::Water;
        surface.planeNormalX = nx;
        surface.planeNormalY = ny;
        surface.planeNormalZ = nz;
        surface.planeDistance = d;
        return surface;
    };

    std::array<xziel::ReflectionSurface, 2> reflectionCandidates{
        makeCandidate(1U, xziel::ReflectionSurfaceKind::Water,
                      kWaterFocusX, kWaterFocusZ, 0.30f, 1.0f, state.waterFrame.roughness,
                      0.0f, 1.0f, 0.0f, 1.48f),
        makeCandidate(2U, xziel::ReflectionSurfaceKind::Mirror,
                      kMirrorFocusX, kMirrorFocusZ, 0.22f, 1.15f, 0.04f,
                      -1.0f, 0.0f, 0.0f, 3.2f)
    };
    std::array<xziel::ReflectionDecision, 2> reflectionDecisions{};
    const std::size_t decisionCount =
        state.reflectionPlanner.plan(
            reflectionCandidates.data(),
            reflectionCandidates.size(),
            state.renderWorkload,
            state.reflectionPlannerFrame++,
            reflectionDecisions.data(),
            reflectionDecisions.size());

    const xziel::ReflectionDecision* selected = nullptr;
    const xziel::ReflectionSurface* selectedSurface = nullptr;
    for (std::size_t index = 0; index < decisionCount; ++index) {
        if (!reflectionDecisions[index].needsExtraScenePass) continue;
        selected = &reflectionDecisions[index];
        for (const auto& candidate : reflectionCandidates) {
            if (candidate.id == selected->surfaceId) {
                selectedSurface = &candidate;
                break;
            }
        }
        if (selectedSurface != nullptr) break;
    }

    if (selected != nullptr && selectedSurface != nullptr) {
        environment.planarReflectionScale = selected->resolutionScale;
        environment.planarReflectionUpdateEveryNFrames =
            std::max(selected->updateEveryNFrames, 1U);
        environment.planarPlaneNormalX = selected->planeNormalX;
        environment.planarPlaneNormalY = selected->planeNormalY;
        environment.planarPlaneNormalZ = selected->planeNormalZ;
        environment.planarPlaneDistance = selected->planeDistance;
        environment.planarReflectionVisible = selectedSurface->visible;
        environment.planarReflectionScreenCoverage = selectedSurface->screenCoverage;
        switch (selectedSurface->kind) {
            case xziel::ReflectionSurfaceKind::Water:
                environment.planarReflectionMaterialId = 13U;
                break;
            case xziel::ReflectionSurfaceKind::Mirror:
                environment.planarReflectionMaterialId = 14U;
                break;
            default:
                environment.planarReflectionMaterialId = 0U;
                break;
        }
    } else {
        environment.planarReflectionUpdateEveryNFrames = 1U;
        environment.planarReflectionVisible = false;
        environment.planarReflectionScreenCoverage = 0.0f;
        environment.planarReflectionMaterialId = 0U;
    }

    environment.waterWavePhase =
        state.waterFrame.
            wavePhase;

    environment.waterFoamStrength =
        state.waterFrame.
            foamStrength;

    environment.waterReflectionStrength =
        state.waterFrame.
            reflectionStrength;

    environment.waterRefractionStrength =
        state.waterFrame.
            refractionStrength;

    environment.waterRoughness =
        state.waterFrame.
            roughness;

    return environment;
}

xziel::android::VulkanSceneState makeSceneState(
    const NativeAppState& state) noexcept {
    xziel::android::VulkanSceneState scene{};

    for (std::size_t index = 0;
         index < state.mapDefinition.boxCount &&
         scene.mapBoxCount < scene.mapBoxes.size();
         ++index) {
        const auto& authored =
            state.mapDefinition.boxes[index];

        if (!authored.visible) {
            continue;
        }

        auto& box =
            scene.mapBoxes[scene.mapBoxCount++];

        box.x = authored.center.x;
        box.y = authored.center.y;
        box.z = authored.center.z;

        // The renderer's procedural cube spans +/-0.75 in local space.
        // Convert authored half-extents into its scale convention here so map
        // data remains renderer-agnostic.
        box.scaleX =
            std::max(
                std::fabs(authored.halfExtents.x) / 0.75f,
                0.001f);
        box.scaleY =
            std::max(
                std::fabs(authored.halfExtents.y) / 0.75f,
                0.001f);
        box.scaleZ =
            std::max(
                std::fabs(authored.halfExtents.z) / 0.75f,
                0.001f);

        box.materialId =
            static_cast<float>(
                authored.materialId);
        box.visible = true;
    }

    for (std::size_t index = 0;
         index < state.mapDefinition.windowCount &&
         scene.windowCount < scene.windows.size();
         ++index) {
        const auto& authored =
            state.mapDefinition.windows[index].window;

        const auto* runtimeWindow =
            state.mapRuntime.windows().frame(
                authored.id);

        if (runtimeWindow == nullptr) {
            continue;
        }

        auto& window =
            scene.windows[scene.windowCount++];

        window.x =
            (authored.blocker.minimum.x +
             authored.blocker.maximum.x) * 0.5f;
        window.y =
            (authored.blocker.minimum.y +
             authored.blocker.maximum.y) * 0.5f;
        window.z =
            (authored.blocker.minimum.z +
             authored.blocker.maximum.z) * 0.5f;

        window.halfWidth =
            std::max(
                (authored.blocker.maximum.x -
                 authored.blocker.minimum.x) * 0.5f,
                0.01f);
        window.halfHeight =
            std::max(
                (authored.blocker.maximum.y -
                 authored.blocker.minimum.y) * 0.5f,
                0.01f);
        window.halfDepth =
            std::max(
                (authored.blocker.maximum.z -
                 authored.blocker.minimum.z) * 0.5f,
                0.01f);

        window.intactPlanks =
            runtimeWindow->barricade.intactPlanks;
        window.maximumPlanks =
            authored.barricade.maximumPlanks;
        window.visible = true;
    }

    for (std::size_t slot = 0;
         slot < state.horde.capacity() &&
         scene.zombieCount <
             scene.zombies.size();
         ++slot) {
        const auto* actor =
            state.horde.zombie(
                slot);

        if (actor == nullptr ||
            actor->frame().state ==
                xziel::ZombieState::Dead) {
            continue;
        }

        auto& zombie =
            scene.zombies[
                scene.zombieCount++];

        const auto& frame =
            actor->frame();

        zombie.x =
            frame.position.x;
        zombie.y =
            frame.position.y;
        zombie.z =
            frame.position.z;

        zombie.yawRadians =
            frame.yawDegrees *
            kDegreesToRadians;

        zombie.stridePhase =
            frame.stridePhase;

        zombie.healthRatio =
            frame.healthRatio;

        zombie.visible = true;
        zombie.staggered =
            frame.state ==
            xziel::ZombieState::Staggered;

        zombie.attack =
            frame.attackThisTick;
    }

    scene.roundProgress =
        state.horde.frame().
            targetThisRound > 0
        ? static_cast<float>(
              state.horde.frame().
                  killedThisRound) /
          static_cast<float>(
              state.horde.frame().
                  targetThisRound)
        : 0.0f;

    scene.interRound =
        state.horde.frame().
            interRound;

    scene.interactionX =
        state.interactionFrame.
            targetPosition.x;
    scene.interactionY =
        state.interactionFrame.
            targetPosition.y;
    scene.interactionZ =
        state.interactionFrame.
            targetPosition.z;

    scene.interactionVisible =
        state.interactionFrame.
            promptVisible;

    scene.interactionActive =
        state.interactionFrame.
            activatedThisTick ||
        (state.interactionFrame.targetId ==
             kPrototypePowerSwitchId &&
         state.stormEnabled);

    scene.doorOpenAlpha =
        state.prototypeDoorOpenAlpha;

    scene.impactX =
        state.impactPoint.x;
    scene.impactY =
        state.impactPoint.y;
    scene.impactZ =
        state.impactPoint.z;

    scene.impactAlpha =
        std::clamp(
            state.impactFxSeconds /
                0.10f,
            0.0f,
            1.0f);

    scene.impactCritical =
        state.criticalHitSeconds >
        0.0f;

    scene.decapOriginX =
        state.decapOrigin.x;
    scene.decapOriginY =
        state.decapOrigin.y;
    scene.decapOriginZ =
        state.decapOrigin.z;

    scene.decapDirectionX =
        state.decapDirection.x;
    scene.decapDirectionY =
        state.decapDirection.y;
    scene.decapDirectionZ =
        state.decapDirection.z;

    scene.decapAlpha =
        std::clamp(
            state.decapFxSeconds /
                0.80f,
            0.0f,
            1.0f);

    return scene;
}

xziel::android::VulkanCamera makeRenderCamera(
    const xziel::FpsPlayerFrame& player,
    const xziel::CameraRigFrame& rig) noexcept {
    xziel::android::VulkanCamera camera{};

    const float yawRadians =
        player.yawDegrees *
        kDegreesToRadians;

    const float rightX =
        std::cos(yawRadians);

    const float rightZ =
        -std::sin(yawRadians);

    camera.x =
        player.cameraPosition.x +
        rightX * rig.positionBobX;

    camera.y =
        player.cameraPosition.y +
        rig.positionBobY;

    camera.z =
        player.cameraPosition.z +
        rightZ * rig.positionBobX;

    camera.yawRadians =
        (player.yawDegrees +
         rig.yawDegrees) *
        kDegreesToRadians;

    camera.pitchRadians =
        (player.pitchDegrees +
         rig.pitchDegrees) *
        kDegreesToRadians;

    camera.verticalFovDegrees =
        std::clamp(
            72.0f +
                rig.fovAddDegrees,
            60.0f,
            90.0f);

    return camera;
}

} // namespace

extern "C" void android_main(
    struct android_app* app) {
    NativeAppState state{};

    state.runtime.onEvent(
        xziel::AndroidLifecycleEvent::Create);

    configurePrototypeMap(
        state);
    configurePrototypeQuest(
        state);

    const auto prototypeMapLoad =
        state.mapRuntime.load(
            state.mapDefinition,
            state.player,
            state.horde,
            state.interaction);

    if (!prototypeMapLoad.success) {
        logError(
            "Prototype map failed to load into Xziel map runtime");
    }

    xziel::WeatherConfig prototypeStorm{};
    prototypeStorm.rainIntensity = 0.78f;
    prototypeStorm.windMetersPerSecond = {
        1.35f,
        0.0f,
        0.42f,
    };
    prototypeStorm.wetnessRisePerSecond = 0.18f;
    prototypeStorm.wetnessDryPerSecond = 0.025f;
    prototypeStorm.lightningIntervalSeconds = 7.5f;
    prototypeStorm.lightningDurationSeconds = 0.14f;
    prototypeStorm.lightningIntensity = 1.0f;
    prototypeStorm.fogDensity = 0.26f;
    prototypeStorm.fogHeightFalloff = 0.12f;
    prototypeStorm.precipitationOcclusion = true;
    prototypeStorm.splashParticles = true;
    prototypeStorm.wetSurfaceResponse = true;

    state.stormWeather =
        prototypeStorm;

    state.calmWeather =
        prototypeStorm;

    state.calmWeather.rainIntensity =
        0.0f;

    state.calmWeather.windMetersPerSecond = {
        0.20f,
        0.0f,
        0.08f,
    };

    state.calmWeather.lightningIntensity =
        0.0f;

    state.calmWeather.fogDensity =
        0.10f;

    state.environment.setWeather(
        state.stormWeather);
    state.environment.setQuality(
        xziel::RenderQuality::High);

    if (app->activity != nullptr) {
        state.javaVm =
            app->activity->vm;
        state.javaActivity =
            app->activity->javaGameActivity;
    }

    if (state.javaVm != nullptr) {
        const jint getEnvResult =
            state.javaVm->GetEnv(
                reinterpret_cast<void**>(
                    &state.jniEnv),
                JNI_VERSION_1_6);

        if (getEnvResult == JNI_EDETACHED) {
            if (state.javaVm->AttachCurrentThread(
                    &state.jniEnv,
                    nullptr) == JNI_OK) {
                state.attachedToJvm = true;
                logInfo(
                    "XZIEL_APP_THREAD_ATTACHED_TO_JVM");
            } else {
                state.jniEnv = nullptr;
                logError(
                    "Unable to attach native app thread to JVM; "
                    "Swappy will use fallback present path");
            }
        } else if (getEnvResult != JNI_OK) {
            state.jniEnv = nullptr;
            logError(
                "Unable to obtain JNIEnv; "
                "Swappy will use fallback present path");
        }
    }

    app->userData = &state;
    app->onAppCmd = handleCommand;

    if (!state.input.initialize(
            app,
            kPackageName)) {
        logError(
            "Input adapter initialization failed; "
            "continuing with renderer-only prototype");
    }

    refreshDisplayRotation(
        state);

    if (!state.hapticsBridge.initialize(
            state.jniEnv,
            state.javaActivity)) {
        logInfo(
            "Haptics unavailable; gameplay continues without vibration");
    }

    if (!state.audio.initialize()) {
        logInfo(
            "AAudio unavailable; gameplay continues with silent fallback");
    }

    logInfo("XZIEL_NATIVE_BOOT");

    while (!app->destroyRequested) {
        const auto runtimeState =
            state.runtime.state();

        const bool animating =
            runtimeState.canRender &&
            state.hasWindow &&
            state.renderer.ready();

        int outEvents = 0;
        android_poll_source* source = nullptr;

        while (true) {
            const int identifier =
                ALooper_pollOnce(
                    animating ? 0 : -1,
                    nullptr,
                    &outEvents,
                    reinterpret_cast<void**>(
                        &source));

            if (identifier == ALOOPER_POLL_TIMEOUT ||
                identifier == ALOOPER_POLL_ERROR) {
                break;
            }

            if (identifier ==
                xziel::android::AndroidInputAdapter::
                    sensorLooperIdentifier()) {
                state.input.handleLooperIdentifier(
                    identifier);
            }

            if (source != nullptr) {
                source->process(
                    source->app,
                    source);
            }

            if (app->destroyRequested ||
                animating) {
                break;
            }
        }

        if (app->destroyRequested) {
            break;
        }

        const auto latest =
            state.runtime.state();

        const auto now =
            std::chrono::steady_clock::now();

        const float frameDelta =
            computeFrameDelta(
                state,
                now);

        state.audio.service();

        state.hapticElapsedSeconds =
            std::min(
                state.hapticElapsedSeconds +
                    frameDelta,
                1.0f);

        state.thermalPollSeconds +=
            frameDelta;

        if (state.thermalPollSeconds >= 1.0f) {
            state.thermalLevel =
                queryThermalLevel(
                    state);

            state.batterySaver =
                queryPowerSaveMode(
                    state);

            state.displayRefreshHz =
                queryRefreshRate(
                    state);

            state.thermalPollSeconds = 0.0f;
        }

        if (state.memoryPressureSeconds > 0.0f) {
            state.memoryPressureSeconds =
                std::max(
                    0.0f,
                    state.memoryPressureSeconds -
                        frameDelta);

            if (state.memoryPressureSeconds <= 0.0f) {
                state.memoryPressure =
                    xziel::MemoryPressure::Normal;
            }
        }

        state.hitMarkerSeconds =
            std::max(
                0.0f,
                state.hitMarkerSeconds -
                    frameDelta);

        state.criticalHitSeconds =
            std::max(
                0.0f,
                state.criticalHitSeconds -
                    frameDelta);

        state.impactFxSeconds =
            std::max(
                0.0f,
                state.impactFxSeconds -
                    frameDelta);

        state.decapFxSeconds =
            std::max(
                0.0f,
                state.decapFxSeconds -
                    frameDelta);

        state.muzzleFlashSeconds =
            std::max(
                0.0f,
                state.muzzleFlashSeconds -
                    frameDelta);

        state.zombieAttackFlashSeconds =
            std::max(
                0.0f,
                state.zombieAttackFlashSeconds -
                    frameDelta);

        state.scorePulseSeconds =
            std::max(
                0.0f,
                state.scorePulseSeconds -
                    frameDelta);

        state.purchaseDeniedSeconds =
            std::max(
                0.0f,
                state.purchaseDeniedSeconds -
                    frameDelta);

        const auto* prototypeDoor =
            state.mapRuntime.doors().frame(
                kPrototypeDoorId);

        const float doorTargetAlpha =
            prototypeDoor != nullptr &&
                    prototypeDoor->open
            ? 1.0f
            : 0.0f;

        const float doorStep =
            frameDelta *
            1.65f;

        if (state.prototypeDoorOpenAlpha <
            doorTargetAlpha) {
            state.prototypeDoorOpenAlpha =
                std::min(
                    doorTargetAlpha,
                    state.prototypeDoorOpenAlpha +
                        doorStep);
        } else {
            state.prototypeDoorOpenAlpha =
                std::max(
                    doorTargetAlpha,
                    state.prototypeDoorOpenAlpha -
                        doorStep);
        }

        state.renderWorkload =
            state.performance.advance(
                {
                    .cpuFrameMs =
                        frameDelta * 1000.0f,
                    .gpuFrameMs = 0.0f,
                    .thermal =
                        state.thermalLevel,
                },
                frameDelta);

        const auto runtimePolicy =
            state.runtimePolicyPlanner.plan(
                {
                    .gameMode =
                        xziel::UserGameMode::Standard,
                    .memoryPressure =
                        state.memoryPressure,
                    .displayRefreshHz =
                        state.displayRefreshHz,
                    .batterySaver =
                        state.batterySaver,
                    .charging = false,
                });

        state.renderWorkload =
            state.runtimePolicyPlanner.
                applyCeiling(
                    state.renderWorkload,
                    runtimePolicy);

        state.renderer.setPreferredFrameRate(
            runtimePolicy.preferredFps);

        state.environment.setQuality(
            state.renderWorkload.
                quality);

        state.environmentFrame =
            state.environment.advance(
                frameDelta);

        const float windSpeed =
            std::sqrt(
                state.environmentFrame.
                    windMetersPerSecond.x *
                    state.environmentFrame.
                        windMetersPerSecond.x +
                state.environmentFrame.
                    windMetersPerSecond.z *
                    state.environmentFrame.
                        windMetersPerSecond.z);

        state.waterFrame =
            state.water.advance(
                windSpeed,
                state.environmentFrame.
                    rainIntensity,
                frameDelta);

        state.input.beginFrame(
            frameDelta);

        state.input.setInteractAvailable(
            state.interactionFrame.
                promptVisible &&
            state.vitals.frame().
                alive);

        const int width =
            app->window != nullptr
            ? ANativeWindow_getWidth(
                  app->window)
            : 0;

        const int height =
            app->window != nullptr
            ? ANativeWindow_getHeight(
                  app->window)
            : 0;

        state.input.consumeInputBuffer(
            app,
            width,
            height);

        const auto inputSnapshot =
            state.input.snapshot();

        if (latest.canSimulate) {
            state.engine.submitInput(
                inputSnapshot.input);

            const auto stats =
                state.engine.advance(
                    static_cast<double>(
                        frameDelta));

            advancePlayer(
                state,
                inputSnapshot,
                stats);
        }

        if (!latest.canRender ||
            !state.hasWindow ||
            !state.renderer.ready()) {
            continue;
        }

        const float seconds =
            std::chrono::duration<float>(
                now - state.start).count();

        const auto rigFrame =
            advanceCameraRig(
                state,
                inputSnapshot,
                frameDelta);

        if (state.horrorFrame.
                requestAudioStinger) {
            state.audio.play(
                xziel::android::AndroidAudioCue::HorrorStinger,
                0.82f);

            requestHaptic(
                state,
                xziel::HapticEvent::HorrorStinger);
        }

        const auto camera =
            makeRenderCamera(
                state.player.frame(),
                rigFrame);

        const auto hud =
            makeHudState(
                state,
                inputSnapshot);

        const auto scene =
            makeSceneState(
                state);

        const auto environment =
            makeEnvironmentState(
                state);

        if (!state.renderer.drawFrame(
                seconds,
                camera,
                hud,
                scene,
                environment)) {
            const bool deviceLost =
                state.renderer.deviceLost();
            const auto recovery =
                state.watchdog.report(
                    {
                        .fault =
                            deviceLost
                            ? xziel::RendererFault::DeviceLost
                            : xziel::RendererFault::PresentFailed,
                        .frameIndex =
                            latest.generation,
                        .code = 0,
                    },
                    xziel::RendererBackend::Vulkan,
                    false);

            if (deviceLost ||
                recovery.recommendedAction ==
                    xziel::RendererRecoveryAction::RecreateDevice ||
                recovery.recommendedAction ==
                    xziel::RendererRecoveryAction::RecreateSwapchain) {
                // Stop all submission immediately. Android may keep the same
                // ANativeWindow alive after a Vulkan device loss, so waiting
                // exclusively for APP_CMD_INIT_WINDOW would deadlock recovery.
                state.hasWindow = false;
                state.renderer.shutdown();

                if (app->window != nullptr &&
                    state.renderer.initialize(
                        app->window,
                        app->activity->assetManager,
                        state.jniEnv,
                        state.javaActivity)) {
                    state.hasWindow = true;
                    state.watchdog.reset();
                    state.lastFrame =
                        std::chrono::steady_clock::now();
                    state.hasLastFrame = false;
                    logInfo(
                        deviceLost
                        ? "XZIEL_VULKAN_DEVICE_RECOVERED"
                        : "XZIEL_VULKAN_SURFACE_RECOVERED");
                } else {
                    logError(
                        deviceLost
                        ? "Vulkan device recovery failed; waiting for Android lifecycle"
                        : "Frame recovery failed; waiting for a fresh Android surface");
                }
            }
        }
    }

    state.input.shutdown();
    state.audio.shutdown();
    state.hapticsBridge.reset();
    state.renderer.shutdown();

    state.runtime.onEvent(
        xziel::AndroidLifecycleEvent::Destroy);

    if (state.attachedToJvm &&
        state.javaVm != nullptr) {
        state.javaVm->DetachCurrentThread();
        state.jniEnv = nullptr;
        state.attachedToJvm = false;
    }

    logInfo("XZIEL_NATIVE_EXIT");
}
