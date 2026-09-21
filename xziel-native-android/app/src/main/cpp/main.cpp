#include "android_haptics.hpp"
#include "android_input.hpp"
#include "vulkan_clear_renderer.hpp"

#include <android/log.h>
#include <android/native_window.h>
#include <game-activity/native_app_glue/android_native_app_glue.h>

#include "xziel/android_runtime.hpp"
#include "xziel/camera_rig.hpp"
#include "xziel/engine.hpp"
#include "xziel/fps_player.hpp"
#include "xziel/hitscan.hpp"
#include "xziel/haptics.hpp"
#include "xziel/horror.hpp"
#include "xziel/player_vitals.hpp"
#include "xziel/renderer_watchdog.hpp"
#include "xziel/weapon.hpp"
#include "xziel/zombie_actor.hpp"

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

struct NativeAppState {
    xziel::AndroidRuntimeStateMachine runtime{};
    xziel::RendererWatchdog watchdog{};
    xziel::Engine engine{};
    xziel::FpsPlayerController player{};
    xziel::WeaponController weapon{};
    xziel::HordeDirector horde{};
    xziel::PlayerVitals vitals{};
    xziel::HorrorDirector horror{};
    xziel::HorrorFrame horrorFrame{};
    xziel::CameraRig cameraRig{};
    xziel::HapticsPlanner haptics{};
    xziel::android::AndroidHapticsBridge hapticsBridge{};
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
    float muzzleFlashSeconds = 0.0f;
    float zombieAttackFlashSeconds = 0.0f;
    float hapticElapsedSeconds = 1.0f;
};

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

        const auto hordeFrame =
            state.horde.step(
                playerFrame.feetPosition,
                fixedDelta);

        (void) hordeFrame;

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
                !state.vitals.frame().
                    alive) {
                continue;
            }

            if (state.vitals.applyDamage(
                    zombie->config().
                        attackDamage)) {
                damagedByZombie = true;
            }
        }

        if (damagedByZombie) {
            state.zombieAttackFlashSeconds =
                0.22f;

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
                    .firePressed = false,
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

            float nearestDistance =
                20.0f;

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
                    xziel::raycastAabb(
                        ray,
                        zombie->bounds(),
                        nearestDistance);

                if (!hit.hit ||
                    hit.distance >
                        nearestDistance) {
                    continue;
                }

                nearestDistance =
                    hit.distance;
                nearestSlot =
                    slot;
            }

            if (nearestSlot <
                    state.horde.capacity() &&
                state.horde.damageZombie(
                    nearestSlot,
                    34.0f)) {
                state.hitMarkerSeconds =
                    0.12f;
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

    hud.hitMarkerAlpha =
        std::clamp(
            state.hitMarkerSeconds /
                0.12f,
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

    return hud;
}

xziel::android::VulkanSceneState makeSceneState(
    const NativeAppState& state) noexcept {
    xziel::android::VulkanSceneState scene{};

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

        state.hapticElapsedSeconds =
            std::min(
                state.hapticElapsedSeconds +
                    frameDelta,
                1.0f);

        state.hitMarkerSeconds =
            std::max(
                0.0f,
                state.hitMarkerSeconds -
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

        state.input.beginFrame(
            frameDelta);

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

        if (!state.renderer.drawFrame(
                seconds,
                camera,
                hud,
                scene)) {
            const auto recovery =
                state.watchdog.report(
                    {
                        .fault =
                            xziel::RendererFault::PresentFailed,
                        .frameIndex =
                            latest.generation,
                        .code = 0,
                    },
                    xziel::RendererBackend::Vulkan,
                    false);

            if (recovery.recommendedAction ==
                xziel::RendererRecoveryAction::RecreateSwapchain) {
                state.hasWindow = false;
                state.renderer.shutdown();
                logError(
                    "Frame failed; waiting for a fresh Android surface");
            }
        }
    }

    state.input.shutdown();
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
