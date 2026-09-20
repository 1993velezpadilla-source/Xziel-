#include "vulkan_clear_renderer.hpp"

#include <android/log.h>
#include <game-activity/native_app_glue/android_native_app_glue.h>

#include "xziel/android_runtime.hpp"
#include "xziel/renderer_watchdog.hpp"

#include <chrono>

namespace {

constexpr const char* kTag = "XzielNative";

struct NativeAppState {
    xziel::AndroidRuntimeStateMachine runtime{};
    xziel::RendererWatchdog watchdog{};
    xziel::android::VulkanClearRenderer renderer{};

    bool hasWindow = false;

    std::chrono::steady_clock::time_point start =
        std::chrono::steady_clock::now();
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
            break;

        case APP_CMD_PAUSE:
            state->runtime.onEvent(
                xziel::AndroidLifecycleEvent::Pause);
            break;

        case APP_CMD_STOP:
            state->runtime.onEvent(
                xziel::AndroidLifecycleEvent::Stop);
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
                        app->window)) {
                    state->hasWindow = true;
                    state->watchdog.reset();
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
            logInfo("SURFACE_DESTROYED");
            break;

        case APP_CMD_DESTROY:
            state->runtime.onEvent(
                xziel::AndroidLifecycleEvent::Destroy);
            break;

        default:
            break;
    }
}

} // namespace

extern "C" void android_main(
    struct android_app* app) {
    NativeAppState state{};

    state.runtime.onEvent(
        xziel::AndroidLifecycleEvent::Create);

    app->userData = &state;
    app->onAppCmd = handleCommand;

    logInfo("XZIEL_NATIVE_BOOT");

    while (!app->destroyRequested) {
        const auto runtimeState =
            state.runtime.state();

        const bool animating =
            runtimeState.canRender &&
            state.hasWindow &&
            state.renderer.ready();

        int events = 0;
        android_poll_source* source = nullptr;

        while (ALooper_pollOnce(
                   animating ? 0 : -1,
                   nullptr,
                   &events,
                   reinterpret_cast<void**>(&source)) >= 0) {
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

        if (!latest.canRender ||
            !state.hasWindow ||
            !state.renderer.ready()) {
            continue;
        }

        const auto now =
            std::chrono::steady_clock::now();

        const float seconds =
            std::chrono::duration<float>(
                now - state.start).count();

        if (!state.renderer.drawFrame(seconds)) {
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

    state.renderer.shutdown();

    state.runtime.onEvent(
        xziel::AndroidLifecycleEvent::Destroy);

    logInfo("XZIEL_NATIVE_EXIT");
}
