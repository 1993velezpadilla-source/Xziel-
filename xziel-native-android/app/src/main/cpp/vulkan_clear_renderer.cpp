#include "vulkan_clear_renderer.hpp"

#include <android/log.h>
#include <swappy/swappyVk.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <limits>
#include <vector>

namespace xziel::android {

namespace {

constexpr const char* kTag = "XzielVulkan";

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

bool ok(VkResult result) noexcept {
    return result == VK_SUCCESS;
}

VkCompositeAlphaFlagBitsKHR chooseCompositeAlpha(
    VkCompositeAlphaFlagsKHR supported) noexcept {
    constexpr std::array<VkCompositeAlphaFlagBitsKHR, 4> order{
        VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
        VK_COMPOSITE_ALPHA_INHERIT_BIT_KHR,
        VK_COMPOSITE_ALPHA_PRE_MULTIPLIED_BIT_KHR,
        VK_COMPOSITE_ALPHA_POST_MULTIPLIED_BIT_KHR,
    };

    for (const auto value : order) {
        if ((supported & value) != 0) {
            return value;
        }
    }

    return VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR;
}

} // namespace

VulkanClearRenderer::~VulkanClearRenderer() {
    shutdown();
}

bool VulkanClearRenderer::initialize(
    ANativeWindow* window,
    AAssetManager* assetManager,
    JNIEnv* env,
    jobject javaActivity) noexcept {
    shutdown();

    if (window == nullptr || assetManager == nullptr) {
        logError("initialize requires window + asset manager");
        return false;
    }

    window_ = window;
    assetManager_ = assetManager;
    jniEnv_ = env;
    javaActivity_ = javaActivity;
    ANativeWindow_acquire(window_);

    if (!createInstance() ||
        !createSurface(window_) ||
        !selectPhysicalDevice() ||
        !createDevice() ||
        !createSwapchain() ||
        !createRenderPass() ||
        !createGraphicsPipeline() ||
        !createUiPipeline() ||
        !createImageViews() ||
        !createDepthResources() ||
        !createCommandResources() ||
        !createReflectionFallbackResources() ||
        !createFramebuffers() ||
        !createSyncObjects()) {
        logError("Vulkan initialization failed");
        shutdown();
        return false;
    }

    initialized_ = true;
    logInfo("XZIEL_VULKAN_3D_READY");
    return true;
}

void VulkanClearRenderer::shutdown() noexcept {
    initialized_ = false;

    if (device_ != VK_NULL_HANDLE) {
        vkDeviceWaitIdle(device_);
    }

    for (auto& frame : frames_) {
        if (frame.imageAvailable != VK_NULL_HANDLE &&
            device_ != VK_NULL_HANDLE) {
            vkDestroySemaphore(
                device_,
                frame.imageAvailable,
                nullptr);
        }

        if (frame.renderFinished != VK_NULL_HANDLE &&
            device_ != VK_NULL_HANDLE) {
            vkDestroySemaphore(
                device_,
                frame.renderFinished,
                nullptr);
        }

        if (frame.inFlight != VK_NULL_HANDLE &&
            device_ != VK_NULL_HANDLE) {
            vkDestroyFence(
                device_,
                frame.inFlight,
                nullptr);
        }

        frame = {};
    }

    destroySwapchainResources();

    if (commandPool_ != VK_NULL_HANDLE &&
        device_ != VK_NULL_HANDLE) {
        vkDestroyCommandPool(
            device_,
            commandPool_,
            nullptr);
        commandPool_ = VK_NULL_HANDLE;
    }

    if (device_ != VK_NULL_HANDLE) {
        vkDestroyDevice(
            device_,
            nullptr);
        device_ = VK_NULL_HANDLE;
    }

    graphicsQueue_ = VK_NULL_HANDLE;
    physicalDevice_ = VK_NULL_HANDLE;
    graphicsQueueFamily_ = UINT32_MAX;

    if (surface_ != VK_NULL_HANDLE &&
        instance_ != VK_NULL_HANDLE) {
        vkDestroySurfaceKHR(
            instance_,
            surface_,
            nullptr);
        surface_ = VK_NULL_HANDLE;
    }

    if (instance_ != VK_NULL_HANDLE) {
        vkDestroyInstance(
            instance_,
            nullptr);
        instance_ = VK_NULL_HANDLE;
    }

    if (window_ != nullptr) {
        ANativeWindow_release(window_);
        window_ = nullptr;
    }

    assetManager_ = nullptr;
    jniEnv_ = nullptr;
    javaActivity_ = nullptr;
    refreshDurationNs_ = 0;
    swappyInitialized_ = false;
    depthFormat_ = VK_FORMAT_UNDEFINED;
    frameIndex_ = 0;
}

void VulkanClearRenderer::setPreferredFrameRate(
    float framesPerSecond) noexcept {
    if (!std::isfinite(framesPerSecond) ||
        framesPerSecond <= 0.0f) {
        return;
    }

    preferredFrameRate_ =
        std::clamp(
            framesPerSecond,
            30.0f,
            240.0f);

    if (!swappyInitialized_ ||
        device_ == VK_NULL_HANDLE ||
        swapchain_ == VK_NULL_HANDLE) {
        return;
    }

    const double targetNs =
        1000000000.0 /
        static_cast<double>(
            preferredFrameRate_);

    std::uint64_t intervalNs =
        static_cast<std::uint64_t>(
            std::llround(
                targetNs));

    if (refreshDurationNs_ > 0) {
        intervalNs =
            std::max(
                intervalNs,
                refreshDurationNs_);
    }

    if (intervalNs ==
        requestedSwapIntervalNs_) {
        return;
    }

    SwappyVk_setSwapIntervalNS(
        device_,
        swapchain_,
        intervalNs);

    requestedSwapIntervalNs_ =
        intervalNs;
}

bool VulkanClearRenderer::drawFrame(
    float timeSeconds,
    const VulkanCamera& camera,
    const VulkanHudState& hud,
    const VulkanSceneState& scene,
    const VulkanEnvironmentState& environment) noexcept {
    if (!initialized_ ||
        device_ == VK_NULL_HANDLE ||
        swapchain_ == VK_NULL_HANDLE) {
        return false;
    }

    // Keep one reusable offscreen reflection target synchronized with the
    // adaptive workload. Allocation happens only when the scale changes, never
    // as per-frame churn. Failure is deliberately non-fatal: probe/shader
    // fallback remains available on memory-constrained devices.
    const float reflectionCoverage =
        std::clamp(
            environment.planarReflectionScreenCoverage,
            0.0f,
            1.0f);
    const bool reflectionContributes =
        environment.planarReflectionVisible &&
        reflectionCoverage > 0.0025f;

    if (reflectionContributes) {
        reflectionInvisibleFrames_ = 0;
    } else if (reflectionInvisibleFrames_ < UINT32_MAX) {
        ++reflectionInvisibleFrames_;
    }

    const float qualityReflectionScale =
        std::clamp(
            environment.planarReflectionScale,
            0.0f,
            1.0f);
    const bool targetWantedByQuality =
        environment.maxPlanarReflectionPasses > 0 &&
        qualityReflectionScale > 0.0f;

    // Quality policy and temporary camera visibility are deliberately
    // separate. Looking away keeps a valid target warm for a short grace
    // period; a quality/thermal downgrade releases it immediately.
    const float requestedReflectionScale =
        targetWantedByQuality
        ? qualityReflectionScale
        : 0.0f;

    const bool shouldAllocateReflectionTarget =
        targetWantedByQuality &&
        reflectionContributes &&
        (reflectionColorImage_ == VK_NULL_HANDLE ||
         std::abs(
             requestedReflectionScale -
             reflectionTargetScale_) > 0.025f);

    if (shouldAllocateReflectionTarget) {
        if (!ok(vkDeviceWaitIdle(device_))) {
            return false;
        }
        (void) createReflectionTarget(
            requestedReflectionScale);
    } else if (!targetWantedByQuality &&
               reflectionColorImage_ != VK_NULL_HANDLE) {
        if (!ok(vkDeviceWaitIdle(device_))) {
            return false;
        }
        destroyReflectionTarget();
    } else if (!reflectionContributes &&
               reflectionColorImage_ != VK_NULL_HANDLE &&
               reflectionInvisibleFrames_ >= 90U) {
        // Camera-facing changes are transient: debounce only this case so a
        // quick turn never creates a device-idle destroy/reallocate loop.
        if (!ok(vkDeviceWaitIdle(device_))) {
            return false;
        }
        destroyReflectionTarget();
    }

    auto& frame =
        frames_[frameIndex_ % kFramesInFlight];

    VkResult result =
        vkWaitForFences(
            device_,
            1,
            &frame.inFlight,
            VK_TRUE,
            UINT64_MAX);

    if (!ok(result)) {
        logError("vkWaitForFences failed");
        return false;
    }

    std::uint32_t imageIndex = 0;

    result =
        vkAcquireNextImageKHR(
            device_,
            swapchain_,
            UINT64_MAX,
            frame.imageAvailable,
            VK_NULL_HANDLE,
            &imageIndex);

    if (result == VK_ERROR_OUT_OF_DATE_KHR) {
        return recreateSwapchain();
    }

    const bool suboptimal =
        result == VK_SUBOPTIMAL_KHR;

    if (result != VK_SUCCESS && !suboptimal) {
        logError("vkAcquireNextImageKHR failed");
        return false;
    }

    if (imageIndex >= imageFences_.size()) {
        logError("invalid swapchain image index");
        return false;
    }

    if (imageFences_[imageIndex] != VK_NULL_HANDLE) {
        result =
            vkWaitForFences(
                device_,
                1,
                &imageFences_[imageIndex],
                VK_TRUE,
                UINT64_MAX);

        if (!ok(result)) {
            logError("image ownership fence wait failed");
            return false;
        }
    }

    imageFences_[imageIndex] =
        frame.inFlight;

    result =
        vkResetFences(
            device_,
            1,
            &frame.inFlight);

    if (!ok(result)) {
        logError("vkResetFences failed");
        return false;
    }

    if (!recordDrawCommand(
            imageIndex,
            timeSeconds,
            camera,
            hud,
            scene,
            environment)) {
        return false;
    }

    const VkPipelineStageFlags waitStage =
        VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;

    VkSubmitInfo submit{
        VK_STRUCTURE_TYPE_SUBMIT_INFO
    };
    submit.waitSemaphoreCount = 1;
    submit.pWaitSemaphores =
        &frame.imageAvailable;
    submit.pWaitDstStageMask =
        &waitStage;
    submit.commandBufferCount = 1;
    submit.pCommandBuffers =
        &commandBuffers_[imageIndex];
    submit.signalSemaphoreCount = 1;
    submit.pSignalSemaphores =
        &frame.renderFinished;

    result =
        vkQueueSubmit(
            graphicsQueue_,
            1,
            &submit,
            frame.inFlight);

    if (!ok(result)) {
        logError("vkQueueSubmit failed");
        return false;
    }

    VkPresentInfoKHR present{
        VK_STRUCTURE_TYPE_PRESENT_INFO_KHR
    };
    present.waitSemaphoreCount = 1;
    present.pWaitSemaphores =
        &frame.renderFinished;
    present.swapchainCount = 1;
    present.pSwapchains =
        &swapchain_;
    present.pImageIndices =
        &imageIndex;

    result =
        swappyInitialized_
        ? SwappyVk_queuePresent(
              graphicsQueue_,
              &present)
        : vkQueuePresentKHR(
              graphicsQueue_,
              &present);

    if (result == VK_ERROR_OUT_OF_DATE_KHR ||
        result == VK_SUBOPTIMAL_KHR ||
        suboptimal) {
        if (!recreateSwapchain()) {
            return false;
        }
    } else if (!ok(result)) {
        logError("vkQueuePresentKHR failed");
        return false;
    }

    ++frameIndex_;
    return true;
}

bool VulkanClearRenderer::ready() const noexcept {
    return initialized_;
}

bool VulkanClearRenderer::createInstance() noexcept {
    constexpr std::array<const char*, 2>
        extensions{
            VK_KHR_SURFACE_EXTENSION_NAME,
            VK_KHR_ANDROID_SURFACE_EXTENSION_NAME,
        };

    VkApplicationInfo appInfo{
        VK_STRUCTURE_TYPE_APPLICATION_INFO
    };
    appInfo.pApplicationName =
        "Xziel Engine Prototype";
    appInfo.applicationVersion =
        VK_MAKE_API_VERSION(0, 0, 0, 2);
    appInfo.pEngineName =
        "Xziel Engine";
    appInfo.engineVersion =
        VK_MAKE_API_VERSION(0, 0, 0, 2);
    appInfo.apiVersion =
        VK_API_VERSION_1_1;

    VkInstanceCreateInfo createInfo{
        VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO
    };
    createInfo.pApplicationInfo =
        &appInfo;
    createInfo.enabledExtensionCount =
        static_cast<std::uint32_t>(
            extensions.size());
    createInfo.ppEnabledExtensionNames =
        extensions.data();

    const VkResult result =
        vkCreateInstance(
            &createInfo,
            nullptr,
            &instance_);

    if (!ok(result)) {
        logError("vkCreateInstance failed");
        return false;
    }

    return true;
}

bool VulkanClearRenderer::createSurface(
    ANativeWindow* window) noexcept {
    VkAndroidSurfaceCreateInfoKHR createInfo{
        VK_STRUCTURE_TYPE_ANDROID_SURFACE_CREATE_INFO_KHR
    };
    createInfo.window = window;

    const VkResult result =
        vkCreateAndroidSurfaceKHR(
            instance_,
            &createInfo,
            nullptr,
            &surface_);

    if (!ok(result)) {
        logError("vkCreateAndroidSurfaceKHR failed");
        return false;
    }

    return true;
}

bool VulkanClearRenderer::selectPhysicalDevice() noexcept {
    std::uint32_t count = 0;

    VkResult result =
        vkEnumeratePhysicalDevices(
            instance_,
            &count,
            nullptr);

    if (!ok(result) || count == 0) {
        logError("No Vulkan physical device found");
        return false;
    }

    std::vector<VkPhysicalDevice> devices(count);

    result =
        vkEnumeratePhysicalDevices(
            instance_,
            &count,
            devices.data());

    if (!ok(result)) {
        logError("vkEnumeratePhysicalDevices failed");
        return false;
    }

    for (const auto candidate : devices) {
        VkPhysicalDeviceProperties properties{};
        vkGetPhysicalDeviceProperties(
            candidate,
            &properties);

        if (VK_API_VERSION_MAJOR(
                properties.apiVersion) < 1 ||
            (VK_API_VERSION_MAJOR(
                 properties.apiVersion) == 1 &&
             VK_API_VERSION_MINOR(
                 properties.apiVersion) < 1)) {
            continue;
        }

        std::uint32_t extensionCount = 0;

        if (!ok(
                vkEnumerateDeviceExtensionProperties(
                    candidate,
                    nullptr,
                    &extensionCount,
                    nullptr))) {
            continue;
        }

        std::vector<VkExtensionProperties>
            extensions(extensionCount);

        if (!ok(
                vkEnumerateDeviceExtensionProperties(
                    candidate,
                    nullptr,
                    &extensionCount,
                    extensions.data()))) {
            continue;
        }

        bool hasSwapchain = false;

        for (const auto& extension : extensions) {
            if (std::strcmp(
                    extension.extensionName,
                    VK_KHR_SWAPCHAIN_EXTENSION_NAME) == 0) {
                hasSwapchain = true;
                break;
            }
        }

        if (!hasSwapchain) {
            continue;
        }

        std::uint32_t queueCount = 0;

        vkGetPhysicalDeviceQueueFamilyProperties(
            candidate,
            &queueCount,
            nullptr);

        std::vector<VkQueueFamilyProperties>
            queues(queueCount);

        vkGetPhysicalDeviceQueueFamilyProperties(
            candidate,
            &queueCount,
            queues.data());

        for (std::uint32_t i = 0;
             i < queueCount;
             ++i) {
            VkBool32 present = VK_FALSE;

            if (!ok(
                    vkGetPhysicalDeviceSurfaceSupportKHR(
                        candidate,
                        i,
                        surface_,
                        &present))) {
                continue;
            }

            const bool graphics =
                (queues[i].queueFlags &
                 VK_QUEUE_GRAPHICS_BIT) != 0;

            if (graphics && present == VK_TRUE) {
                physicalDevice_ = candidate;
                graphicsQueueFamily_ = i;
                return true;
            }
        }
    }

    logError(
        "No Vulkan 1.1 device supports graphics + present + swapchain");
    return false;
}

bool VulkanClearRenderer::createDevice() noexcept {
    constexpr float priority = 1.0f;

    VkDeviceQueueCreateInfo queueInfo{
        VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO
    };
    queueInfo.queueFamilyIndex =
        graphicsQueueFamily_;
    queueInfo.queueCount = 1;
    queueInfo.pQueuePriorities =
        &priority;

    std::uint32_t availableExtensionCount = 0;
    if (!ok(
            vkEnumerateDeviceExtensionProperties(
                physicalDevice_,
                nullptr,
                &availableExtensionCount,
                nullptr))) {
        logError("device extension count query failed");
        return false;
    }

    std::vector<VkExtensionProperties>
        availableExtensions(
            availableExtensionCount);

    if (availableExtensionCount > 0 &&
        !ok(
            vkEnumerateDeviceExtensionProperties(
                physicalDevice_,
                nullptr,
                &availableExtensionCount,
                availableExtensions.data()))) {
        logError("device extension list query failed");
        return false;
    }

    std::uint32_t swappyExtensionCount = 0;
    SwappyVk_determineDeviceExtensions(
        physicalDevice_,
        availableExtensionCount,
        availableExtensions.empty()
            ? nullptr
            : availableExtensions.data(),
        &swappyExtensionCount,
        nullptr);

    std::vector<std::array<
        char,
        VK_MAX_EXTENSION_NAME_SIZE + 1U>>
        swappyExtensionStorage(
            swappyExtensionCount);

    std::vector<char*>
        swappyExtensionNames(
            swappyExtensionCount);

    for (std::uint32_t i = 0;
         i < swappyExtensionCount;
         ++i) {
        swappyExtensionStorage[i].fill('\0');
        swappyExtensionNames[i] =
            swappyExtensionStorage[i].data();
    }

    if (swappyExtensionCount > 0) {
        std::uint32_t requestedCount =
            swappyExtensionCount;

        SwappyVk_determineDeviceExtensions(
            physicalDevice_,
            availableExtensionCount,
            availableExtensions.data(),
            &requestedCount,
            swappyExtensionNames.data());

        swappyExtensionCount =
            std::min(
                swappyExtensionCount,
                requestedCount);
    }

    std::vector<const char*>
        enabledExtensions;
    enabledExtensions.reserve(
        static_cast<std::size_t>(
            swappyExtensionCount) + 1U);

    enabledExtensions.push_back(
        VK_KHR_SWAPCHAIN_EXTENSION_NAME);

    for (std::uint32_t i = 0;
         i < swappyExtensionCount;
         ++i) {
        const char* name =
            swappyExtensionNames[i];

        if (name == nullptr ||
            name[0] == '\0') {
            continue;
        }

        bool duplicate = false;
        for (const char* existing :
             enabledExtensions) {
            if (std::strcmp(
                    existing,
                    name) == 0) {
                duplicate = true;
                break;
            }
        }

        if (!duplicate) {
            enabledExtensions.push_back(
                name);
        }
    }

    VkDeviceCreateInfo createInfo{
        VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO
    };
    createInfo.queueCreateInfoCount = 1;
    createInfo.pQueueCreateInfos =
        &queueInfo;
    createInfo.enabledExtensionCount =
        static_cast<std::uint32_t>(
            enabledExtensions.size());
    createInfo.ppEnabledExtensionNames =
        enabledExtensions.data();

    const VkResult result =
        vkCreateDevice(
            physicalDevice_,
            &createInfo,
            nullptr,
            &device_);

    if (!ok(result)) {
        logError("vkCreateDevice failed");
        return false;
    }

    vkGetDeviceQueue(
        device_,
        graphicsQueueFamily_,
        0,
        &graphicsQueue_);

    if (graphicsQueue_ == VK_NULL_HANDLE) {
        logError("vkGetDeviceQueue returned null");
        return false;
    }

    SwappyVk_setQueueFamilyIndex(
        device_,
        graphicsQueue_,
        graphicsQueueFamily_);

    return true;
}

bool VulkanClearRenderer::chooseSurfaceFormat(
    VkSurfaceFormatKHR& out) const noexcept {
    std::uint32_t count = 0;

    VkResult result =
        vkGetPhysicalDeviceSurfaceFormatsKHR(
            physicalDevice_,
            surface_,
            &count,
            nullptr);

    if (!ok(result) || count == 0) {
        return false;
    }

    std::vector<VkSurfaceFormatKHR> formats(count);

    result =
        vkGetPhysicalDeviceSurfaceFormatsKHR(
            physicalDevice_,
            surface_,
            &count,
            formats.data());

    if (!ok(result)) {
        return false;
    }

    for (const auto& format : formats) {
        if (format.format ==
                VK_FORMAT_R8G8B8A8_SRGB &&
            format.colorSpace ==
                VK_COLOR_SPACE_SRGB_NONLINEAR_KHR) {
            out = format;
            return true;
        }
    }

    for (const auto& format : formats) {
        if (format.format ==
                VK_FORMAT_B8G8R8A8_SRGB &&
            format.colorSpace ==
                VK_COLOR_SPACE_SRGB_NONLINEAR_KHR) {
            out = format;
            return true;
        }
    }

    out = formats.front();
    return true;
}

bool VulkanClearRenderer::chooseDepthFormat(
    VkFormat& out) const noexcept {
    constexpr std::array<VkFormat, 3> candidates{
        VK_FORMAT_D32_SFLOAT,
        VK_FORMAT_D24_UNORM_S8_UINT,
        VK_FORMAT_D16_UNORM,
    };

    for (const auto format : candidates) {
        VkFormatProperties properties{};

        vkGetPhysicalDeviceFormatProperties(
            physicalDevice_,
            format,
            &properties);

        if ((properties.optimalTilingFeatures &
             VK_FORMAT_FEATURE_DEPTH_STENCIL_ATTACHMENT_BIT) != 0) {
            out = format;
            return true;
        }
    }

    return false;
}

bool VulkanClearRenderer::findMemoryType(
    std::uint32_t typeBits,
    VkMemoryPropertyFlags required,
    std::uint32_t& outIndex) const noexcept {
    VkPhysicalDeviceMemoryProperties memoryProperties{};

    vkGetPhysicalDeviceMemoryProperties(
        physicalDevice_,
        &memoryProperties);

    for (std::uint32_t i = 0;
         i < memoryProperties.memoryTypeCount;
         ++i) {
        const bool allowed =
            (typeBits & (1U << i)) != 0;

        const bool matches =
            (memoryProperties.memoryTypes[i].propertyFlags &
             required) == required;

        if (allowed && matches) {
            outIndex = i;
            return true;
        }
    }

    return false;
}

bool VulkanClearRenderer::createSwapchain() noexcept {
    VkSurfaceCapabilitiesKHR caps{};

    if (!ok(
            vkGetPhysicalDeviceSurfaceCapabilitiesKHR(
                physicalDevice_,
                surface_,
                &caps))) {
        logError("surface capability query failed");
        return false;
    }

    if ((caps.supportedUsageFlags &
         VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT) == 0) {
        logError(
            "surface does not support color attachment usage");
        return false;
    }

    VkSurfaceFormatKHR surfaceFormat{};

    if (!chooseSurfaceFormat(surfaceFormat)) {
        logError("No usable surface format");
        return false;
    }

    VkExtent2D extent = caps.currentExtent;

    if (extent.width ==
        std::numeric_limits<std::uint32_t>::max()) {
        const auto width =
            static_cast<std::uint32_t>(
                std::max(
                    1,
                    ANativeWindow_getWidth(window_)));

        const auto height =
            static_cast<std::uint32_t>(
                std::max(
                    1,
                    ANativeWindow_getHeight(window_)));

        extent.width =
            std::clamp(
                width,
                caps.minImageExtent.width,
                caps.maxImageExtent.width);

        extent.height =
            std::clamp(
                height,
                caps.minImageExtent.height,
                caps.maxImageExtent.height);
    }

    std::uint32_t imageCount =
        caps.minImageCount + 1U;

    if (caps.maxImageCount > 0) {
        imageCount =
            std::min(
                imageCount,
                caps.maxImageCount);
    }

    VkSwapchainCreateInfoKHR createInfo{
        VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR
    };
    createInfo.surface = surface_;
    createInfo.minImageCount = imageCount;
    createInfo.imageFormat =
        surfaceFormat.format;
    createInfo.imageColorSpace =
        surfaceFormat.colorSpace;
    createInfo.imageExtent = extent;
    createInfo.imageArrayLayers = 1;
    createInfo.imageUsage =
        VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT;
    createInfo.imageSharingMode =
        VK_SHARING_MODE_EXCLUSIVE;
    createInfo.preTransform =
        caps.currentTransform;
    createInfo.compositeAlpha =
        chooseCompositeAlpha(
            caps.supportedCompositeAlpha);
    createInfo.presentMode =
        VK_PRESENT_MODE_FIFO_KHR;
    createInfo.clipped = VK_TRUE;

    const VkResult result =
        vkCreateSwapchainKHR(
            device_,
            &createInfo,
            nullptr,
            &swapchain_);

    if (!ok(result)) {
        logError("vkCreateSwapchainKHR failed");
        return false;
    }

    swapchainFormat_ =
        surfaceFormat.format;
    swapchainExtent_ =
        extent;

    std::uint32_t actualCount = 0;

    if (!ok(
            vkGetSwapchainImagesKHR(
                device_,
                swapchain_,
                &actualCount,
                nullptr)) ||
        actualCount == 0) {
        logError("swapchain image count failed");
        return false;
    }

    swapchainImages_.resize(actualCount);

    if (!ok(
            vkGetSwapchainImagesKHR(
                device_,
                swapchain_,
                &actualCount,
                swapchainImages_.data()))) {
        logError("swapchain image list failed");
        return false;
    }

    imageFences_.assign(
        swapchainImages_.size(),
        VK_NULL_HANDLE);

    (void) initializeFramePacing();

    return true;
}

bool VulkanClearRenderer::initializeFramePacing() noexcept {
    swappyInitialized_ = false;
    refreshDurationNs_ = 0;
    requestedSwapIntervalNs_ = 0;

    if (jniEnv_ == nullptr ||
        javaActivity_ == nullptr ||
        physicalDevice_ == VK_NULL_HANDLE ||
        device_ == VK_NULL_HANDLE ||
        swapchain_ == VK_NULL_HANDLE ||
        window_ == nullptr) {
        logInfo("Swappy unavailable; using direct Vulkan present");
        return false;
    }

    const bool initialized =
        SwappyVk_initAndGetRefreshCycleDuration(
            jniEnv_,
            javaActivity_,
            physicalDevice_,
            device_,
            swapchain_,
            &refreshDurationNs_);

    if (!initialized ||
        refreshDurationNs_ == 0) {
        logInfo("Swappy init failed; using direct Vulkan present");
        refreshDurationNs_ = 0;
        return false;
    }

    SwappyVk_setWindow(
        device_,
        swapchain_,
        window_);

    SwappyVk_setAutoSwapInterval(true);
    SwappyVk_setAutoPipelineMode(true);

    // Begin at the native display cadence. Swappy may adapt the interval when
    // sustained frame cost requires it. RuntimePolicy will later choose
    // deliberate 60/90/120 targets.
    const std::uint64_t initialInterval =
        preferredFrameRate_ > 0.0f
        ? static_cast<std::uint64_t>(
              std::llround(
                  1000000000.0 /
                  static_cast<double>(
                      preferredFrameRate_)))
        : refreshDurationNs_;

    requestedSwapIntervalNs_ =
        std::max(
            initialInterval,
            refreshDurationNs_);

    SwappyVk_setSwapIntervalNS(
        device_,
        swapchain_,
        requestedSwapIntervalNs_);

    swappyInitialized_ = true;
    logInfo("XZIEL_SWAPPY_READY");
    return true;
}

bool VulkanClearRenderer::createRenderPass() noexcept {
    if (!chooseDepthFormat(depthFormat_)) {
        logError("No supported depth attachment format");
        return false;
    }

    VkAttachmentDescription color{};
    color.format = swapchainFormat_;
    color.samples =
        VK_SAMPLE_COUNT_1_BIT;
    color.loadOp =
        VK_ATTACHMENT_LOAD_OP_CLEAR;
    color.storeOp =
        VK_ATTACHMENT_STORE_OP_STORE;
    color.stencilLoadOp =
        VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    color.stencilStoreOp =
        VK_ATTACHMENT_STORE_OP_DONT_CARE;
    color.initialLayout =
        VK_IMAGE_LAYOUT_UNDEFINED;
    color.finalLayout =
        VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;

    VkAttachmentDescription depth{};
    depth.format = depthFormat_;
    depth.samples =
        VK_SAMPLE_COUNT_1_BIT;
    depth.loadOp =
        VK_ATTACHMENT_LOAD_OP_CLEAR;
    depth.storeOp =
        VK_ATTACHMENT_STORE_OP_DONT_CARE;
    depth.stencilLoadOp =
        VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    depth.stencilStoreOp =
        VK_ATTACHMENT_STORE_OP_DONT_CARE;
    depth.initialLayout =
        VK_IMAGE_LAYOUT_UNDEFINED;
    depth.finalLayout =
        VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;

    const std::array<VkAttachmentDescription, 2>
        attachments{color, depth};

    VkAttachmentReference colorReference{};
    colorReference.attachment = 0;
    colorReference.layout =
        VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;

    VkAttachmentReference depthReference{};
    depthReference.attachment = 1;
    depthReference.layout =
        VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;

    VkSubpassDescription subpass{};
    subpass.pipelineBindPoint =
        VK_PIPELINE_BIND_POINT_GRAPHICS;
    subpass.colorAttachmentCount = 1;
    subpass.pColorAttachments =
        &colorReference;
    subpass.pDepthStencilAttachment =
        &depthReference;

    VkSubpassDependency dependency{};
    dependency.srcSubpass =
        VK_SUBPASS_EXTERNAL;
    dependency.dstSubpass = 0;
    dependency.srcStageMask =
        VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
        VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
    dependency.dstStageMask =
        VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
        VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
    dependency.srcAccessMask = 0;
    dependency.dstAccessMask =
        VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
        VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;

    VkRenderPassCreateInfo createInfo{
        VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO
    };
    createInfo.attachmentCount =
        static_cast<std::uint32_t>(
            attachments.size());
    createInfo.pAttachments =
        attachments.data();
    createInfo.subpassCount = 1;
    createInfo.pSubpasses =
        &subpass;
    createInfo.dependencyCount = 1;
    createInfo.pDependencies =
        &dependency;

    const VkResult result =
        vkCreateRenderPass(
            device_,
            &createInfo,
            nullptr,
            &renderPass_);

    if (!ok(result)) {
        logError("vkCreateRenderPass failed");
        return false;
    }

    return true;
}

bool VulkanClearRenderer::createShaderModuleFromAsset(
    const char* assetPath,
    VkShaderModule& outModule) noexcept {
    outModule = VK_NULL_HANDLE;

    if (assetManager_ == nullptr ||
        assetPath == nullptr ||
        device_ == VK_NULL_HANDLE) {
        return false;
    }

    AAsset* asset =
        AAssetManager_open(
            assetManager_,
            assetPath,
            AASSET_MODE_BUFFER);

    if (asset == nullptr) {
        logError("Failed to open SPIR-V shader asset");
        return false;
    }

    const off_t length =
        AAsset_getLength(asset);

    if (length <= 0 ||
        (length % 4) != 0) {
        AAsset_close(asset);
        logError("Invalid SPIR-V shader asset size");
        return false;
    }

    std::vector<std::uint32_t> words(
        static_cast<std::size_t>(length) / 4U);

    const int bytesRead =
        AAsset_read(
            asset,
            words.data(),
            static_cast<std::size_t>(length));

    AAsset_close(asset);

    if (bytesRead < 0 ||
        static_cast<off_t>(bytesRead) != length) {
        logError("Failed reading complete SPIR-V shader asset");
        return false;
    }

    VkShaderModuleCreateInfo createInfo{
        VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO
    };
    createInfo.codeSize =
        static_cast<std::size_t>(length);
    createInfo.pCode =
        words.data();

    const VkResult result =
        vkCreateShaderModule(
            device_,
            &createInfo,
            nullptr,
            &outModule);

    if (!ok(result)) {
        logError("vkCreateShaderModule failed");
        outModule = VK_NULL_HANDLE;
        return false;
    }

    return true;
}

bool VulkanClearRenderer::createGraphicsPipeline() noexcept {
    VkShaderModule vertex =
        VK_NULL_HANDLE;
    VkShaderModule fragment =
        VK_NULL_HANDLE;

    if (!createShaderModuleFromAsset(
            "shaders/xziel_first.vert.spv",
            vertex) ||
        !createShaderModuleFromAsset(
            "shaders/xziel_first.frag.spv",
            fragment)) {
        if (vertex != VK_NULL_HANDLE) {
            vkDestroyShaderModule(
                device_,
                vertex,
                nullptr);
        }

        if (fragment != VK_NULL_HANDLE) {
            vkDestroyShaderModule(
                device_,
                fragment,
                nullptr);
        }

        return false;
    }

    const std::array<VkPipelineShaderStageCreateInfo, 2>
        stages{{
            {
                VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                nullptr,
                0,
                VK_SHADER_STAGE_VERTEX_BIT,
                vertex,
                "main",
                nullptr,
            },
            {
                VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                nullptr,
                0,
                VK_SHADER_STAGE_FRAGMENT_BIT,
                fragment,
                "main",
                nullptr,
            },
        }};

    VkPipelineVertexInputStateCreateInfo vertexInput{
        VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO
    };

    VkPipelineInputAssemblyStateCreateInfo inputAssembly{
        VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO
    };
    inputAssembly.topology =
        VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    inputAssembly.primitiveRestartEnable =
        VK_FALSE;

    VkViewport viewport{};
    viewport.x = 0.0f;
    viewport.y = 0.0f;
    viewport.width =
        static_cast<float>(
            swapchainExtent_.width);
    viewport.height =
        static_cast<float>(
            swapchainExtent_.height);
    viewport.minDepth = 0.0f;
    viewport.maxDepth = 1.0f;

    VkRect2D scissor{};
    scissor.offset = {0, 0};
    scissor.extent =
        swapchainExtent_;

    VkPipelineViewportStateCreateInfo viewportState{
        VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO
    };
    viewportState.viewportCount = 1;
    viewportState.pViewports =
        &viewport;
    viewportState.scissorCount = 1;
    viewportState.pScissors =
        &scissor;

    VkPipelineRasterizationStateCreateInfo raster{
        VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO
    };
    raster.depthClampEnable =
        VK_FALSE;
    raster.rasterizerDiscardEnable =
        VK_FALSE;
    raster.polygonMode =
        VK_POLYGON_MODE_FILL;
    raster.cullMode =
        VK_CULL_MODE_NONE;
    raster.frontFace =
        VK_FRONT_FACE_COUNTER_CLOCKWISE;
    raster.depthBiasEnable =
        VK_FALSE;
    raster.lineWidth = 1.0f;

    VkPipelineMultisampleStateCreateInfo multisample{
        VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO
    };
    multisample.rasterizationSamples =
        VK_SAMPLE_COUNT_1_BIT;
    multisample.sampleShadingEnable =
        VK_FALSE;

    VkPipelineDepthStencilStateCreateInfo depthStencil{
        VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO
    };
    depthStencil.depthTestEnable =
        VK_TRUE;
    depthStencil.depthWriteEnable =
        VK_TRUE;
    depthStencil.depthCompareOp =
        VK_COMPARE_OP_LESS_OR_EQUAL;
    depthStencil.depthBoundsTestEnable =
        VK_FALSE;
    depthStencil.stencilTestEnable =
        VK_FALSE;

    VkPipelineColorBlendAttachmentState colorAttachment{};
    colorAttachment.blendEnable =
        VK_FALSE;
    colorAttachment.colorWriteMask =
        VK_COLOR_COMPONENT_R_BIT |
        VK_COLOR_COMPONENT_G_BIT |
        VK_COLOR_COMPONENT_B_BIT |
        VK_COLOR_COMPONENT_A_BIT;

    VkPipelineColorBlendStateCreateInfo colorBlend{
        VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO
    };
    colorBlend.logicOpEnable =
        VK_FALSE;
    colorBlend.attachmentCount = 1;
    colorBlend.pAttachments =
        &colorAttachment;

    VkDescriptorSetLayoutBinding reflectionBinding{};
    reflectionBinding.binding = 0;
    reflectionBinding.descriptorType =
        VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    reflectionBinding.descriptorCount = 1;
    reflectionBinding.stageFlags =
        VK_SHADER_STAGE_FRAGMENT_BIT;

    VkDescriptorSetLayoutCreateInfo descriptorLayoutInfo{
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO
    };
    descriptorLayoutInfo.bindingCount = 1;
    descriptorLayoutInfo.pBindings = &reflectionBinding;

    if (!ok(
            vkCreateDescriptorSetLayout(
                device_,
                &descriptorLayoutInfo,
                nullptr,
                &reflectionDescriptorSetLayout_))) {
        vkDestroyShaderModule(device_, fragment, nullptr);
        vkDestroyShaderModule(device_, vertex, nullptr);
        logError("vkCreateDescriptorSetLayout reflection failed");
        return false;
    }

    VkPushConstantRange pushRange{};
    pushRange.stageFlags =
        VK_SHADER_STAGE_VERTEX_BIT;
    pushRange.offset = 0;
    pushRange.size =
        static_cast<std::uint32_t>(
            sizeof(PushConstants));

    VkPipelineLayoutCreateInfo layoutInfo{
        VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO
    };
    layoutInfo.setLayoutCount = 1;
    layoutInfo.pSetLayouts =
        &reflectionDescriptorSetLayout_;
    layoutInfo.pushConstantRangeCount = 1;
    layoutInfo.pPushConstantRanges =
        &pushRange;

    VkResult result =
        vkCreatePipelineLayout(
            device_,
            &layoutInfo,
            nullptr,
            &pipelineLayout_);

    if (!ok(result)) {
        vkDestroyShaderModule(
            device_,
            fragment,
            nullptr);
        vkDestroyShaderModule(
            device_,
            vertex,
            nullptr);
        logError("vkCreatePipelineLayout failed");
        return false;
    }

    VkGraphicsPipelineCreateInfo pipelineInfo{
        VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO
    };
    pipelineInfo.stageCount =
        static_cast<std::uint32_t>(
            stages.size());
    pipelineInfo.pStages =
        stages.data();
    pipelineInfo.pVertexInputState =
        &vertexInput;
    pipelineInfo.pInputAssemblyState =
        &inputAssembly;
    pipelineInfo.pViewportState =
        &viewportState;
    pipelineInfo.pRasterizationState =
        &raster;
    pipelineInfo.pMultisampleState =
        &multisample;
    pipelineInfo.pDepthStencilState =
        &depthStencil;
    pipelineInfo.pColorBlendState =
        &colorBlend;
    pipelineInfo.layout =
        pipelineLayout_;
    pipelineInfo.renderPass =
        renderPass_;
    pipelineInfo.subpass = 0;

    result =
        vkCreateGraphicsPipelines(
            device_,
            VK_NULL_HANDLE,
            1,
            &pipelineInfo,
            nullptr,
            &graphicsPipeline_);

    vkDestroyShaderModule(
        device_,
        fragment,
        nullptr);
    vkDestroyShaderModule(
        device_,
        vertex,
        nullptr);

    if (!ok(result)) {
        logError("vkCreateGraphicsPipelines failed");

        if (pipelineLayout_ != VK_NULL_HANDLE) {
            vkDestroyPipelineLayout(
                device_,
                pipelineLayout_,
                nullptr);
            pipelineLayout_ =
                VK_NULL_HANDLE;
        }

        graphicsPipeline_ =
            VK_NULL_HANDLE;
        return false;
    }

    logInfo("XZIEL_3D_PIPELINE_READY");
    return true;
}

bool VulkanClearRenderer::createUiPipeline() noexcept {
    VkShaderModule vertex =
        VK_NULL_HANDLE;
    VkShaderModule fragment =
        VK_NULL_HANDLE;

    if (!createShaderModuleFromAsset(
            "shaders/xziel_ui.vert.spv",
            vertex) ||
        !createShaderModuleFromAsset(
            "shaders/xziel_ui.frag.spv",
            fragment)) {
        if (vertex != VK_NULL_HANDLE) {
            vkDestroyShaderModule(
                device_,
                vertex,
                nullptr);
        }

        if (fragment != VK_NULL_HANDLE) {
            vkDestroyShaderModule(
                device_,
                fragment,
                nullptr);
        }

        return false;
    }

    const std::array<VkPipelineShaderStageCreateInfo, 2>
        stages{{
            {
                VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                nullptr,
                0,
                VK_SHADER_STAGE_VERTEX_BIT,
                vertex,
                "main",
                nullptr,
            },
            {
                VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                nullptr,
                0,
                VK_SHADER_STAGE_FRAGMENT_BIT,
                fragment,
                "main",
                nullptr,
            },
        }};

    VkPipelineVertexInputStateCreateInfo vertexInput{
        VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO
    };

    VkPipelineInputAssemblyStateCreateInfo inputAssembly{
        VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO
    };
    inputAssembly.topology =
        VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    inputAssembly.primitiveRestartEnable =
        VK_FALSE;

    VkViewport viewport{};
    viewport.x = 0.0f;
    viewport.y = 0.0f;
    viewport.width =
        static_cast<float>(
            swapchainExtent_.width);
    viewport.height =
        static_cast<float>(
            swapchainExtent_.height);
    viewport.minDepth = 0.0f;
    viewport.maxDepth = 1.0f;

    VkRect2D scissor{};
    scissor.offset = {0, 0};
    scissor.extent =
        swapchainExtent_;

    VkPipelineViewportStateCreateInfo viewportState{
        VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO
    };
    viewportState.viewportCount = 1;
    viewportState.pViewports =
        &viewport;
    viewportState.scissorCount = 1;
    viewportState.pScissors =
        &scissor;

    VkPipelineRasterizationStateCreateInfo raster{
        VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO
    };
    raster.depthClampEnable =
        VK_FALSE;
    raster.rasterizerDiscardEnable =
        VK_FALSE;
    raster.polygonMode =
        VK_POLYGON_MODE_FILL;
    raster.cullMode =
        VK_CULL_MODE_NONE;
    raster.frontFace =
        VK_FRONT_FACE_COUNTER_CLOCKWISE;
    raster.depthBiasEnable =
        VK_FALSE;
    raster.lineWidth = 1.0f;

    VkPipelineMultisampleStateCreateInfo multisample{
        VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO
    };
    multisample.rasterizationSamples =
        VK_SAMPLE_COUNT_1_BIT;
    multisample.sampleShadingEnable =
        VK_FALSE;

    VkPipelineDepthStencilStateCreateInfo depthStencil{
        VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO
    };
    depthStencil.depthTestEnable =
        VK_FALSE;
    depthStencil.depthWriteEnable =
        VK_FALSE;
    depthStencil.depthCompareOp =
        VK_COMPARE_OP_ALWAYS;
    depthStencil.depthBoundsTestEnable =
        VK_FALSE;
    depthStencil.stencilTestEnable =
        VK_FALSE;

    VkPipelineColorBlendAttachmentState colorAttachment{};
    colorAttachment.blendEnable =
        VK_TRUE;
    colorAttachment.srcColorBlendFactor =
        VK_BLEND_FACTOR_SRC_ALPHA;
    colorAttachment.dstColorBlendFactor =
        VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
    colorAttachment.colorBlendOp =
        VK_BLEND_OP_ADD;
    colorAttachment.srcAlphaBlendFactor =
        VK_BLEND_FACTOR_ONE;
    colorAttachment.dstAlphaBlendFactor =
        VK_BLEND_FACTOR_ONE_MINUS_SRC_ALPHA;
    colorAttachment.alphaBlendOp =
        VK_BLEND_OP_ADD;
    colorAttachment.colorWriteMask =
        VK_COLOR_COMPONENT_R_BIT |
        VK_COLOR_COMPONENT_G_BIT |
        VK_COLOR_COMPONENT_B_BIT |
        VK_COLOR_COMPONENT_A_BIT;

    VkPipelineColorBlendStateCreateInfo colorBlend{
        VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO
    };
    colorBlend.logicOpEnable =
        VK_FALSE;
    colorBlend.attachmentCount = 1;
    colorBlend.pAttachments =
        &colorAttachment;

    VkPushConstantRange pushRange{};
    pushRange.stageFlags =
        VK_SHADER_STAGE_VERTEX_BIT |
        VK_SHADER_STAGE_FRAGMENT_BIT;
    pushRange.offset = 0;
    pushRange.size =
        static_cast<std::uint32_t>(
            sizeof(UiPushConstants));

    VkPipelineLayoutCreateInfo layoutInfo{
        VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO
    };
    layoutInfo.pushConstantRangeCount = 1;
    layoutInfo.pPushConstantRanges =
        &pushRange;

    VkResult result =
        vkCreatePipelineLayout(
            device_,
            &layoutInfo,
            nullptr,
            &uiPipelineLayout_);

    if (!ok(result)) {
        vkDestroyShaderModule(
            device_,
            fragment,
            nullptr);
        vkDestroyShaderModule(
            device_,
            vertex,
            nullptr);
        logError("vkCreatePipelineLayout UI failed");
        return false;
    }

    VkGraphicsPipelineCreateInfo pipelineInfo{
        VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO
    };
    pipelineInfo.stageCount =
        static_cast<std::uint32_t>(
            stages.size());
    pipelineInfo.pStages =
        stages.data();
    pipelineInfo.pVertexInputState =
        &vertexInput;
    pipelineInfo.pInputAssemblyState =
        &inputAssembly;
    pipelineInfo.pViewportState =
        &viewportState;
    pipelineInfo.pRasterizationState =
        &raster;
    pipelineInfo.pMultisampleState =
        &multisample;
    pipelineInfo.pDepthStencilState =
        &depthStencil;
    pipelineInfo.pColorBlendState =
        &colorBlend;
    pipelineInfo.layout =
        uiPipelineLayout_;
    pipelineInfo.renderPass =
        renderPass_;
    pipelineInfo.subpass = 0;

    result =
        vkCreateGraphicsPipelines(
            device_,
            VK_NULL_HANDLE,
            1,
            &pipelineInfo,
            nullptr,
            &uiPipeline_);

    vkDestroyShaderModule(
        device_,
        fragment,
        nullptr);
    vkDestroyShaderModule(
        device_,
        vertex,
        nullptr);

    if (!ok(result)) {
        logError("vkCreateGraphicsPipelines UI failed");

        if (uiPipelineLayout_ != VK_NULL_HANDLE) {
            vkDestroyPipelineLayout(
                device_,
                uiPipelineLayout_,
                nullptr);
            uiPipelineLayout_ =
                VK_NULL_HANDLE;
        }

        uiPipeline_ =
            VK_NULL_HANDLE;
        return false;
    }

    logInfo("XZIEL_UI_PIPELINE_READY");
    return true;
}

bool VulkanClearRenderer::createImageViews() noexcept {
    imageViews_.assign(
        swapchainImages_.size(),
        VK_NULL_HANDLE);

    for (std::size_t i = 0;
         i < swapchainImages_.size();
         ++i) {
        VkImageViewCreateInfo view{
            VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO
        };
        view.image =
            swapchainImages_[i];
        view.viewType =
            VK_IMAGE_VIEW_TYPE_2D;
        view.format =
            swapchainFormat_;
        view.components = {
            VK_COMPONENT_SWIZZLE_IDENTITY,
            VK_COMPONENT_SWIZZLE_IDENTITY,
            VK_COMPONENT_SWIZZLE_IDENTITY,
            VK_COMPONENT_SWIZZLE_IDENTITY,
        };
        view.subresourceRange.aspectMask =
            VK_IMAGE_ASPECT_COLOR_BIT;
        view.subresourceRange.baseMipLevel = 0;
        view.subresourceRange.levelCount = 1;
        view.subresourceRange.baseArrayLayer = 0;
        view.subresourceRange.layerCount = 1;

        if (!ok(
                vkCreateImageView(
                    device_,
                    &view,
                    nullptr,
                    &imageViews_[i]))) {
            logError("vkCreateImageView failed");
            return false;
        }
    }

    return true;
}

bool VulkanClearRenderer::createDepthResources() noexcept {
    const std::size_t count =
        swapchainImages_.size();

    depthImages_.assign(
        count,
        VK_NULL_HANDLE);
    depthMemory_.assign(
        count,
        VK_NULL_HANDLE);
    depthViews_.assign(
        count,
        VK_NULL_HANDLE);

    for (std::size_t i = 0;
         i < count;
         ++i) {
        VkImageCreateInfo imageInfo{
            VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO
        };
        imageInfo.imageType =
            VK_IMAGE_TYPE_2D;
        imageInfo.format =
            depthFormat_;
        imageInfo.extent = {
            swapchainExtent_.width,
            swapchainExtent_.height,
            1,
        };
        imageInfo.mipLevels = 1;
        imageInfo.arrayLayers = 1;
        imageInfo.samples =
            VK_SAMPLE_COUNT_1_BIT;
        imageInfo.tiling =
            VK_IMAGE_TILING_OPTIMAL;
        imageInfo.usage =
            VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT;
        imageInfo.sharingMode =
            VK_SHARING_MODE_EXCLUSIVE;
        imageInfo.initialLayout =
            VK_IMAGE_LAYOUT_UNDEFINED;

        if (!ok(
                vkCreateImage(
                    device_,
                    &imageInfo,
                    nullptr,
                    &depthImages_[i]))) {
            logError("vkCreateImage depth failed");
            return false;
        }

        VkMemoryRequirements requirements{};

        vkGetImageMemoryRequirements(
            device_,
            depthImages_[i],
            &requirements);

        std::uint32_t memoryType = 0;

        if (!findMemoryType(
                requirements.memoryTypeBits,
                VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
                memoryType)) {
            logError("No device-local memory for depth image");
            return false;
        }

        VkMemoryAllocateInfo allocation{
            VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO
        };
        allocation.allocationSize =
            requirements.size;
        allocation.memoryTypeIndex =
            memoryType;

        if (!ok(
                vkAllocateMemory(
                    device_,
                    &allocation,
                    nullptr,
                    &depthMemory_[i]))) {
            logError("vkAllocateMemory depth failed");
            return false;
        }

        if (!ok(
                vkBindImageMemory(
                    device_,
                    depthImages_[i],
                    depthMemory_[i],
                    0))) {
            logError("vkBindImageMemory depth failed");
            return false;
        }

        VkImageViewCreateInfo view{
            VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO
        };
        view.image =
            depthImages_[i];
        view.viewType =
            VK_IMAGE_VIEW_TYPE_2D;
        view.format =
            depthFormat_;
        view.subresourceRange.aspectMask =
            VK_IMAGE_ASPECT_DEPTH_BIT;
        view.subresourceRange.baseMipLevel = 0;
        view.subresourceRange.levelCount = 1;
        view.subresourceRange.baseArrayLayer = 0;
        view.subresourceRange.layerCount = 1;

        if (!ok(
                vkCreateImageView(
                    device_,
                    &view,
                    nullptr,
                    &depthViews_[i]))) {
            logError("vkCreateImageView depth failed");
            return false;
        }
    }

    return true;
}

bool VulkanClearRenderer::createReflectionFallbackResources() noexcept {
    if (device_ == VK_NULL_HANDLE || commandPool_ == VK_NULL_HANDLE ||
        reflectionDescriptorSetLayout_ == VK_NULL_HANDLE) {
        return false;
    }

    if (reflectionFallbackView_ != VK_NULL_HANDLE &&
        reflectionDescriptorSet_ != VK_NULL_HANDLE) {
        updateReflectionDescriptor(reflectionFallbackView_);
        reflectionHasValidContents_ = true;
        return true;
    }

    VkImageCreateInfo imageInfo{VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO};
    imageInfo.imageType = VK_IMAGE_TYPE_2D;
    imageInfo.format = VK_FORMAT_R8G8B8A8_UNORM;
    imageInfo.extent = {1, 1, 1};
    imageInfo.mipLevels = 1;
    imageInfo.arrayLayers = 1;
    imageInfo.samples = VK_SAMPLE_COUNT_1_BIT;
    imageInfo.tiling = VK_IMAGE_TILING_OPTIMAL;
    imageInfo.usage = VK_IMAGE_USAGE_TRANSFER_DST_BIT | VK_IMAGE_USAGE_SAMPLED_BIT;
    imageInfo.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
    imageInfo.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    if (!ok(vkCreateImage(device_, &imageInfo, nullptr, &reflectionFallbackImage_))) return false;

    VkMemoryRequirements requirements{};
    vkGetImageMemoryRequirements(device_, reflectionFallbackImage_, &requirements);
    std::uint32_t memoryType = 0;
    if (!findMemoryType(requirements.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT, memoryType)) return false;
    VkMemoryAllocateInfo allocation{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    allocation.allocationSize = requirements.size;
    allocation.memoryTypeIndex = memoryType;
    if (!ok(vkAllocateMemory(device_, &allocation, nullptr, &reflectionFallbackMemory_)) ||
        !ok(vkBindImageMemory(device_, reflectionFallbackImage_, reflectionFallbackMemory_, 0))) return false;

    VkImageViewCreateInfo viewInfo{VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO};
    viewInfo.image = reflectionFallbackImage_;
    viewInfo.viewType = VK_IMAGE_VIEW_TYPE_2D;
    viewInfo.format = VK_FORMAT_R8G8B8A8_UNORM;
    viewInfo.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    viewInfo.subresourceRange.levelCount = 1;
    viewInfo.subresourceRange.layerCount = 1;
    if (!ok(vkCreateImageView(device_, &viewInfo, nullptr, &reflectionFallbackView_))) return false;

    VkSamplerCreateInfo samplerInfo{VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO};
    samplerInfo.magFilter = VK_FILTER_LINEAR;
    samplerInfo.minFilter = VK_FILTER_LINEAR;
    samplerInfo.mipmapMode = VK_SAMPLER_MIPMAP_MODE_NEAREST;
    samplerInfo.addressModeU = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    samplerInfo.addressModeV = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    samplerInfo.addressModeW = VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    samplerInfo.maxAnisotropy = 1.0f;
    if (!ok(vkCreateSampler(device_, &samplerInfo, nullptr, &reflectionSampler_))) return false;

    VkDescriptorPoolSize poolSize{};
    poolSize.type = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    poolSize.descriptorCount = 1;
    VkDescriptorPoolCreateInfo poolInfo{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
    poolInfo.maxSets = 1;
    poolInfo.poolSizeCount = 1;
    poolInfo.pPoolSizes = &poolSize;
    if (!ok(vkCreateDescriptorPool(device_, &poolInfo, nullptr, &reflectionDescriptorPool_))) return false;

    VkDescriptorSetAllocateInfo setInfo{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
    setInfo.descriptorPool = reflectionDescriptorPool_;
    setInfo.descriptorSetCount = 1;
    setInfo.pSetLayouts = &reflectionDescriptorSetLayout_;
    if (!ok(vkAllocateDescriptorSets(device_, &setInfo, &reflectionDescriptorSet_))) return false;

    VkCommandBufferAllocateInfo commandInfo{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
    commandInfo.commandPool = commandPool_;
    commandInfo.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    commandInfo.commandBufferCount = 1;
    VkCommandBuffer command = VK_NULL_HANDLE;
    if (!ok(vkAllocateCommandBuffers(device_, &commandInfo, &command))) return false;
    VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
    begin.flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if (!ok(vkBeginCommandBuffer(command, &begin))) return false;

    VkImageMemoryBarrier toTransfer{VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER};
    toTransfer.oldLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    toTransfer.newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    toTransfer.srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    toTransfer.dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED;
    toTransfer.image = reflectionFallbackImage_;
    toTransfer.subresourceRange.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT;
    toTransfer.subresourceRange.levelCount = 1;
    toTransfer.subresourceRange.layerCount = 1;
    toTransfer.dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, nullptr, 0, nullptr, 1, &toTransfer);

    VkClearColorValue clear{};
    clear.float32[0] = 0.008f; clear.float32[1] = 0.010f; clear.float32[2] = 0.016f; clear.float32[3] = 1.0f;
    VkImageSubresourceRange range{};
    range.aspectMask = VK_IMAGE_ASPECT_COLOR_BIT; range.levelCount = 1; range.layerCount = 1;
    vkCmdClearColorImage(command, reflectionFallbackImage_, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, &clear, 1, &range);

    VkImageMemoryBarrier toSample = toTransfer;
    toSample.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    toSample.newLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    toSample.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
    toSample.dstAccessMask = VK_ACCESS_SHADER_READ_BIT;
    vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT, 0, 0, nullptr, 0, nullptr, 1, &toSample);
    if (!ok(vkEndCommandBuffer(command))) return false;
    VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};
    submit.commandBufferCount = 1; submit.pCommandBuffers = &command;
    if (!ok(vkQueueSubmit(graphicsQueue_, 1, &submit, VK_NULL_HANDLE)) || !ok(vkQueueWaitIdle(graphicsQueue_))) return false;
    vkFreeCommandBuffers(device_, commandPool_, 1, &command);

    updateReflectionDescriptor(reflectionFallbackView_);
    reflectionHasValidContents_ = true;
    return true;
}

void VulkanClearRenderer::updateReflectionDescriptor(VkImageView view) noexcept {
    if (device_ == VK_NULL_HANDLE || reflectionDescriptorSet_ == VK_NULL_HANDLE ||
        reflectionSampler_ == VK_NULL_HANDLE || view == VK_NULL_HANDLE) return;
    VkDescriptorImageInfo imageInfo{};
    imageInfo.sampler = reflectionSampler_;
    imageInfo.imageView = view;
    imageInfo.imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    VkWriteDescriptorSet write{VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET};
    write.dstSet = reflectionDescriptorSet_;
    write.dstBinding = 0;
    write.descriptorCount = 1;
    write.descriptorType = VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    write.pImageInfo = &imageInfo;
    vkUpdateDescriptorSets(device_, 1, &write, 0, nullptr);
}

void VulkanClearRenderer::destroyReflectionFallbackResources() noexcept {
    if (device_ == VK_NULL_HANDLE) return;
    if (reflectionFallbackView_ != VK_NULL_HANDLE) vkDestroyImageView(device_, reflectionFallbackView_, nullptr);
    if (reflectionFallbackImage_ != VK_NULL_HANDLE) vkDestroyImage(device_, reflectionFallbackImage_, nullptr);
    if (reflectionFallbackMemory_ != VK_NULL_HANDLE) vkFreeMemory(device_, reflectionFallbackMemory_, nullptr);
    reflectionFallbackView_ = VK_NULL_HANDLE;
    reflectionFallbackImage_ = VK_NULL_HANDLE;
    reflectionFallbackMemory_ = VK_NULL_HANDLE;
}

bool VulkanClearRenderer::createReflectionTarget(
    float resolutionScale) noexcept {
    destroyReflectionTarget();

    if (device_ == VK_NULL_HANDLE ||
        swapchainExtent_.width == 0 ||
        swapchainExtent_.height == 0 ||
        !std::isfinite(resolutionScale) ||
        resolutionScale <= 0.0f) {
        return true;
    }

    const float requestedScale =
        std::clamp(
            resolutionScale,
            0.10f,
            1.0f);

    // Match ReflectionTargetPlanner exactly: one uniform cap preserves the
    // source aspect ratio on wide/high-resolution phones instead of clamping
    // each axis independently and stretching the reflected scene.
    constexpr float kMaxReflectionDimension = 1536.0f;
    const float dimensionCapScale =
        std::min(
            kMaxReflectionDimension /
                static_cast<float>(swapchainExtent_.width),
            kMaxReflectionDimension /
                static_cast<float>(swapchainExtent_.height));
    const float scale =
        std::min(
            requestedScale,
            dimensionCapScale);

    const auto scaledDimension =
        [scale](std::uint32_t value) noexcept {
            const auto scaled =
                static_cast<std::uint32_t>(
                    std::max(
                        16.0f,
                        std::floor(
                            static_cast<float>(value) *
                            scale)));
            return std::max(
                16U,
                scaled & ~15U);
        };

    reflectionExtent_.width =
        scaledDimension(swapchainExtent_.width);
    reflectionExtent_.height =
        scaledDimension(swapchainExtent_.height);
    // Keep the requested workload scale as the cache key. The effective
    // allocation scale may be smaller solely because of the hard GPU cap.
    reflectionTargetScale_ = requestedScale;

    const auto createAttachment =
        [&](VkFormat format,
            VkImageUsageFlags usage,
            VkImageAspectFlags aspect,
            VkImage& image,
            VkDeviceMemory& memory,
            VkImageView& view) noexcept {
            VkImageCreateInfo imageInfo{
                VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO
            };
            imageInfo.imageType = VK_IMAGE_TYPE_2D;
            imageInfo.format = format;
            imageInfo.extent = {
                reflectionExtent_.width,
                reflectionExtent_.height,
                1,
            };
            imageInfo.mipLevels = 1;
            imageInfo.arrayLayers = 1;
            imageInfo.samples = VK_SAMPLE_COUNT_1_BIT;
            imageInfo.tiling = VK_IMAGE_TILING_OPTIMAL;
            imageInfo.usage = usage;
            imageInfo.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
            imageInfo.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;

            if (!ok(
                    vkCreateImage(
                        device_,
                        &imageInfo,
                        nullptr,
                        &image))) {
                return false;
            }

            VkMemoryRequirements requirements{};
            vkGetImageMemoryRequirements(
                device_,
                image,
                &requirements);

            std::uint32_t memoryType = 0;
            if (!findMemoryType(
                    requirements.memoryTypeBits,
                    VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
                    memoryType)) {
                return false;
            }

            VkMemoryAllocateInfo allocation{
                VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO
            };
            allocation.allocationSize = requirements.size;
            allocation.memoryTypeIndex = memoryType;

            if (!ok(
                    vkAllocateMemory(
                        device_,
                        &allocation,
                        nullptr,
                        &memory)) ||
                !ok(
                    vkBindImageMemory(
                        device_,
                        image,
                        memory,
                        0))) {
                return false;
            }

            VkImageViewCreateInfo viewInfo{
                VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO
            };
            viewInfo.image = image;
            viewInfo.viewType = VK_IMAGE_VIEW_TYPE_2D;
            viewInfo.format = format;
            viewInfo.subresourceRange.aspectMask = aspect;
            viewInfo.subresourceRange.baseMipLevel = 0;
            viewInfo.subresourceRange.levelCount = 1;
            viewInfo.subresourceRange.baseArrayLayer = 0;
            viewInfo.subresourceRange.layerCount = 1;

            return ok(
                vkCreateImageView(
                    device_,
                    &viewInfo,
                    nullptr,
                    &view));
        };

    VkFormatProperties reflectionFormatProperties{};
    vkGetPhysicalDeviceFormatProperties(
        physicalDevice_,
        swapchainFormat_,
        &reflectionFormatProperties);

    const VkFormatFeatureFlags requiredColorFeatures =
        VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT |
        VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT;

    if ((reflectionFormatProperties.optimalTilingFeatures &
         requiredColorFeatures) != requiredColorFeatures) {
        logInfo(
            "Planar reflection format unsupported for sampled color; "
            "falling back");
        destroyReflectionTarget();
        return true;
    }

    const bool colorReady =
        createAttachment(
            swapchainFormat_,
            VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT |
                VK_IMAGE_USAGE_SAMPLED_BIT,
            VK_IMAGE_ASPECT_COLOR_BIT,
            reflectionColorImage_,
            reflectionColorMemory_,
            reflectionColorView_);

    const bool depthReady =
        colorReady &&
        createAttachment(
            depthFormat_,
            VK_IMAGE_USAGE_DEPTH_STENCIL_ATTACHMENT_BIT,
            VK_IMAGE_ASPECT_DEPTH_BIT,
            reflectionDepthImage_,
            reflectionDepthMemory_,
            reflectionDepthView_);

    if (!colorReady || !depthReady) {
        logError("Planar reflection target allocation failed; falling back");
        destroyReflectionTarget();
        return true;
    }

    if (!createReflectionPassResources()) {
        logError("Planar reflection pass setup failed; falling back");
        destroyReflectionTarget();
        return true;
    }

    if (reflectionDescriptorSet_ == VK_NULL_HANDLE) {
        logError("Reflection descriptor fallback is unavailable");
        destroyReflectionTarget();
        return true;
    }

    // A newly allocated target starts UNDEFINED. Keep it unavailable until
    // its first capture pass performs the transition to shader-read layout.
    // The persistent descriptor allocation itself survives target churn.
    reflectionHasValidContents_ = false;

    // The capture pass runs before the main pass in the same command buffer,
    // so the live target reaches shader-read layout before it is sampled.
    updateReflectionDescriptor(reflectionColorView_);
    return true;
}

bool VulkanClearRenderer::createReflectionPassResources() noexcept {
    if (reflectionColorView_ == VK_NULL_HANDLE ||
        reflectionDepthView_ == VK_NULL_HANDLE ||
        reflectionExtent_.width == 0 ||
        reflectionExtent_.height == 0) {
        return false;
    }

    VkAttachmentDescription color{};
    color.format = swapchainFormat_;
    color.samples = VK_SAMPLE_COUNT_1_BIT;
    color.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    color.storeOp = VK_ATTACHMENT_STORE_OP_STORE;
    color.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    color.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    color.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    color.finalLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;

    VkAttachmentDescription depth{};
    depth.format = depthFormat_;
    depth.samples = VK_SAMPLE_COUNT_1_BIT;
    depth.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR;
    depth.storeOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    depth.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    depth.stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE;
    depth.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED;
    depth.finalLayout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;

    const std::array<VkAttachmentDescription, 2> attachments{
        color,
        depth,
    };

    VkAttachmentReference colorReference{};
    colorReference.attachment = 0;
    colorReference.layout = VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;

    VkAttachmentReference depthReference{};
    depthReference.attachment = 1;
    depthReference.layout = VK_IMAGE_LAYOUT_DEPTH_STENCIL_ATTACHMENT_OPTIMAL;

    VkSubpassDescription subpass{};
    subpass.pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS;
    subpass.colorAttachmentCount = 1;
    subpass.pColorAttachments = &colorReference;
    subpass.pDepthStencilAttachment = &depthReference;

    std::array<VkSubpassDependency, 2> dependencies{};

    dependencies[0].srcSubpass = VK_SUBPASS_EXTERNAL;
    dependencies[0].dstSubpass = 0;
    dependencies[0].srcStageMask =
        VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT;
    dependencies[0].dstStageMask =
        VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT |
        VK_PIPELINE_STAGE_EARLY_FRAGMENT_TESTS_BIT;
    dependencies[0].srcAccessMask =
        VK_ACCESS_SHADER_READ_BIT;
    dependencies[0].dstAccessMask =
        VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT |
        VK_ACCESS_DEPTH_STENCIL_ATTACHMENT_WRITE_BIT;

    dependencies[1].srcSubpass = 0;
    dependencies[1].dstSubpass = VK_SUBPASS_EXTERNAL;
    dependencies[1].srcStageMask =
        VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dependencies[1].dstStageMask =
        VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT;
    dependencies[1].srcAccessMask =
        VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    dependencies[1].dstAccessMask =
        VK_ACCESS_SHADER_READ_BIT;

    VkRenderPassCreateInfo renderPassInfo{
        VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO
    };
    renderPassInfo.attachmentCount =
        static_cast<std::uint32_t>(attachments.size());
    renderPassInfo.pAttachments = attachments.data();
    renderPassInfo.subpassCount = 1;
    renderPassInfo.pSubpasses = &subpass;
    renderPassInfo.dependencyCount =
        static_cast<std::uint32_t>(dependencies.size());
    renderPassInfo.pDependencies = dependencies.data();

    if (!ok(
            vkCreateRenderPass(
                device_,
                &renderPassInfo,
                nullptr,
                &reflectionRenderPass_))) {
        return false;
    }

    const std::array<VkImageView, 2> views{
        reflectionColorView_,
        reflectionDepthView_,
    };

    VkFramebufferCreateInfo framebufferInfo{
        VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO
    };
    framebufferInfo.renderPass = reflectionRenderPass_;
    framebufferInfo.attachmentCount =
        static_cast<std::uint32_t>(views.size());
    framebufferInfo.pAttachments = views.data();
    framebufferInfo.width = reflectionExtent_.width;
    framebufferInfo.height = reflectionExtent_.height;
    framebufferInfo.layers = 1;

    if (!ok(
            vkCreateFramebuffer(
                device_,
                &framebufferInfo,
                nullptr,
                &reflectionFramebuffer_))) {
        destroyReflectionPassResources();
        return false;
    }

    VkShaderModule vertex = VK_NULL_HANDLE;
    VkShaderModule fragment = VK_NULL_HANDLE;

    if (!createShaderModuleFromAsset(
            "shaders/xziel_first.vert.spv",
            vertex) ||
        !createShaderModuleFromAsset(
            "shaders/xziel_reflection_capture.frag.spv",
            fragment)) {
        if (vertex != VK_NULL_HANDLE) {
            vkDestroyShaderModule(device_, vertex, nullptr);
        }
        if (fragment != VK_NULL_HANDLE) {
            vkDestroyShaderModule(device_, fragment, nullptr);
        }
        destroyReflectionPassResources();
        return false;
    }

    const std::array<VkPipelineShaderStageCreateInfo, 2> stages{{
        {
            VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
            nullptr,
            0,
            VK_SHADER_STAGE_VERTEX_BIT,
            vertex,
            "main",
            nullptr,
        },
        {
            VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
            nullptr,
            0,
            VK_SHADER_STAGE_FRAGMENT_BIT,
            fragment,
            "main",
            nullptr,
        },
    }};

    VkPipelineVertexInputStateCreateInfo vertexInput{
        VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO
    };
    VkPipelineInputAssemblyStateCreateInfo inputAssembly{
        VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO
    };
    inputAssembly.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

    VkViewport viewport{};
    viewport.width = static_cast<float>(reflectionExtent_.width);
    viewport.height = static_cast<float>(reflectionExtent_.height);
    viewport.minDepth = 0.0f;
    viewport.maxDepth = 1.0f;

    VkRect2D scissor{};
    scissor.extent = reflectionExtent_;

    VkPipelineViewportStateCreateInfo viewportState{
        VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO
    };
    viewportState.viewportCount = 1;
    viewportState.pViewports = &viewport;
    viewportState.scissorCount = 1;
    viewportState.pScissors = &scissor;

    VkPipelineRasterizationStateCreateInfo raster{
        VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO
    };
    raster.polygonMode = VK_POLYGON_MODE_FILL;
    raster.cullMode = VK_CULL_MODE_NONE;
    raster.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE;
    raster.lineWidth = 1.0f;

    VkPipelineMultisampleStateCreateInfo multisample{
        VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO
    };
    multisample.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT;

    VkPipelineDepthStencilStateCreateInfo depthStencil{
        VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO
    };
    depthStencil.depthTestEnable = VK_TRUE;
    depthStencil.depthWriteEnable = VK_TRUE;
    depthStencil.depthCompareOp = VK_COMPARE_OP_LESS_OR_EQUAL;

    VkPipelineColorBlendAttachmentState blendAttachment{};
    blendAttachment.colorWriteMask =
        VK_COLOR_COMPONENT_R_BIT |
        VK_COLOR_COMPONENT_G_BIT |
        VK_COLOR_COMPONENT_B_BIT |
        VK_COLOR_COMPONENT_A_BIT;

    VkPipelineColorBlendStateCreateInfo blend{
        VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO
    };
    blend.attachmentCount = 1;
    blend.pAttachments = &blendAttachment;

    VkGraphicsPipelineCreateInfo pipelineInfo{
        VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO
    };
    pipelineInfo.stageCount =
        static_cast<std::uint32_t>(stages.size());
    pipelineInfo.pStages = stages.data();
    pipelineInfo.pVertexInputState = &vertexInput;
    pipelineInfo.pInputAssemblyState = &inputAssembly;
    pipelineInfo.pViewportState = &viewportState;
    pipelineInfo.pRasterizationState = &raster;
    pipelineInfo.pMultisampleState = &multisample;
    pipelineInfo.pDepthStencilState = &depthStencil;
    pipelineInfo.pColorBlendState = &blend;
    pipelineInfo.layout = pipelineLayout_;
    pipelineInfo.renderPass = reflectionRenderPass_;
    pipelineInfo.subpass = 0;

    const VkResult pipelineResult =
        vkCreateGraphicsPipelines(
            device_,
            VK_NULL_HANDLE,
            1,
            &pipelineInfo,
            nullptr,
            &reflectionPipeline_);

    vkDestroyShaderModule(device_, fragment, nullptr);
    vkDestroyShaderModule(device_, vertex, nullptr);

    if (!ok(pipelineResult)) {
        destroyReflectionPassResources();
        return false;
    }

    return true;
}

void VulkanClearRenderer::destroyReflectionPassResources() noexcept {
    if (device_ != VK_NULL_HANDLE) {
        if (reflectionPipeline_ != VK_NULL_HANDLE) {
            vkDestroyPipeline(
                device_,
                reflectionPipeline_,
                nullptr);
        }
        if (reflectionFramebuffer_ != VK_NULL_HANDLE) {
            vkDestroyFramebuffer(
                device_,
                reflectionFramebuffer_,
                nullptr);
        }
        if (reflectionRenderPass_ != VK_NULL_HANDLE) {
            vkDestroyRenderPass(
                device_,
                reflectionRenderPass_,
                nullptr);
        }
    }

    reflectionPipeline_ = VK_NULL_HANDLE;
    reflectionFramebuffer_ = VK_NULL_HANDLE;
    reflectionRenderPass_ = VK_NULL_HANDLE;
}

void VulkanClearRenderer::destroyReflectionTarget() noexcept {
    // Pass/framebuffer resources follow the transient target. Descriptor
    // allocation and sampler lifetime are deliberately independent so the
    // main pipeline can keep one stable descriptor slot across target churn.
    // The descriptor must be considered unusable before its image view is
    // destroyed; a later fallback/live target update is the only path that
    // makes it sampleable again.
    reflectionHasValidContents_ = false;
    if (reflectionFallbackView_ != VK_NULL_HANDLE) {
        updateReflectionDescriptor(reflectionFallbackView_);
        reflectionHasValidContents_ = true;
    }
    destroyReflectionPassResources();

    if (device_ != VK_NULL_HANDLE) {
        if (reflectionDepthView_ != VK_NULL_HANDLE) {
            vkDestroyImageView(
                device_,
                reflectionDepthView_,
                nullptr);
        }
        if (reflectionDepthImage_ != VK_NULL_HANDLE) {
            vkDestroyImage(
                device_,
                reflectionDepthImage_,
                nullptr);
        }
        if (reflectionDepthMemory_ != VK_NULL_HANDLE) {
            vkFreeMemory(
                device_,
                reflectionDepthMemory_,
                nullptr);
        }
        if (reflectionColorView_ != VK_NULL_HANDLE) {
            vkDestroyImageView(
                device_,
                reflectionColorView_,
                nullptr);
        }
        if (reflectionColorImage_ != VK_NULL_HANDLE) {
            vkDestroyImage(
                device_,
                reflectionColorImage_,
                nullptr);
        }
        if (reflectionColorMemory_ != VK_NULL_HANDLE) {
            vkFreeMemory(
                device_,
                reflectionColorMemory_,
                nullptr);
        }
    }

    reflectionColorImage_ = VK_NULL_HANDLE;
    reflectionColorMemory_ = VK_NULL_HANDLE;
    reflectionColorView_ = VK_NULL_HANDLE;
    reflectionDepthImage_ = VK_NULL_HANDLE;
    reflectionDepthMemory_ = VK_NULL_HANDLE;
    reflectionDepthView_ = VK_NULL_HANDLE;
    reflectionExtent_ = {};
    reflectionTargetScale_ = 0.0f;
    reflectionHasValidContents_ = false;
    reflectionInvisibleFrames_ = 0;
}

bool VulkanClearRenderer::createFramebuffers() noexcept {
    if (imageViews_.size() != depthViews_.size()) {
        return false;
    }

    framebuffers_.assign(
        imageViews_.size(),
        VK_NULL_HANDLE);

    for (std::size_t i = 0;
         i < framebuffers_.size();
         ++i) {
        const std::array<VkImageView, 2>
            attachments{
                imageViews_[i],
                depthViews_[i],
            };

        VkFramebufferCreateInfo framebuffer{
            VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO
        };
        framebuffer.renderPass =
            renderPass_;
        framebuffer.attachmentCount =
            static_cast<std::uint32_t>(
                attachments.size());
        framebuffer.pAttachments =
            attachments.data();
        framebuffer.width =
            swapchainExtent_.width;
        framebuffer.height =
            swapchainExtent_.height;
        framebuffer.layers = 1;

        if (!ok(
                vkCreateFramebuffer(
                    device_,
                    &framebuffer,
                    nullptr,
                    &framebuffers_[i]))) {
            logError("vkCreateFramebuffer failed");
            return false;
        }
    }

    return true;
}

bool VulkanClearRenderer::createCommandResources() noexcept {
    if (commandPool_ == VK_NULL_HANDLE) {
        VkCommandPoolCreateInfo pool{
            VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO
        };
        pool.flags =
            VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT;
        pool.queueFamilyIndex =
            graphicsQueueFamily_;

        if (!ok(
                vkCreateCommandPool(
                    device_,
                    &pool,
                    nullptr,
                    &commandPool_))) {
            logError("vkCreateCommandPool failed");
            return false;
        }
    }

    commandBuffers_.assign(
        swapchainImages_.size(),
        VK_NULL_HANDLE);

    VkCommandBufferAllocateInfo allocation{
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO
    };
    allocation.commandPool =
        commandPool_;
    allocation.level =
        VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocation.commandBufferCount =
        static_cast<std::uint32_t>(
            commandBuffers_.size());

    if (!ok(
            vkAllocateCommandBuffers(
                device_,
                &allocation,
                commandBuffers_.data()))) {
        logError("vkAllocateCommandBuffers failed");
        return false;
    }

    return true;
}

bool VulkanClearRenderer::createSyncObjects() noexcept {
    VkSemaphoreCreateInfo semaphore{
        VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO
    };

    VkFenceCreateInfo fence{
        VK_STRUCTURE_TYPE_FENCE_CREATE_INFO
    };
    fence.flags =
        VK_FENCE_CREATE_SIGNALED_BIT;

    for (auto& frame : frames_) {
        if (!ok(
                vkCreateSemaphore(
                    device_,
                    &semaphore,
                    nullptr,
                    &frame.imageAvailable)) ||
            !ok(
                vkCreateSemaphore(
                    device_,
                    &semaphore,
                    nullptr,
                    &frame.renderFinished)) ||
            !ok(
                vkCreateFence(
                    device_,
                    &fence,
                    nullptr,
                    &frame.inFlight))) {
            logError("failed creating sync objects");
            return false;
        }
    }

    return true;
}

void VulkanClearRenderer::destroySwapchainResources() noexcept {
    if (device_ == VK_NULL_HANDLE) {
        swapchainImages_.clear();
        imageViews_.clear();
        depthImages_.clear();
        depthMemory_.clear();
        depthViews_.clear();
        framebuffers_.clear();
        commandBuffers_.clear();
        imageFences_.clear();
        return;
    }

    destroyReflectionTarget();

    if (commandPool_ != VK_NULL_HANDLE &&
        !commandBuffers_.empty()) {
        vkFreeCommandBuffers(
            device_,
            commandPool_,
            static_cast<std::uint32_t>(
                commandBuffers_.size()),
            commandBuffers_.data());
    }

    commandBuffers_.clear();

    for (const auto framebuffer : framebuffers_) {
        if (framebuffer != VK_NULL_HANDLE) {
            vkDestroyFramebuffer(
                device_,
                framebuffer,
                nullptr);
        }
    }

    framebuffers_.clear();

    for (const auto view : depthViews_) {
        if (view != VK_NULL_HANDLE) {
            vkDestroyImageView(
                device_,
                view,
                nullptr);
        }
    }

    depthViews_.clear();

    for (const auto image : depthImages_) {
        if (image != VK_NULL_HANDLE) {
            vkDestroyImage(
                device_,
                image,
                nullptr);
        }
    }

    depthImages_.clear();

    for (const auto memory : depthMemory_) {
        if (memory != VK_NULL_HANDLE) {
            vkFreeMemory(
                device_,
                memory,
                nullptr);
        }
    }

    depthMemory_.clear();

    for (const auto view : imageViews_) {
        if (view != VK_NULL_HANDLE) {
            vkDestroyImageView(
                device_,
                view,
                nullptr);
        }
    }

    imageViews_.clear();

    if (uiPipeline_ != VK_NULL_HANDLE) {
        vkDestroyPipeline(
            device_,
            uiPipeline_,
            nullptr);
        uiPipeline_ =
            VK_NULL_HANDLE;
    }

    if (uiPipelineLayout_ != VK_NULL_HANDLE) {
        vkDestroyPipelineLayout(
            device_,
            uiPipelineLayout_,
            nullptr);
        uiPipelineLayout_ =
            VK_NULL_HANDLE;
    }

    if (graphicsPipeline_ != VK_NULL_HANDLE) {
        vkDestroyPipeline(
            device_,
            graphicsPipeline_,
            nullptr);
        graphicsPipeline_ =
            VK_NULL_HANDLE;
    }

    if (pipelineLayout_ != VK_NULL_HANDLE) {
        vkDestroyPipelineLayout(
            device_,
            pipelineLayout_,
            nullptr);
        pipelineLayout_ =
            VK_NULL_HANDLE;
    }

    destroyReflectionFallbackResources();

    if (reflectionDescriptorPool_ != VK_NULL_HANDLE) {
        vkDestroyDescriptorPool(device_, reflectionDescriptorPool_, nullptr);
        reflectionDescriptorPool_ = VK_NULL_HANDLE;
        reflectionDescriptorSet_ = VK_NULL_HANDLE;
    }
    if (reflectionSampler_ != VK_NULL_HANDLE) {
        vkDestroySampler(device_, reflectionSampler_, nullptr);
        reflectionSampler_ = VK_NULL_HANDLE;
    }

    if (reflectionDescriptorSetLayout_ != VK_NULL_HANDLE) {
        vkDestroyDescriptorSetLayout(
            device_,
            reflectionDescriptorSetLayout_,
            nullptr);
        reflectionDescriptorSetLayout_ =
            VK_NULL_HANDLE;
    }

    if (renderPass_ != VK_NULL_HANDLE) {
        vkDestroyRenderPass(
            device_,
            renderPass_,
            nullptr);
        renderPass_ =
            VK_NULL_HANDLE;
    }

    if (swapchain_ != VK_NULL_HANDLE) {
        if (swappyInitialized_) {
            SwappyVk_destroySwapchain(
                device_,
                swapchain_);
            swappyInitialized_ = false;
            refreshDurationNs_ = 0;
        }

        vkDestroySwapchainKHR(
            device_,
            swapchain_,
            nullptr);
        swapchain_ =
            VK_NULL_HANDLE;
    }

    swapchainImages_.clear();
    imageFences_.clear();
}

bool VulkanClearRenderer::recreateSwapchain() noexcept {
    if (device_ == VK_NULL_HANDLE ||
        window_ == nullptr) {
        return false;
    }

    if (ANativeWindow_getWidth(window_) <= 0 ||
        ANativeWindow_getHeight(window_) <= 0) {
        return true;
    }

    if (!ok(
            vkDeviceWaitIdle(
                device_))) {
        return false;
    }

    destroySwapchainResources();

    const bool success =
        createSwapchain() &&
        createRenderPass() &&
        createGraphicsPipeline() &&
        createUiPipeline() &&
        createImageViews() &&
        createDepthResources() &&
        createCommandResources() &&
        createReflectionFallbackResources() &&
        createFramebuffers();

    if (!success) {
        logError("Swapchain recreation failed");
    }

    return success;
}

bool VulkanClearRenderer::recordDrawCommand(
    std::uint32_t imageIndex,
    float timeSeconds,
    const VulkanCamera& camera,
    const VulkanHudState& hud,
    const VulkanSceneState& scene,
    const VulkanEnvironmentState& environment) noexcept {
    if (imageIndex >= commandBuffers_.size() ||
        imageIndex >= framebuffers_.size()) {
        return false;
    }

    const VkCommandBuffer command =
        commandBuffers_[imageIndex];

    if (!ok(
            vkResetCommandBuffer(
                command,
                0))) {
        logError("vkResetCommandBuffer failed");
        return false;
    }

    VkCommandBufferBeginInfo begin{
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO
    };
    begin.flags =
        VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;

    if (!ok(
            vkBeginCommandBuffer(
                command,
                &begin))) {
        logError("vkBeginCommandBuffer failed");
        return false;
    }

    const float pulse =
        0.5f +
        0.5f * std::sin(
            timeSeconds * 1.45f);

    std::array<VkClearValue, 2> clears{};

    const float lightning =
        std::clamp(
            environment.lightningFlash,
            0.0f,
            1.0f);

    clears[0].color.float32[0] =
        0.006f +
        pulse * 0.006f +
        lightning * 0.18f;

    clears[0].color.float32[1] =
        0.004f +
        lightning * 0.22f;

    clears[0].color.float32[2] =
        0.010f +
        pulse * 0.010f +
        lightning * 0.30f;
    clears[0].color.float32[3] =
        1.0f;

    clears[1].depthStencil.depth =
        1.0f;
    clears[1].depthStencil.stencil =
        0;

    VkRenderPassBeginInfo render{
        VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO
    };
    render.renderPass =
        renderPass_;
    render.framebuffer =
        framebuffers_[imageIndex];
    render.renderArea.offset =
        {0, 0};
    render.renderArea.extent =
        swapchainExtent_;
    render.clearValueCount =
        static_cast<std::uint32_t>(
            clears.size());
    render.pClearValues =
        clears.data();

    const float reflectionCoverage =
        std::clamp(
            environment.planarReflectionScreenCoverage,
            0.0f,
            1.0f);

    // Refresh the offscreen planar scene before the main pass. The first
    // implementation intentionally renders a compact subset of the room with
    // a reflected camera; the target is already transitioned to shader-read
    // layout by the reflection render pass for the material sampling stage.
    // Tiny reflective surfaces can retain the previous target longer. This
    // is deliberately quantized to avoid unstable frame-to-frame scheduling.
    const std::uint32_t coverageIntervalMultiplier =
        reflectionCoverage < 0.025f
        ? 4U
        : (reflectionCoverage < 0.08f ? 2U : 1U);
    const std::uint32_t reflectionUpdateInterval =
        std::clamp(
            environment.planarReflectionUpdateEveryNFrames *
                coverageIntervalMultiplier,
            1U,
            8U);
    const bool reflectionDue =
        !reflectionHasValidContents_ ||
        reflectionFrameCounter_ % reflectionUpdateInterval == 0;

    if (reflectionRenderPass_ != VK_NULL_HANDLE &&
        reflectionFramebuffer_ != VK_NULL_HANDLE &&
        reflectionPipeline_ != VK_NULL_HANDLE &&
        environment.maxPlanarReflectionPasses > 0 &&
        environment.planarReflectionVisible &&
        reflectionCoverage > 0.0025f &&
        reflectionDue) {
        std::array<VkClearValue, 2> reflectionClears{};
        reflectionClears[0].color.float32[0] =
            clears[0].color.float32[0] * 0.55f;
        reflectionClears[0].color.float32[1] =
            clears[0].color.float32[1] * 0.65f;
        reflectionClears[0].color.float32[2] =
            clears[0].color.float32[2] * 0.80f;
        reflectionClears[0].color.float32[3] = 1.0f;
        reflectionClears[1].depthStencil.depth = 1.0f;

        VkRenderPassBeginInfo reflectionBegin{
            VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO
        };
        reflectionBegin.renderPass = reflectionRenderPass_;
        reflectionBegin.framebuffer = reflectionFramebuffer_;
        reflectionBegin.renderArea.extent = reflectionExtent_;
        reflectionBegin.clearValueCount =
            static_cast<std::uint32_t>(reflectionClears.size());
        reflectionBegin.pClearValues = reflectionClears.data();

        vkCmdBeginRenderPass(
            command,
            &reflectionBegin,
            VK_SUBPASS_CONTENTS_INLINE);
        vkCmdBindPipeline(
            command,
            VK_PIPELINE_BIND_POINT_GRAPHICS,
            reflectionPipeline_);

        const float reflectedAspect =
            reflectionExtent_.height > 0
            ? static_cast<float>(reflectionExtent_.width) /
              static_cast<float>(reflectionExtent_.height)
            : 1.0f;

        const auto drawReflectedBox = [&](
            float tx,
            float ty,
            float tz,
            float sx,
            float sy,
            float sz,
            float materialId) noexcept {
            PushConstants push{};
            push.timeSeconds =
                std::isfinite(timeSeconds) ? timeSeconds : 0.0f;
            push.aspect = reflectedAspect;
            push.horrorPulse = pulse;
            push.materialId = materialId;
            push.translationX = tx;
            push.translationY = ty;
            push.translationZ = tz;
            push.scaleX = sx;
            push.scaleY = sy;
            push.scaleZ = sz;

            float planeNx = environment.planarPlaneNormalX;
            float planeNy = environment.planarPlaneNormalY;
            float planeNz = environment.planarPlaneNormalZ;
            float planeD = environment.planarPlaneDistance;
            const float planeLength = std::sqrt(
                planeNx * planeNx +
                planeNy * planeNy +
                planeNz * planeNz);
            if (!std::isfinite(planeLength) || planeLength < 0.0001f) {
                planeNx = 0.0f;
                planeNy = 1.0f;
                planeNz = 0.0f;
                planeD = 1.48f;
            } else {
                const float inversePlaneLength = 1.0f / planeLength;
                planeNx *= inversePlaneLength;
                planeNy *= inversePlaneLength;
                planeNz *= inversePlaneLength;
                planeD = std::isfinite(planeD)
                    ? planeD * inversePlaneLength
                    : 0.0f;
            }

            const float signedCameraDistance =
                planeNx * camera.x +
                planeNy * camera.y +
                planeNz * camera.z +
                planeD;
            push.cameraX = camera.x - 2.0f * signedCameraDistance * planeNx;
            push.cameraY = camera.y - 2.0f * signedCameraDistance * planeNy;
            push.cameraZ = camera.z - 2.0f * signedCameraDistance * planeNz;
            // Reflect the camera forward vector across the authored plane,
            // then recover the yaw/pitch convention used by xziel_first.vert.
            // This handles horizontal water, vertical mirrors, and oblique
            // planar surfaces instead of only flipping pitch for floors.
            const float safeYaw = std::isfinite(camera.yawRadians)
                ? camera.yawRadians : 0.0f;
            const float safePitch = std::isfinite(camera.pitchRadians)
                ? camera.pitchRadians : 0.0f;
            const float cosPitch = std::cos(safePitch);
            float forwardX = std::sin(safeYaw) * cosPitch;
            float forwardY = -std::sin(safePitch);
            float forwardZ = std::cos(safeYaw) * cosPitch;
            const float forwardDotPlane =
                forwardX * planeNx +
                forwardY * planeNy +
                forwardZ * planeNz;
            forwardX -= 2.0f * forwardDotPlane * planeNx;
            forwardY -= 2.0f * forwardDotPlane * planeNy;
            forwardZ -= 2.0f * forwardDotPlane * planeNz;
            const float horizontalForward =
                std::sqrt(forwardX * forwardX + forwardZ * forwardZ);
            push.cameraYawRadians = std::atan2(forwardX, forwardZ);
            push.cameraPitchRadians = std::atan2(-forwardY, horizontalForward);
            push.verticalFovDegrees =
                std::clamp(camera.verticalFovDegrees, 50.0f, 110.0f);
            push.fogDensity =
                std::clamp(environment.fogDensity, 0.0f, 1.0f);
            push.lightningFlash =
                std::clamp(environment.lightningFlash, 0.0f, 2.0f);
            push.wetness =
                std::clamp(environment.wetness, 0.0f, 1.0f);
            push.rainIntensity =
                std::clamp(environment.rainIntensity, 0.0f, 1.0f);
            push.waterWavePhase = environment.waterWavePhase;
            push.waterFoamStrength =
                std::clamp(environment.waterFoamStrength, 0.0f, 1.0f);
            push.waterReflectionStrength = 0.0f;
            push.waterRefractionStrength = 0.0f;
            push.waterRoughness =
                std::clamp(environment.waterRoughness, 0.02f, 0.85f);
            push.waterQualityScale =
                std::clamp(environment.postProcessScale, 0.35f, 1.0f);
            push.waterParticleScale =
                std::clamp(environment.particleDensityScale, 0.25f, 1.0f);
            push.waterFogScale =
                std::clamp(environment.fogQualityScale, 0.35f, 1.0f);

            vkCmdPushConstants(
                command,
                pipelineLayout_,
                VK_SHADER_STAGE_VERTEX_BIT,
                0,
                static_cast<std::uint32_t>(sizeof(PushConstants)),
                &push);
            vkCmdDraw(command, 36, 1, 0, 0);
        };

        // Deliberately omit the water itself to prevent recursive reflection.
        drawReflectedBox(0.0f, -1.58f, 0.0f, 4.2f, 0.12f, 5.0f, 0.0f);
        drawReflectedBox(-3.15f, 0.05f, 0.0f, 0.12f, 2.2f, 5.0f, 1.0f);
        drawReflectedBox(3.15f, 0.05f, 0.0f, 0.12f, 2.2f, 5.0f, 1.0f);
        drawReflectedBox(0.0f, 0.05f, 3.85f, 4.2f, 2.2f, 0.12f, 2.0f);

        const std::size_t reflectedZombieCount =
            std::min(scene.zombieCount, scene.zombies.size());
        for (std::size_t i = 0; i < reflectedZombieCount; ++i) {
            const auto& zombie = scene.zombies[i];
            if (!zombie.visible) {
                continue;
            }
            drawReflectedBox(
                zombie.x,
                zombie.y + 1.08f,
                zombie.z,
                0.34f,
                0.55f,
                0.22f,
                4.0f);
            drawReflectedBox(
                zombie.x,
                zombie.y + 1.73f,
                zombie.z + 0.01f,
                0.23f,
                0.24f,
                0.22f,
                5.0f);
        }

        vkCmdEndRenderPass(command);
        reflectionHasValidContents_ = true;
    }

    ++reflectionFrameCounter_;

    vkCmdBeginRenderPass(
        command,
        &render,
        VK_SUBPASS_CONTENTS_INLINE);

    if (graphicsPipeline_ == VK_NULL_HANDLE ||
        pipelineLayout_ == VK_NULL_HANDLE) {
        vkCmdEndRenderPass(command);
        logError("graphics pipeline missing");
        return false;
    }

    vkCmdBindPipeline(
        command,
        VK_PIPELINE_BIND_POINT_GRAPHICS,
        graphicsPipeline_);

    // xziel_first.frag statically declares the reflection sampler. Vulkan
    // therefore requires descriptor set 0 to be valid for every main-pipeline
    // draw, even when the current material is not water. Never submit a draw
    // with an unbound or stale descriptor after a quality downgrade, target
    // reallocation, or allocation failure.
    if (reflectionDescriptorSet_ == VK_NULL_HANDLE) {
        vkCmdEndRenderPass(command);
        logError("reflection descriptor unavailable; refusing invalid Vulkan draw");
        return false;
    }

    vkCmdBindDescriptorSets(
        command,
        VK_PIPELINE_BIND_POINT_GRAPHICS,
        pipelineLayout_,
        0,
        1,
        &reflectionDescriptorSet_,
        0,
        nullptr);

    const float safeTime =
        std::isfinite(timeSeconds)
        ? timeSeconds
        : 0.0f;

    const float aspect =
        swapchainExtent_.height > 0
        ? static_cast<float>(
              swapchainExtent_.width) /
          static_cast<float>(
              swapchainExtent_.height)
        : 1.0f;

    const auto drawBox = [&](
        float tx,
        float ty,
        float tz,
        float sx,
        float sy,
        float sz,
        float materialId) noexcept {
        PushConstants push{};
        push.timeSeconds = safeTime;
        push.aspect = aspect;
        push.horrorPulse = pulse;
        push.materialId = materialId;

        push.translationX = tx;
        push.translationY = ty;
        push.translationZ = tz;

        push.scaleX = sx;
        push.scaleY = sy;
        push.scaleZ = sz;

        push.cameraX =
            std::isfinite(camera.x)
            ? camera.x
            : 0.0f;
        push.cameraY =
            std::isfinite(camera.y)
            ? camera.y
            : 0.14f;
        push.cameraZ =
            std::isfinite(camera.z)
            ? camera.z
            : -2.55f;

        push.cameraYawRadians =
            std::isfinite(camera.yawRadians)
            ? camera.yawRadians
            : 0.0f;

        push.cameraPitchRadians =
            std::isfinite(camera.pitchRadians)
            ? camera.pitchRadians
            : 0.0f;

        push.verticalFovDegrees =
            std::clamp(
                std::isfinite(camera.verticalFovDegrees)
                    ? camera.verticalFovDegrees
                    : 72.0f,
                50.0f,
                110.0f);

        push.fogDensity =
            std::clamp(
                environment.fogDensity,
                0.0f,
                1.0f);

        push.lightningFlash =
            std::clamp(
                environment.lightningFlash,
                0.0f,
                2.0f);

        push.wetness =
            std::clamp(
                environment.wetness,
                0.0f,
                1.0f);

        push.rainIntensity =
            std::clamp(
                environment.rainIntensity,
                0.0f,
                1.0f);

        push.waterWavePhase =
            environment.waterWavePhase;

        push.waterFoamStrength =
            std::clamp(
                environment.waterFoamStrength,
                0.0f,
                1.0f);

        push.waterReflectionStrength =
            std::clamp(
                environment.waterReflectionStrength,
                0.0f,
                1.0f);

        push.waterRefractionStrength =
            std::clamp(
                environment.waterRefractionStrength,
                0.0f,
                1.0f);

        push.waterRoughness =
            std::clamp(
                environment.waterRoughness,
                0.02f,
                0.85f);

        // Reuse the final water push-constant vec4 as a compact, uniform
        // adaptive-quality budget. These values are constant for each draw,
        // so the fragment shader can cheaply scale storm surface detail
        // without allocating textures or adding a render pass.
        push.waterQualityScale =
            std::clamp(
                environment.postProcessScale,
                0.35f,
                1.0f);

        push.waterParticleScale =
            std::clamp(
                environment.particleDensityScale,
                0.25f,
                1.0f);

        push.waterFogScale =
            std::clamp(
                environment.fogQualityScale,
                0.35f,
                1.0f);

        vkCmdPushConstants(
            command,
            pipelineLayout_,
            VK_SHADER_STAGE_VERTEX_BIT,
            0,
            static_cast<std::uint32_t>(
                sizeof(PushConstants)),
            &push);

        vkCmdDraw(
            command,
            36,
            1,
            0,
            0);
    };

    // First procedural Xziel horror room. Geometry is deliberately generated
    // without a model asset so the earliest Android renderer milestone proves
    // depth, projection, repeated draws and lighting before asset streaming.
    drawBox(
        0.0f, -1.58f, 0.0f,
        4.2f, 0.12f, 5.0f,
        0.0f);

    drawBox(
        -3.15f, 0.05f, 0.0f,
        0.12f, 2.2f, 5.0f,
        1.0f);

    drawBox(
        3.15f, 0.05f, 0.0f,
        0.12f, 2.2f, 5.0f,
        1.0f);

    drawBox(
        0.0f, 0.05f, 3.85f,
        4.2f, 2.2f, 0.12f,
        2.0f);

    drawBox(
        0.0f, 2.02f, 0.0f,
        4.2f, 0.10f, 5.0f,
        2.0f);

    // First live procedural water surface. This is fixed-cost geometry with
    // storm-driven wave/foam/roughness state, ready to receive a later planar
    // reflection texture without changing gameplay code.
    drawBox(
        -1.70f,
        -1.505f,
        -0.25f,
        1.10f,
        0.025f,
        1.45f,
        13.0f);

    // Glossy reflection panel exercises the reflective-material path. True
    // offscreen planar scene reflection remains a separate render-pass step.
    drawBox(
        3.00f,
        0.15f,
        -0.65f,
        0.025f,
        1.05f,
        1.10f,
        14.0f);

    const float prototypeDoorOpen =
        std::clamp(
            scene.doorOpenAlpha,
            0.0f,
            1.0f);

    // The single authoritative purchasable door proves that contextual
    // interactions alter collision, zombie navigation and visible world state.
    drawBox(
        -2.88f,
        -0.12f,
        1.57f,
        0.12f,
        1.52f,
        0.20f,
        1.0f);

    drawBox(
        2.88f,
        -0.12f,
        1.57f,
        0.12f,
        1.52f,
        0.20f,
        1.0f);

    drawBox(
        0.0f,
        1.34f,
        1.57f,
        3.0f,
        0.10f,
        0.20f,
        1.0f);

    drawBox(
        0.0f,
        -0.18f +
            prototypeDoorOpen *
                3.05f,
        1.57f,
        2.72f,
        1.32f,
        0.10f,
        prototypeDoorOpen >
            0.01f
            ? 7.0f
            : 8.0f);

    if (scene.interactionVisible) {
        drawBox(
            scene.interactionX,
            scene.interactionY,
            scene.interactionZ,
            0.18f,
            0.30f,
            0.12f,
            scene.interactionActive
                ? 7.0f
                : 8.0f);

        drawBox(
            scene.interactionX,
            scene.interactionY + 0.30f,
            scene.interactionZ - 0.02f,
            0.09f,
            0.055f,
            0.035f,
            scene.interactionActive
                ? 7.0f
                : 8.0f);
    }

    const std::size_t visibleZombieCount =
        std::min(
            scene.zombieCount,
            scene.zombies.size());

    for (std::size_t zombieIndex = 0;
         zombieIndex < visibleZombieCount;
         ++zombieIndex) {
        const auto& zombieState =
            scene.zombies[
                zombieIndex];

        if (!zombieState.visible) {
            continue;
        }

        const float stride =
            std::sin(
                zombieState.stridePhase *
                6.28318530718f);

        const float staggerOffset =
            zombieState.staggered
            ? std::sin(
                  safeTime *
                  38.0f +
                  static_cast<float>(
                      zombieIndex)) *
                  0.045f
            : 0.0f;

        const float attackLunge =
            zombieState.attack
            ? 0.18f
            : 0.0f;

        const float zombieX =
            zombieState.x +
            staggerOffset;

        const float zombieY =
            zombieState.y;

        const float zombieZ =
            zombieState.z -
            attackLunge;

        // Cheap contact shadow proxy keeps mobile cost bounded while giving
        // the procedural horde visible grounding before shadow maps land.
        drawBox(
            zombieX,
            -1.472f,
            zombieZ,
            0.44f,
            0.010f,
            0.30f,
            7.0f);

        drawBox(
            zombieX,
            zombieY + 1.08f,
            zombieZ,
            0.34f,
            0.55f,
            0.22f,
            4.0f);

        drawBox(
            zombieX,
            zombieY + 1.73f,
            zombieZ + 0.01f,
            0.23f,
            0.24f,
            0.22f,
            5.0f);

        drawBox(
            zombieX - 0.43f,
            zombieY + 1.08f,
            zombieZ +
                stride * 0.08f -
                attackLunge * 0.45f,
            0.11f,
            0.48f,
            0.11f,
            5.0f);

        drawBox(
            zombieX + 0.43f,
            zombieY + 1.08f,
            zombieZ -
                stride * 0.08f -
                attackLunge * 0.45f,
            0.11f,
            0.48f,
            0.11f,
            5.0f);

        drawBox(
            zombieX - 0.17f,
            zombieY + 0.38f,
            zombieZ -
                stride * 0.09f,
            0.13f,
            0.43f,
            0.14f,
            4.0f);

        drawBox(
            zombieX + 0.17f,
            zombieY + 0.38f,
            zombieZ +
                stride * 0.09f,
            0.13f,
            0.43f,
            0.14f,
            4.0f);

        if (zombieState.healthRatio <
            0.70f) {
            drawBox(
                zombieX + 0.16f,
                zombieY + 1.24f,
                zombieZ - 0.23f,
                0.08f,
                0.15f,
                0.025f,
                6.0f);
        }
    }

    const float impactAlpha =
        std::clamp(
            scene.impactAlpha,
            0.0f,
            1.0f);

    if (impactAlpha > 0.001f) {
        const float impactSize =
            scene.impactCritical
            ? 0.12f
            : 0.075f;

        drawBox(
            scene.impactX,
            scene.impactY,
            scene.impactZ,
            impactSize,
            impactSize,
            impactSize,
            6.0f);

        drawBox(
            scene.impactX +
                0.08f * impactAlpha,
            scene.impactY +
                0.05f * impactAlpha,
            scene.impactZ -
                0.04f * impactAlpha,
            impactSize * 0.55f,
            impactSize * 0.55f,
            impactSize * 0.55f,
            6.0f);

        drawBox(
            scene.impactX -
                0.07f * impactAlpha,
            scene.impactY +
                0.02f * impactAlpha,
            scene.impactZ +
                0.05f * impactAlpha,
            impactSize * 0.42f,
            impactSize * 0.42f,
            impactSize * 0.42f,
            6.0f);
    }

    const float rainForSplashes =
        std::clamp(
            environment.rainIntensity *
                environment.particleDensityScale,
            0.0f,
            1.0f);

    if (rainForSplashes > 0.08f) {
        constexpr int kPrototypeSplashCount = 7;

        for (int splashIndex = 0;
             splashIndex < kPrototypeSplashCount;
             ++splashIndex) {
            const float seed =
                static_cast<float>(
                    splashIndex);

            const float cycle =
                std::fmod(
                    safeTime *
                        (1.7f +
                         rainForSplashes *
                             1.4f) +
                    seed *
                        0.173f,
                    1.0f);

            const float x =
                -2.35f +
                std::fmod(
                    seed *
                        1.381f,
                    4.70f);

            const float z =
                -2.80f +
                std::fmod(
                    seed *
                        1.917f,
                    5.70f);

            const float radius =
                0.025f +
                cycle *
                    0.12f;

            if (cycle < 0.72f) {
                drawBox(
                    x,
                    -1.455f,
                    z,
                    radius,
                    0.006f,
                    radius,
                    8.0f);
            }
        }
    }

    const float decapAlpha =
        std::clamp(
            scene.decapAlpha,
            0.0f,
            1.0f);

    if (decapAlpha > 0.001f) {
        const float progress =
            1.0f -
            decapAlpha;

        const float ballisticRise =
            std::sin(
                progress *
                3.14159265358979323846f) *
            0.92f;

        const float travel =
            progress *
            0.95f;

        const float headX =
            scene.decapOriginX +
            scene.decapDirectionX *
                travel +
            std::sin(
                progress *
                11.0f) *
                0.08f;

        const float headY =
            scene.decapOriginY +
            ballisticRise -
            progress *
                0.18f;

        const float headZ =
            scene.decapOriginZ +
            scene.decapDirectionZ *
                travel;

        drawBox(
            headX,
            headY,
            headZ,
            0.18f,
            0.18f,
            0.18f,
            5.0f);

        drawBox(
            headX,
            headY - 0.10f,
            headZ - 0.05f,
            0.10f,
            0.045f,
            0.10f,
            6.0f);
    }

    const float weaponAds =
        std::clamp(
            hud.weaponAdsAlpha,
            0.0f,
            1.0f);

    const float weaponReload =
        std::clamp(
            hud.weaponReloadAlpha,
            0.0f,
            1.0f);

    const float weaponFire =
        std::clamp(
            hud.weaponFireAlpha,
            0.0f,
            1.0f);

    const float viewmodelLowering =
        std::clamp(
            hud.viewmodelLowering,
            0.0f,
            1.0f);

    const float reloadArc =
        std::sin(
            weaponReload *
            3.14159265358979323846f);

    const float weaponX =
        0.72f *
            (1.0f - weaponAds) +
        0.05f *
            weaponAds +
        0.11f *
            viewmodelLowering;

    const float weaponY =
        -0.72f +
        0.16f *
            weaponAds -
        0.30f *
            reloadArc -
        0.46f *
            viewmodelLowering;

    const float weaponZ =
        1.22f -
        0.12f *
            weaponAds +
        0.10f *
            reloadArc +
        0.08f *
            viewmodelLowering;

    // First procedural viewmodel: receiver, barrel and sight. This deliberately
    // uses the same cube primitive as the room so the weapon path is proven
    // before importing any external mesh asset.
    drawBox(
        weaponX,
        weaponY,
        weaponZ,
        0.38f,
        0.22f,
        0.72f,
        10.0f);

    drawBox(
        weaponX + 0.02f,
        weaponY + 0.015f,
        weaponZ + 0.72f,
        0.15f,
        0.12f,
        0.78f,
        10.0f);

    drawBox(
        weaponX,
        weaponY + 0.20f,
        weaponZ - 0.02f,
        0.085f,
        0.09f,
        0.18f,
        10.0f);

    // Procedural gloved hands make slide/dive/reload motion visible in
    // first-person before a final skinned viewmodel is imported.
    drawBox(
        weaponX + 0.22f,
        weaponY - 0.10f -
            reloadArc * 0.05f,
        weaponZ - 0.18f +
            reloadArc * 0.10f,
        0.11f,
        0.13f,
        0.28f,
        12.0f);

    drawBox(
        weaponX - 0.18f -
            reloadArc * 0.10f,
        weaponY - 0.04f -
            reloadArc * 0.12f,
        weaponZ + 0.35f,
        0.10f,
        0.12f,
        0.23f,
        12.0f);

    drawBox(
        weaponX + 0.31f,
        weaponY - 0.20f,
        weaponZ - 0.34f,
        0.13f,
        0.10f,
        0.32f,
        12.0f);

    if (weaponFire > 0.01f) {
        drawBox(
            weaponX + 0.02f,
            weaponY + 0.015f,
            weaponZ + 1.34f,
            0.13f +
                0.05f *
                weaponFire,
            0.13f +
                0.05f *
                weaponFire,
            0.16f +
                0.10f *
                weaponFire,
            11.0f);
    }

    if (uiPipeline_ == VK_NULL_HANDLE ||
        uiPipelineLayout_ == VK_NULL_HANDLE) {
        vkCmdEndRenderPass(command);
        logError("UI pipeline missing");
        return false;
    }

    vkCmdBindPipeline(
        command,
        VK_PIPELINE_BIND_POINT_GRAPHICS,
        uiPipeline_);

    const float viewportWidth =
        static_cast<float>(
            std::max(
                swapchainExtent_.width,
                1U));

    const float viewportHeight =
        static_cast<float>(
            std::max(
                swapchainExtent_.height,
                1U));

    const float minViewport =
        std::min(
            viewportWidth,
            viewportHeight);

    const auto drawUiPrimitive = [&](
        float centerXNormalized,
        float centerYNormalized,
        float halfWidthNormalized,
        float halfHeightNormalized,
        float red,
        float green,
        float blue,
        float alpha,
        float shape,
        float ringWidth) noexcept {
        UiPushConstants ui{};

        ui.centerX =
            std::clamp(
                centerXNormalized,
                0.0f,
                1.0f) *
                2.0f -
            1.0f;

        ui.centerY =
            1.0f -
            std::clamp(
                centerYNormalized,
                0.0f,
                1.0f) *
                2.0f;

        ui.halfWidth =
            std::max(
                halfWidthNormalized,
                0.0005f) *
            2.0f;

        ui.halfHeight =
            std::max(
                halfHeightNormalized,
                0.0005f) *
            2.0f;

        ui.colorR =
            std::clamp(
                red,
                0.0f,
                1.0f);

        ui.colorG =
            std::clamp(
                green,
                0.0f,
                1.0f);

        ui.colorB =
            std::clamp(
                blue,
                0.0f,
                1.0f);

        ui.colorA =
            std::clamp(
                alpha,
                0.0f,
                1.0f);

        ui.shape = shape;
        ui.ringWidth = ringWidth;

        vkCmdPushConstants(
            command,
            uiPipelineLayout_,
            VK_SHADER_STAGE_VERTEX_BIT |
                VK_SHADER_STAGE_FRAGMENT_BIT,
            0,
            static_cast<std::uint32_t>(
                sizeof(UiPushConstants)),
            &ui);

        vkCmdDraw(
            command,
            6,
            1,
            0,
            0);
    };

    const auto drawUiCircle = [&](
        float centerXNormalized,
        float centerYNormalized,
        float radiusOfShortSide,
        float red,
        float green,
        float blue,
        float alpha,
        bool ring,
        float ringWidth = 0.18f) noexcept {
        const float radiusPixels =
            std::max(
                radiusOfShortSide,
                0.002f) *
            minViewport;

        drawUiPrimitive(
            centerXNormalized,
            centerYNormalized,
            radiusPixels /
                viewportWidth,
            radiusPixels /
                viewportHeight,
            red,
            green,
            blue,
            alpha,
            ring ? 2.0f : 1.0f,
            ringWidth);
    };

    static constexpr std::array<std::uint8_t, 10>
        kDigitMasks{{
            0x3FU,
            0x06U,
            0x5BU,
            0x4FU,
            0x66U,
            0x6DU,
            0x7DU,
            0x07U,
            0x7FU,
            0x6FU,
        }};

    const auto drawSevenSegmentDigit = [&](
        int digit,
        float centerX,
        float centerY,
        float scale,
        float alpha) noexcept {
        if (digit < 0 || digit > 9) {
            return;
        }

        const std::uint8_t mask =
            kDigitMasks[
                static_cast<std::size_t>(
                    digit)];

        const float horizontalHalfWidth =
            0.0078f * scale;

        const float horizontalHalfHeight =
            0.00125f * scale;

        const float verticalHalfWidth =
            0.00120f * scale;

        const float verticalHalfHeight =
            0.0062f * scale;

        const float xOffset =
            0.0084f * scale;

        const float yOffset =
            0.0080f * scale;

        const float red =
            0.92f;

        const float green =
            0.58f +
            0.20f *
                std::clamp(
                    hud.scorePulseAlpha,
                    0.0f,
                    1.0f);

        const float blue =
            0.10f;

        const auto segment = [&](
            std::uint8_t bit,
            float x,
            float y,
            float halfWidth,
            float halfHeight) noexcept {
            if ((mask & bit) == 0U) {
                return;
            }

            drawUiPrimitive(
                x,
                y,
                halfWidth,
                halfHeight,
                red,
                green,
                blue,
                alpha,
                0.0f,
                0.10f);
        };

        segment(
            0x01U,
            centerX,
            centerY -
                yOffset * 2.0f,
            horizontalHalfWidth,
            horizontalHalfHeight);

        segment(
            0x02U,
            centerX +
                xOffset,
            centerY -
                yOffset,
            verticalHalfWidth,
            verticalHalfHeight);

        segment(
            0x04U,
            centerX +
                xOffset,
            centerY +
                yOffset,
            verticalHalfWidth,
            verticalHalfHeight);

        segment(
            0x08U,
            centerX,
            centerY +
                yOffset * 2.0f,
            horizontalHalfWidth,
            horizontalHalfHeight);

        segment(
            0x10U,
            centerX -
                xOffset,
            centerY +
                yOffset,
            verticalHalfWidth,
            verticalHalfHeight);

        segment(
            0x20U,
            centerX -
                xOffset,
            centerY -
                yOffset,
            verticalHalfWidth,
            verticalHalfHeight);

        segment(
            0x40U,
            centerX,
            centerY,
            horizontalHalfWidth,
            horizontalHalfHeight);
    };

    const float rainIntensity =
        std::clamp(
            environment.rainIntensity,
            0.0f,
            1.0f);

    if (rainIntensity > 0.01f) {
        const int visibleRainStreaks =
            std::clamp(
                static_cast<int>(
                    std::lround(
                        18.0f *
                        std::clamp(
                            environment.
                                particleDensityScale,
                            0.25f,
                            1.0f))),
                5,
                18);

        for (int i = 0;
             i < visibleRainStreaks;
             ++i) {
            const float seed =
                static_cast<float>(i) *
                0.61803398875f;

            const float wrappedX =
                std::fmod(
                    seed +
                    safeTime *
                        (0.035f +
                         rainIntensity *
                             0.018f) +
                    environment.windX *
                        0.012f,
                    1.0f);

            const float normalizedX =
                wrappedX < 0.0f
                ? wrappedX + 1.0f
                : wrappedX;

            const float fall =
                std::fmod(
                    static_cast<float>(i) *
                        0.173f +
                    safeTime *
                        (0.72f +
                         0.35f *
                             rainIntensity),
                    1.18f);

            const float normalizedY =
                fall - 0.09f;

            drawUiPrimitive(
                normalizedX,
                normalizedY,
                0.0008f,
                0.022f +
                    rainIntensity *
                        0.018f,
                0.52f,
                0.72f,
                0.92f,
                0.10f +
                    rainIntensity *
                        0.22f,
                0.0f,
                0.10f);
        }
    }

    const float fogOverlay =
        std::clamp(
            environment.fogDensity *
                0.10f *
                std::clamp(
                    environment.fogQualityScale,
                    0.25f,
                    1.0f),
            0.0f,
            0.12f);

    if (fogOverlay > 0.001f) {
        drawUiPrimitive(
            0.5f,
            0.5f,
            0.5f,
            0.5f,
            0.035f,
            0.045f,
            0.065f,
            fogOverlay,
            0.0f,
            0.10f);
    }

    const float lightningOverlay =
        std::clamp(
            environment.lightningFlash *
                0.24f *
                std::clamp(
                    environment.postProcessScale,
                    0.35f,
                    1.0f),
            0.0f,
            0.30f);

    if (lightningOverlay > 0.001f) {
        drawUiPrimitive(
            0.5f,
            0.5f,
            0.5f,
            0.5f,
            0.68f,
            0.78f,
            1.0f,
            lightningOverlay,
            0.0f,
            0.10f);
    }

    std::array<int, 6> scoreDigits{};
    std::uint64_t scoreValue =
        hud.scoreTotal %
        1000000ULL;

    for (std::size_t reverseIndex = 0;
         reverseIndex <
             scoreDigits.size();
         ++reverseIndex) {
        const std::size_t index =
            scoreDigits.size() -
            1U -
            reverseIndex;

        scoreDigits[index] =
            static_cast<int>(
                scoreValue %
                10ULL);

        scoreValue /= 10ULL;
    }

    std::size_t firstVisibleDigit =
        scoreDigits.size() - 1U;

    for (std::size_t i = 0;
         i + 1U <
             scoreDigits.size();
         ++i) {
        if (scoreDigits[i] != 0) {
            firstVisibleDigit = i;
            break;
        }
    }

    const float scorePulse =
        std::clamp(
            hud.scorePulseAlpha,
            0.0f,
            1.0f);

    const float scoreScale =
        1.0f +
        scorePulse *
            0.10f;

    const float scoreAlpha =
        0.72f +
        scorePulse *
            0.26f;

    float scoreX = 0.055f;

    for (std::size_t i = firstVisibleDigit;
         i < scoreDigits.size();
         ++i) {
        drawSevenSegmentDigit(
            scoreDigits[i],
            scoreX,
            0.095f,
            scoreScale,
            scoreAlpha);

        scoreX +=
            0.022f *
            scoreScale;
    }

    const float moveAnchorX =
        hud.moveActive
        ? std::clamp(
              hud.moveAnchorX,
              0.08f,
              0.42f)
        : 0.17f;

    const float moveAnchorY =
        hud.moveActive
        ? std::clamp(
              hud.moveAnchorY,
              0.55f,
              0.92f)
        : 0.78f;

    drawUiCircle(
        moveAnchorX,
        moveAnchorY,
        0.105f,
        0.04f,
        0.70f,
        0.95f,
        hud.moveActive
            ? 0.38f
            : 0.20f,
        true,
        0.12f);

    const float knobTravel =
        0.060f;

    drawUiCircle(
        moveAnchorX +
            std::clamp(
                hud.moveX,
                -1.0f,
                1.0f) *
            knobTravel,
        moveAnchorY -
            std::clamp(
                hud.moveY,
                -1.0f,
                1.0f) *
            knobTravel,
        0.040f,
        0.08f,
        0.78f,
        1.0f,
        hud.moveActive
            ? 0.62f
            : 0.28f,
        false);

    drawUiCircle(
        0.90f,
        0.47f,
        0.082f,
        0.98f,
        0.05f,
        0.24f,
        hud.fire
            ? 0.82f
            : 0.30f,
        true,
        hud.fire
            ? 0.24f
            : 0.12f);

    drawUiCircle(
        0.73f,
        0.54f,
        0.070f,
        0.10f,
        0.72f,
        0.96f,
        hud.aim
            ? 0.78f
            : 0.27f,
        true,
        hud.aim
            ? 0.22f
            : 0.12f);

    drawUiCircle(
        0.80f,
        0.35f,
        0.055f,
        0.96f,
        0.62f,
        0.08f,
        hud.reload
            ? 0.80f
            : 0.24f,
        true,
        hud.reload
            ? 0.24f
            : 0.11f);

    if (hud.interactAvailable) {
        const float interactProgress =
            std::clamp(
                hud.interactProgress,
                0.0f,
                1.0f);

        const float denied =
            std::clamp(
                hud.interactionDeniedAlpha,
                0.0f,
                1.0f);

        const bool affordable =
            hud.interactionAffordable;

        const float interactR =
            denied > 0.001f ||
                !affordable
            ? 0.98f
            : 0.12f;

        const float interactG =
            denied > 0.001f ||
                !affordable
            ? 0.10f
            : 0.82f;

        const float interactB =
            denied > 0.001f ||
                !affordable
            ? 0.16f
            : 0.92f;

        drawUiCircle(
            0.65f,
            0.73f,
            0.058f +
                denied *
                    0.006f,
            interactR,
            interactG,
            interactB,
            hud.interactHeld
                ? 0.82f
                : 0.42f +
                    denied *
                        0.24f,
            true,
            0.16f +
                denied *
                    0.06f);

        drawUiCircle(
            0.65f,
            0.73f,
            0.016f +
                interactProgress *
                    0.024f,
            interactR,
            interactG,
            interactB,
            0.28f +
                interactProgress *
                    0.52f,
            false);

        if (hud.interactionCost > 0U) {
            std::array<int, 5> costDigits{};
            std::uint32_t costValue =
                std::min<std::uint32_t>(
                    hud.interactionCost,
                    99999U);

            for (std::size_t reverseIndex = 0;
                 reverseIndex <
                     costDigits.size();
                 ++reverseIndex) {
                const std::size_t index =
                    costDigits.size() -
                    1U -
                    reverseIndex;

                costDigits[index] =
                    static_cast<int>(
                        costValue %
                        10U);

                costValue /= 10U;
            }

            std::size_t firstCostDigit =
                costDigits.size() - 1U;

            for (std::size_t i = 0;
                 i + 1U <
                     costDigits.size();
                 ++i) {
                if (costDigits[i] != 0) {
                    firstCostDigit = i;
                    break;
                }
            }

            float costX =
                0.65f -
                static_cast<float>(
                    costDigits.size() -
                    firstCostDigit) *
                    0.010f;

            for (std::size_t i = firstCostDigit;
                 i < costDigits.size();
                 ++i) {
                drawSevenSegmentDigit(
                    costDigits[i],
                    costX,
                    0.655f,
                    0.72f,
                    affordable
                        ? 0.78f
                        : 0.50f +
                            denied *
                                0.40f);

                costX += 0.017f;
            }
        }
    }

    drawUiCircle(
        0.89f,
        0.72f,
        0.075f,
        0.88f,
        0.93f,
        1.0f,
        hud.jump
            ? 0.72f
            : 0.24f,
        true,
        hud.jump
            ? 0.22f
            : 0.11f);

    drawUiCircle(
        0.77f,
        0.83f,
        0.067f,
        0.66f,
        0.10f,
        0.95f,
        hud.stance
            ? 0.76f
            : 0.25f,
        true,
        hud.stance
            ? 0.24f
            : 0.12f);

    const float roundProgress =
        std::clamp(
            scene.roundProgress,
            0.0f,
            1.0f);

    constexpr float roundCenterX = 0.5f;
    constexpr float roundCenterY = 0.055f;
    constexpr float roundHalfWidth = 0.13f;
    constexpr float roundHalfHeight = 0.0035f;

    drawUiPrimitive(
        roundCenterX,
        roundCenterY,
        roundHalfWidth,
        roundHalfHeight,
        0.02f,
        0.025f,
        0.035f,
        0.62f,
        0.0f,
        0.10f);

    const float roundFill =
        std::max(
            roundHalfWidth *
                roundProgress,
            0.0005f);

    drawUiPrimitive(
        roundCenterX -
            roundHalfWidth +
            roundFill,
        roundCenterY,
        roundFill,
        roundHalfHeight * 0.70f,
        scene.interRound
            ? 0.72f
            : 0.62f,
        scene.interRound
            ? 0.16f
            : 0.06f,
        scene.interRound
            ? 0.96f
            : 0.78f,
        0.88f,
        0.0f,
        0.10f);

    const float magazineRatio =
        std::clamp(
            hud.weaponMagazineRatio,
            0.0f,
            1.0f);

    constexpr float ammoCenterX = 0.885f;
    constexpr float ammoCenterY = 0.935f;
    constexpr float ammoHalfWidth = 0.072f;
    constexpr float ammoHalfHeight = 0.0045f;

    drawUiPrimitive(
        ammoCenterX,
        ammoCenterY,
        ammoHalfWidth,
        ammoHalfHeight,
        0.02f,
        0.025f,
        0.035f,
        0.72f,
        0.0f,
        0.10f);

    const float ammoFillHalf =
        std::max(
            ammoHalfWidth *
                magazineRatio,
            0.0005f);

    const float ammoLeft =
        ammoCenterX -
        ammoHalfWidth;

    const float ammoFillCenter =
        ammoLeft +
        ammoFillHalf;

    const bool lowAmmo =
        magazineRatio <
        0.25f;

    drawUiPrimitive(
        ammoFillCenter,
        ammoCenterY,
        ammoFillHalf,
        ammoHalfHeight * 0.72f,
        lowAmmo ? 0.98f : 0.08f,
        lowAmmo ? 0.08f : 0.78f,
        lowAmmo ? 0.12f : 0.96f,
        0.92f,
        0.0f,
        0.10f);

    if (hud.weaponReloadAlpha > 0.001f) {
        const float reloadProgress =
            std::clamp(
                hud.weaponReloadAlpha,
                0.0f,
                1.0f);

        drawUiPrimitive(
            ammoLeft +
                ammoHalfWidth *
                reloadProgress,
            ammoCenterY - 0.014f,
            std::max(
                ammoHalfWidth *
                    reloadProgress,
                0.0005f),
            ammoHalfHeight * 0.48f,
            0.96f,
            0.62f,
            0.08f,
            0.78f,
            0.0f,
            0.10f);
    }

    const float healthRatio =
        std::clamp(
            hud.playerHealthRatio,
            0.0f,
            1.0f);

    constexpr float healthCenterX = 0.145f;
    constexpr float healthCenterY = 0.935f;
    constexpr float healthHalfWidth = 0.082f;
    constexpr float healthHalfHeight = 0.0050f;

    drawUiPrimitive(
        healthCenterX,
        healthCenterY,
        healthHalfWidth,
        healthHalfHeight,
        0.025f,
        0.020f,
        0.025f,
        0.76f,
        0.0f,
        0.10f);

    const float healthFillHalf =
        std::max(
            healthHalfWidth *
                healthRatio,
            0.0005f);

    drawUiPrimitive(
        healthCenterX -
            healthHalfWidth +
            healthFillHalf,
        healthCenterY,
        healthFillHalf,
        healthHalfHeight * 0.72f,
        0.96f -
            healthRatio * 0.70f,
        0.08f +
            healthRatio * 0.58f,
        0.12f,
        0.92f,
        0.0f,
        0.10f);

    const float damageFlash =
        std::clamp(
            hud.damageFlashAlpha,
            0.0f,
            1.0f);

    const float horrorVignette =
        std::clamp(
            hud.horrorVignette,
            0.0f,
            0.45f);

    const float edgeAlpha =
        std::clamp(
            damageFlash * 0.34f +
                horrorVignette * 0.45f,
            0.0f,
            0.52f);

    if (edgeAlpha > 0.001f) {
        drawUiPrimitive(
            0.5f,
            0.055f,
            0.5f,
            0.055f,
            0.34f,
            0.005f,
            0.012f,
            edgeAlpha,
            0.0f,
            0.10f);

        drawUiPrimitive(
            0.5f,
            0.945f,
            0.5f,
            0.055f,
            0.34f,
            0.005f,
            0.012f,
            edgeAlpha,
            0.0f,
            0.10f);

        drawUiPrimitive(
            0.035f,
            0.5f,
            0.035f,
            0.5f,
            0.34f,
            0.005f,
            0.012f,
            edgeAlpha,
            0.0f,
            0.10f);

        drawUiPrimitive(
            0.965f,
            0.5f,
            0.035f,
            0.5f,
            0.34f,
            0.005f,
            0.012f,
            edgeAlpha,
            0.0f,
            0.10f);
    }

    const float deathAlpha =
        std::clamp(
            hud.deathAlpha,
            0.0f,
            1.0f);

    if (deathAlpha > 0.001f) {
        drawUiPrimitive(
            0.5f,
            0.5f,
            0.5f,
            0.5f,
            0.035f,
            0.0f,
            0.006f,
            deathAlpha * 0.86f,
            0.0f,
            0.10f);
    }

    // Thin center reticle. Keeping this procedural avoids introducing font or
    // texture dependencies before the renderer has an asset streaming layer.
    const float hitMarker =
        std::clamp(
            hud.hitMarkerAlpha,
            0.0f,
            1.0f);

    const float criticalHit =
        std::clamp(
            hud.criticalHitAlpha,
            0.0f,
            1.0f);

    const float reticleR =
        std::min(
            1.0f,
            0.95f +
                criticalHit * 0.05f);

    const float reticleG =
        std::max(
            0.0f,
            0.96f -
                hitMarker * 0.78f -
                criticalHit * 0.14f);

    const float reticleB =
        std::max(
            0.0f,
            1.0f -
                hitMarker * 0.72f -
                criticalHit * 0.10f);

    const float reticleAlpha =
        0.72f +
        hitMarker * 0.24f;

    drawUiPrimitive(
        0.5f,
        0.5f,
        0.0011f,
        0.010f,
        reticleR,
        reticleG,
        reticleB,
        reticleAlpha,
        0.0f,
        0.10f);

    drawUiPrimitive(
        0.5f,
        0.5f,
        0.0060f,
        0.0016f,
        reticleR,
        reticleG,
        reticleB,
        reticleAlpha,
        0.0f,
        0.10f);

    if (hitMarker > 0.001f) {
        const float slashWidth =
            0.0012f +
            criticalHit * 0.0008f;

        const float slashHeight =
            0.013f +
            criticalHit * 0.009f;

        drawUiPrimitive(
            0.490f,
            0.490f,
            slashWidth,
            slashHeight,
            1.0f,
            0.10f,
            0.18f,
            hitMarker,
            0.0f,
            0.10f);

        drawUiPrimitive(
            0.510f,
            0.510f,
            slashWidth,
            slashHeight,
            1.0f,
            0.10f,
            0.18f,
            hitMarker,
            0.0f,
            0.10f);
    }

    if (hud.gyroAvailable) {
        drawUiCircle(
            0.965f,
            0.075f,
            0.010f,
            0.10f,
            0.82f,
            0.96f,
            0.58f,
            false);
    }

    vkCmdEndRenderPass(command);

    if (!ok(
            vkEndCommandBuffer(
                command))) {
        logError("vkEndCommandBuffer failed");
        return false;
    }

    return true;
}

} // namespace xziel::android
