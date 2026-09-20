#include "vulkan_clear_renderer.hpp"

#include <android/log.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <limits>

namespace xziel::android {

namespace {

constexpr const char* kTag = "XzielVulkan";

void logInfo(const char* message) noexcept {
    __android_log_print(ANDROID_LOG_INFO, kTag, "%s", message);
}

void logError(const char* message) noexcept {
    __android_log_print(ANDROID_LOG_ERROR, kTag, "%s", message);
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
    AAssetManager* assetManager) noexcept {
    shutdown();

    if (window == nullptr || assetManager == nullptr) {
        logError("initialize requires window + asset manager");
        return false;
    }

    window_ = window;
    assetManager_ = assetManager;
    ANativeWindow_acquire(window_);

    if (!createInstance() ||
        !createSurface(window_) ||
        !selectPhysicalDevice() ||
        !createDevice() ||
        !createSwapchain() ||
        !createRenderPass() ||
        !createGraphicsPipeline() ||
        !createImageViewsAndFramebuffers() ||
        !createCommandResources() ||
        !createSyncObjects()) {
        logError("Vulkan initialization failed");
        shutdown();
        return false;
    }

    initialized_ = true;
    logInfo("FIRST_VULKAN_FRAMEWORK_READY");
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
        vkDestroyDevice(device_, nullptr);
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
        vkDestroyInstance(instance_, nullptr);
        instance_ = VK_NULL_HANDLE;
    }

    if (window_ != nullptr) {
        ANativeWindow_release(window_);
        window_ = nullptr;
    }

    assetManager_ = nullptr;
    frameIndex_ = 0;
}

bool VulkanClearRenderer::drawFrame(
    float timeSeconds) noexcept {
    if (!initialized_ ||
        device_ == VK_NULL_HANDLE ||
        swapchain_ == VK_NULL_HANDLE) {
        return false;
    }

    auto& frame =
        frames_[frameIndex_ % kFramesInFlight];

    VkResult result = vkWaitForFences(
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

    result = vkAcquireNextImageKHR(
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
        result = vkWaitForFences(
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

    imageFences_[imageIndex] = frame.inFlight;

    result = vkResetFences(
        device_,
        1,
        &frame.inFlight);

    if (!ok(result)) {
        logError("vkResetFences failed");
        return false;
    }

    if (!recordClearCommand(
            imageIndex,
            timeSeconds)) {
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

    result = vkQueueSubmit(
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
    present.pSwapchains = &swapchain_;
    present.pImageIndices = &imageIndex;

    result =
        vkQueuePresentKHR(
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
        VK_MAKE_API_VERSION(0, 0, 0, 1);
    appInfo.pEngineName = "Xziel Engine";
    appInfo.engineVersion =
        VK_MAKE_API_VERSION(0, 0, 0, 1);
    appInfo.apiVersion = VK_API_VERSION_1_1;

    VkInstanceCreateInfo createInfo{
        VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO
    };
    createInfo.pApplicationInfo = &appInfo;
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

    std::vector<VkPhysicalDevice>
        devices(count);

    result =
        vkEnumeratePhysicalDevices(
            instance_,
            &count,
            devices.data());

    if (!ok(result)) {
        logError("vkEnumeratePhysicalDevices failed");
        return false;
    }

    for (const auto device : devices) {
        std::uint32_t extensionCount = 0;
        if (!ok(
                vkEnumerateDeviceExtensionProperties(
                    device,
                    nullptr,
                    &extensionCount,
                    nullptr))) {
            continue;
        }

        std::vector<VkExtensionProperties>
            extensions(extensionCount);

        if (!ok(
                vkEnumerateDeviceExtensionProperties(
                    device,
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
            device,
            &queueCount,
            nullptr);

        std::vector<VkQueueFamilyProperties>
            queues(queueCount);

        vkGetPhysicalDeviceQueueFamilyProperties(
            device,
            &queueCount,
            queues.data());

        for (std::uint32_t i = 0;
             i < queueCount;
             ++i) {
            VkBool32 present = VK_FALSE;

            if (!ok(
                    vkGetPhysicalDeviceSurfaceSupportKHR(
                        device,
                        i,
                        surface_,
                        &present))) {
                continue;
            }

            const bool graphics =
                (queues[i].queueFlags &
                 VK_QUEUE_GRAPHICS_BIT) != 0;

            if (graphics && present == VK_TRUE) {
                physicalDevice_ = device;
                graphicsQueueFamily_ = i;
                return true;
            }
        }
    }

    logError(
        "No device supports graphics + present + swapchain");
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

    constexpr std::array<const char*, 1>
        extensions{
            VK_KHR_SWAPCHAIN_EXTENSION_NAME,
        };

    VkDeviceCreateInfo createInfo{
        VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO
    };
    createInfo.queueCreateInfoCount = 1;
    createInfo.pQueueCreateInfos =
        &queueInfo;
    createInfo.enabledExtensionCount =
        static_cast<std::uint32_t>(
            extensions.size());
    createInfo.ppEnabledExtensionNames =
        extensions.data();

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

    return graphicsQueue_ != VK_NULL_HANDLE;
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

    std::vector<VkSurfaceFormatKHR>
        formats(count);

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
        std::numeric_limits<
            std::uint32_t>::max()) {
        const auto width =
            static_cast<std::uint32_t>(
                std::max(
                    1,
                    ANativeWindow_getWidth(
                        window_)));

        const auto height =
            static_cast<std::uint32_t>(
                std::max(
                    1,
                    ANativeWindow_getHeight(
                        window_)));

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
    swapchainExtent_ = extent;

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

    return true;
}

bool VulkanClearRenderer::createRenderPass() noexcept {
    VkAttachmentDescription color{};
    color.format = swapchainFormat_;
    color.samples = VK_SAMPLE_COUNT_1_BIT;
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

    VkAttachmentReference reference{};
    reference.attachment = 0;
    reference.layout =
        VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;

    VkSubpassDescription subpass{};
    subpass.pipelineBindPoint =
        VK_PIPELINE_BIND_POINT_GRAPHICS;
    subpass.colorAttachmentCount = 1;
    subpass.pColorAttachments = &reference;

    VkSubpassDependency dependency{};
    dependency.srcSubpass =
        VK_SUBPASS_EXTERNAL;
    dependency.dstSubpass = 0;
    dependency.srcStageMask =
        VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dependency.dstStageMask =
        VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dependency.srcAccessMask = 0;
    dependency.dstAccessMask =
        VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;

    VkRenderPassCreateInfo createInfo{
        VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO
    };
    createInfo.attachmentCount = 1;
    createInfo.pAttachments = &color;
    createInfo.subpassCount = 1;
    createInfo.pSubpasses = &subpass;
    createInfo.dependencyCount = 1;
    createInfo.pDependencies = &dependency;

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

    if (bytesRead != length) {
        logError("Failed reading complete SPIR-V shader asset");
        return false;
    }

    VkShaderModuleCreateInfo createInfo{
        VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO
    };
    createInfo.codeSize =
        static_cast<std::size_t>(length);
    createInfo.pCode = words.data();

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
    VkShaderModule vertex = VK_NULL_HANDLE;
    VkShaderModule fragment = VK_NULL_HANDLE;

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
    scissor.extent = swapchainExtent_;

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
    raster.depthClampEnable = VK_FALSE;
    raster.rasterizerDiscardEnable = VK_FALSE;
    raster.polygonMode = VK_POLYGON_MODE_FILL;
    raster.cullMode = VK_CULL_MODE_NONE;
    raster.frontFace = VK_FRONT_FACE_COUNTER_CLOCKWISE;
    raster.depthBiasEnable = VK_FALSE;
    raster.lineWidth = 1.0f;

    VkPipelineMultisampleStateCreateInfo multisample{
        VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO
    };
    multisample.rasterizationSamples =
        VK_SAMPLE_COUNT_1_BIT;
    multisample.sampleShadingEnable =
        VK_FALSE;

    VkPipelineColorBlendAttachmentState colorAttachment{};
    colorAttachment.blendEnable = VK_FALSE;
    colorAttachment.colorWriteMask =
        VK_COLOR_COMPONENT_R_BIT |
        VK_COLOR_COMPONENT_G_BIT |
        VK_COLOR_COMPONENT_B_BIT |
        VK_COLOR_COMPONENT_A_BIT;

    VkPipelineColorBlendStateCreateInfo colorBlend{
        VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO
    };
    colorBlend.logicOpEnable = VK_FALSE;
    colorBlend.attachmentCount = 1;
    colorBlend.pAttachments =
        &colorAttachment;

    VkPipelineLayoutCreateInfo layoutInfo{
        VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO
    };

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
    pipelineInfo.pStages = stages.data();
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

    logInfo("FIRST_TRIANGLE_PIPELINE_READY");
    return true;
}

bool VulkanClearRenderer::
createImageViewsAndFramebuffers() noexcept {
    imageViews_.resize(
        swapchainImages_.size(),
        VK_NULL_HANDLE);

    framebuffers_.resize(
        swapchainImages_.size(),
        VK_NULL_HANDLE);

    for (std::size_t i = 0;
         i < swapchainImages_.size();
         ++i) {
        VkImageViewCreateInfo view{
            VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO
        };
        view.image = swapchainImages_[i];
        view.viewType =
            VK_IMAGE_VIEW_TYPE_2D;
        view.format = swapchainFormat_;
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

        const VkImageView attachment =
            imageViews_[i];

        VkFramebufferCreateInfo framebuffer{
            VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO
        };
        framebuffer.renderPass = renderPass_;
        framebuffer.attachmentCount = 1;
        framebuffer.pAttachments = &attachment;
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

bool VulkanClearRenderer::
createCommandResources() noexcept {
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

    commandBuffers_.resize(
        swapchainImages_.size(),
        VK_NULL_HANDLE);

    VkCommandBufferAllocateInfo alloc{
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO
    };
    alloc.commandPool = commandPool_;
    alloc.level =
        VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    alloc.commandBufferCount =
        static_cast<std::uint32_t>(
            commandBuffers_.size());

    if (!ok(
            vkAllocateCommandBuffers(
                device_,
                &alloc,
                commandBuffers_.data()))) {
        logError(
            "vkAllocateCommandBuffers failed");
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
            logError(
                "failed creating sync objects");
            return false;
        }
    }

    return true;
}

void VulkanClearRenderer::
destroySwapchainResources() noexcept {
    if (device_ == VK_NULL_HANDLE) {
        swapchainImages_.clear();
        imageViews_.clear();
        framebuffers_.clear();
        commandBuffers_.clear();
        imageFences_.clear();
        return;
    }

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

    for (const auto framebuffer :
         framebuffers_) {
        if (framebuffer != VK_NULL_HANDLE) {
            vkDestroyFramebuffer(
                device_,
                framebuffer,
                nullptr);
        }
    }

    framebuffers_.clear();

    for (const auto view : imageViews_) {
        if (view != VK_NULL_HANDLE) {
            vkDestroyImageView(
                device_,
                view,
                nullptr);
        }
    }

    imageViews_.clear();

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

    if (renderPass_ != VK_NULL_HANDLE) {
        vkDestroyRenderPass(
            device_,
            renderPass_,
            nullptr);
        renderPass_ = VK_NULL_HANDLE;
    }

    if (swapchain_ != VK_NULL_HANDLE) {
        vkDestroySwapchainKHR(
            device_,
            swapchain_,
            nullptr);
        swapchain_ = VK_NULL_HANDLE;
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

    if (!ok(vkDeviceWaitIdle(device_))) {
        return false;
    }

    destroySwapchainResources();

    const bool success =
        createSwapchain() &&
        createRenderPass() &&
        createGraphicsPipeline() &&
        createImageViewsAndFramebuffers() &&
        createCommandResources();

    if (!success) {
        logError("Swapchain recreation failed");
    }

    return success;
}

bool VulkanClearRenderer::recordClearCommand(
    std::uint32_t imageIndex,
    float timeSeconds) noexcept {
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
            timeSeconds * 0.55f);

    VkClearValue clear{};
    clear.color.float32[0] =
        0.012f + pulse * 0.020f;
    clear.color.float32[1] =
        0.006f + pulse * 0.004f;
    clear.color.float32[2] =
        0.016f + pulse * 0.026f;
    clear.color.float32[3] = 1.0f;

    VkRenderPassBeginInfo render{
        VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO
    };
    render.renderPass = renderPass_;
    render.framebuffer =
        framebuffers_[imageIndex];
    render.renderArea.offset = {0, 0};
    render.renderArea.extent =
        swapchainExtent_;
    render.clearValueCount = 1;
    render.pClearValues = &clear;

    vkCmdBeginRenderPass(
        command,
        &render,
        VK_SUBPASS_CONTENTS_INLINE);

    if (graphicsPipeline_ == VK_NULL_HANDLE) {
        vkCmdEndRenderPass(command);
        logError("graphics pipeline missing");
        return false;
    }

    vkCmdBindPipeline(
        command,
        VK_PIPELINE_BIND_POINT_GRAPHICS,
        graphicsPipeline_);

    vkCmdDraw(
        command,
        3,
        1,
        0,
        0);

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
