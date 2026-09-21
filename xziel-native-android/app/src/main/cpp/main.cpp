#include "android_input.hpp"
#include "vulkan_clear_renderer.hpp"

#include <android/log.h>
#include <android/native_window.h>
#include <game-activity/native_app_glue/android_native_app_glue.h>

#include "xziel/android_runtime.hpp"
#include "xziel/engine.hpp"
#include "xziel/renderer_watchdog.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>

namespace {

constexpr const char* kTag = "XzielNative";
constexpr const char* kPackageName =
    "com.xziel.engineprototype";

struct NativeAppState {
    xziel::AndroidRuntimeStateMachine runtime{};
    xziel::RendererWatchdog watchdog{};
    xziel::Engine engine{};
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

        if (latest.canSimulate) {
            state.engine.submitInput(
                state.input.snapshot().input);

            const auto stats =
                state.engine.advance(
                    static_cast<double>(
                        frameDelta));

            (void) stats;
        }

        if (!latest.canRender ||
            !state.hasWindow ||
            !state.renderer.ready()) {
            continue;
        }

        const float seconds =
            std::chrono::duration<float>(
                now - state.start).count();

        if (!state.renderer.drawFrame(
                seconds)) {
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
