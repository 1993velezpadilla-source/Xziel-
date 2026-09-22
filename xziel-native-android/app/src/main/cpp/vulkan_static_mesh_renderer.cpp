#include "vulkan_static_mesh_renderer.hpp"

#include <android/bitmap.h>
#include <android/imagedecoder.h>
#include <android/log.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstddef>
#include <cstring>
#include <limits>
#include <span>
#include <unordered_map>
#include <vector>

namespace xziel::android {

namespace {

constexpr const char* kTag = "XzielSanctumMesh";

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

[[nodiscard]] bool ok(VkResult result) noexcept {
    return result == VK_SUCCESS;
}

std::string textureAssetPath(
    const std::string& exportedName) {
    std::string path = exportedName;

    if (!path.ends_with(".png")) {
        path += ".png";
    }

    return path;
}

} // namespace

VulkanStaticMeshRenderer::~VulkanStaticMeshRenderer() {
    shutdown();
}

bool VulkanStaticMeshRenderer::initialize(
    VkPhysicalDevice physicalDevice,
    VkDevice device,
    VkQueue graphicsQueue,
    std::uint32_t graphicsQueueFamily,
    VkCommandPool commandPool,
    VkRenderPass renderPass,
    AAssetManager* assetManager,
    const char* modelAssetPath) noexcept {
    shutdown();

    if (physicalDevice == VK_NULL_HANDLE ||
        device == VK_NULL_HANDLE ||
        graphicsQueue == VK_NULL_HANDLE ||
        graphicsQueueFamily == UINT32_MAX ||
        commandPool == VK_NULL_HANDLE ||
        renderPass == VK_NULL_HANDLE ||
        assetManager == nullptr ||
        modelAssetPath == nullptr) {
        return false;
    }

    physicalDevice_ = physicalDevice;
    device_ = device;

    VkPhysicalDeviceFeatures deviceFeatures{};
    vkGetPhysicalDeviceFeatures(
        physicalDevice_,
        &deviceFeatures);

    VkPhysicalDeviceProperties deviceProperties{};
    vkGetPhysicalDeviceProperties(
        physicalDevice_,
        &deviceProperties);

    samplerAnisotropyEnabled_ =
        deviceFeatures.samplerAnisotropy == VK_TRUE;

    maxSamplerAnisotropy_ =
        samplerAnisotropyEnabled_
        ? std::clamp(
              deviceProperties.limits.maxSamplerAnisotropy,
              1.0f,
              8.0f)
        : 1.0f;

    graphicsQueue_ = graphicsQueue;
    graphicsQueueFamily_ = graphicsQueueFamily;
    commandPool_ = commandPool;
    renderPass_ = renderPass;

    StaticMeshAsset asset{};
    if (!loadModel(
            assetManager,
            modelAssetPath,
            asset)) {
        shutdown();
        return false;
    }

    if (!createPipeline(assetManager)) {
        shutdown();
        return false;
    }

    VkDescriptorPoolSize poolSize{};
    poolSize.type =
        VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    poolSize.descriptorCount =
        static_cast<std::uint32_t>(
            std::max<std::size_t>(
                asset.batches.size(),
                1U));

    VkDescriptorPoolCreateInfo poolInfo{
        VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO
    };
    poolInfo.maxSets =
        poolSize.descriptorCount;
    poolInfo.poolSizeCount = 1U;
    poolInfo.pPoolSizes = &poolSize;

    if (!ok(
            vkCreateDescriptorPool(
                device_,
                &poolInfo,
                nullptr,
                &descriptorPool_))) {
        logError("descriptor pool creation failed");
        shutdown();
        return false;
    }

    std::unordered_map<std::string, std::uint32_t>
        textureIndices;

    try {
        batches_.reserve(asset.batches.size());

        for (const auto& batch : asset.batches) {
            const std::string path =
                textureAssetPath(
                    batch.textureName);

            auto found =
                textureIndices.find(path);

            std::uint32_t textureIndex = 0U;

            if (found == textureIndices.end()) {
                GpuTexture texture{};

                if (!createTexture(
                        assetManager,
                        path,
                        texture)) {
                    logError(
                        "Sanctum albedo texture load failed");
                    shutdown();
                    return false;
                }

                textureIndex =
                    static_cast<std::uint32_t>(
                        textures_.size());

                textures_.emplace_back(
                    std::move(texture));

                textureIndices.emplace(
                    path,
                    textureIndex);
            } else {
                textureIndex = found->second;
            }

            GpuBatch gpuBatch{};

            if (!uploadBatch(
                    batch,
                    textureIndex,
                    gpuBatch)) {
                logError(
                    "Sanctum geometry upload failed");
                shutdown();
                return false;
            }

            batches_.emplace_back(
                std::move(gpuBatch));
        }
    } catch (...) {
        logError(
            "Sanctum GPU resource allocation failed");
        shutdown();
        return false;
    }

    totalVertices_ =
        asset.totalVertices;
    totalIndices_ =
        asset.totalIndices;
    ready_ =
        !batches_.empty() &&
        !textures_.empty();

    if (ready_) {
        const std::string modelPath =
            modelAssetPath != nullptr
            ? modelAssetPath
            : "";

        if (modelPath.find("/weapons/") !=
            std::string::npos) {
            logInfo("XZIEL_WEAPON_VIEWMODEL_READY");
        } else {
            logInfo("XZIEL_SANCTUM_MESH_READY");
        }
    }

    return ready_;
}

void VulkanStaticMeshRenderer::shutdown() noexcept {
    ready_ = false;

    if (device_ != VK_NULL_HANDLE) {
        for (auto& batch : batches_) {
            destroyBatch(batch);
        }

        for (auto& texture : textures_) {
            destroyTexture(texture);
        }

        if (pipeline_ != VK_NULL_HANDLE) {
            vkDestroyPipeline(
                device_,
                pipeline_,
                nullptr);
        }

        if (pipelineLayout_ != VK_NULL_HANDLE) {
            vkDestroyPipelineLayout(
                device_,
                pipelineLayout_,
                nullptr);
        }

        if (descriptorPool_ != VK_NULL_HANDLE) {
            vkDestroyDescriptorPool(
                device_,
                descriptorPool_,
                nullptr);
        }

        if (descriptorSetLayout_ != VK_NULL_HANDLE) {
            vkDestroyDescriptorSetLayout(
                device_,
                descriptorSetLayout_,
                nullptr);
        }
    }

    batches_.clear();
    textures_.clear();

    pipeline_ = VK_NULL_HANDLE;
    pipelineLayout_ = VK_NULL_HANDLE;
    descriptorPool_ = VK_NULL_HANDLE;
    descriptorSetLayout_ = VK_NULL_HANDLE;

    totalVertices_ = 0U;
    totalIndices_ = 0U;
    samplerAnisotropyEnabled_ = false;
    maxSamplerAnisotropy_ = 1.0f;

    physicalDevice_ = VK_NULL_HANDLE;
    device_ = VK_NULL_HANDLE;
    graphicsQueue_ = VK_NULL_HANDLE;
    graphicsQueueFamily_ = UINT32_MAX;
    commandPool_ = VK_NULL_HANDLE;
    renderPass_ = VK_NULL_HANDLE;
}

bool VulkanStaticMeshRenderer::ready() const noexcept {
    return ready_;
}

std::uint32_t VulkanStaticMeshRenderer::batchCount() const noexcept {
    return static_cast<std::uint32_t>(
        batches_.size());
}

std::uint32_t VulkanStaticMeshRenderer::totalVertices() const noexcept {
    return totalVertices_;
}

std::uint32_t VulkanStaticMeshRenderer::totalIndices() const noexcept {
    return totalIndices_;
}

void VulkanStaticMeshRenderer::record(
    VkCommandBuffer command,
    VkExtent2D extent,
    const StaticMeshCameraState& camera,
    const StaticMeshEnvironmentState& environment) const noexcept {
    if (!ready_ ||
        command == VK_NULL_HANDLE ||
        extent.width == 0U ||
        extent.height == 0U) {
        return;
    }

    // Do not let a bad gameplay/animation value poison clip-space math.
    // A NaN/Inf transform can turn otherwise valid viewmodel triangles into
    // full-screen streaks on some drivers.
    if (!std::isfinite(state.x) ||
        !std::isfinite(state.y) ||
        !std::isfinite(state.z) ||
        !std::isfinite(state.scale) ||
        !std::isfinite(state.yawRadians) ||
        !std::isfinite(state.pitchRadians) ||
        !std::isfinite(state.rollRadians) ||
        !std::isfinite(state.verticalFovDegrees) ||
        !std::isfinite(state.aspect)) {
        return;
    }

    vkCmdBindPipeline(
        command,
        VK_PIPELINE_BIND_POINT_GRAPHICS,
        pipeline_);

    VkViewport viewport{};
    viewport.x = 0.0f;
    viewport.y = 0.0f;
    viewport.width =
        static_cast<float>(extent.width);
    viewport.height =
        static_cast<float>(extent.height);
    viewport.minDepth = 0.0f;
    viewport.maxDepth = 1.0f;

    VkRect2D scissor{};
    scissor.extent = extent;

    vkCmdSetViewport(
        command,
        0U,
        1U,
        &viewport);

    vkCmdSetScissor(
        command,
        0U,
        1U,
        &scissor);

    PushConstants push{};
    push.cameraX = camera.x;
    push.cameraY = camera.y;
    push.cameraZ = camera.z;
    push.cameraYaw = camera.yawRadians;
    push.cameraPitch = camera.pitchRadians;
    push.verticalFovDegrees =
        camera.verticalFovDegrees;
    push.aspect =
        std::max(camera.aspect, 0.25f);
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
    push.modelScale = 1.0f;
    push.viewmodelMode = 0.0f;

    vkCmdPushConstants(
        command,
        pipelineLayout_,
        VK_SHADER_STAGE_VERTEX_BIT |
            VK_SHADER_STAGE_FRAGMENT_BIT,
        0U,
        static_cast<std::uint32_t>(
            sizeof(push)),
        &push);

    const float yawCos =
        std::cos(camera.yawRadians);
    const float yawSin =
        std::sin(camera.yawRadians);
    const float pitchCos =
        std::cos(camera.pitchRadians);
    const float pitchSin =
        std::sin(camera.pitchRadians);
    const float halfFovRadians =
        std::clamp(
            camera.verticalFovDegrees,
            50.0f,
            110.0f) *
        0.5f *
        0.01745329251994329577f;
    const float tanHalfFov =
        std::tan(halfFovRadians);
    constexpr float nearPlane = 0.08f;
    constexpr float farPlane = 180.0f;

    for (const auto& batch : batches_) {
        if (batch.textureIndex >=
            textures_.size()) {
            continue;
        }

        const float centerX =
            (batch.bounds.minimum[0] +
             batch.bounds.maximum[0]) *
            0.5f;
        const float centerY =
            (batch.bounds.minimum[1] +
             batch.bounds.maximum[1]) *
            0.5f;
        const float centerZ =
            (batch.bounds.minimum[2] +
             batch.bounds.maximum[2]) *
            0.5f;

        const float extentX =
            (batch.bounds.maximum[0] -
             batch.bounds.minimum[0]) *
            0.5f;
        const float extentY =
            (batch.bounds.maximum[1] -
             batch.bounds.minimum[1]) *
            0.5f;
        const float extentZ =
            (batch.bounds.maximum[2] -
             batch.bounds.minimum[2]) *
            0.5f;

        const float radius =
            std::sqrt(
                extentX * extentX +
                extentY * extentY +
                extentZ * extentZ);

        const float relativeX =
            centerX - camera.x;
        const float relativeY =
            centerY - camera.y;
        const float relativeZ =
            centerZ - camera.z;

        const float yawViewX =
            yawCos * relativeX -
            yawSin * relativeZ;
        const float yawViewZ =
            yawSin * relativeX +
            yawCos * relativeZ;

        const float viewY =
            pitchCos * relativeY +
            pitchSin * yawViewZ;
        const float viewZ =
            -pitchSin * relativeY +
            pitchCos * yawViewZ;

        if (viewZ + radius < nearPlane ||
            viewZ - radius > farPlane) {
            continue;
        }

        const float projectedDepth =
            std::max(viewZ, nearPlane);
        const float halfHeight =
            projectedDepth *
            tanHalfFov;
        const float halfWidth =
            halfHeight *
            std::max(camera.aspect, 0.25f);

        if (std::abs(yawViewX) - radius >
                halfWidth ||
            std::abs(viewY) - radius >
                halfHeight) {
            continue;
        }

        const auto& texture =
            textures_[batch.textureIndex];

        const VkDeviceSize offset = 0U;

        vkCmdBindVertexBuffers(
            command,
            0U,
            1U,
            &batch.vertexBuffer,
            &offset);

        vkCmdBindIndexBuffer(
            command,
            batch.indexBuffer,
            0U,
            VK_INDEX_TYPE_UINT16);

        vkCmdBindDescriptorSets(
            command,
            VK_PIPELINE_BIND_POINT_GRAPHICS,
            pipelineLayout_,
            0U,
            1U,
            &texture.descriptorSet,
            0U,
            nullptr);

        vkCmdDrawIndexed(
            command,
            batch.indexCount,
            1U,
            0U,
            0,
            0U);
    }
}

void VulkanStaticMeshRenderer::recordViewmodel(
    VkCommandBuffer command,
    VkExtent2D extent,
    const StaticMeshViewmodelState& state) const noexcept {
    if (!ready_ ||
        command == VK_NULL_HANDLE ||
        extent.width == 0U ||
        extent.height == 0U) {
        return;
    }

    vkCmdBindPipeline(
        command,
        VK_PIPELINE_BIND_POINT_GRAPHICS,
        pipeline_);

    VkViewport viewport{};
    viewport.width =
        static_cast<float>(extent.width);
    viewport.height =
        static_cast<float>(extent.height);
    viewport.minDepth = 0.0f;
    viewport.maxDepth = 1.0f;

    VkRect2D scissor{};
    scissor.extent = extent;

    vkCmdSetViewport(
        command,
        0U,
        1U,
        &viewport);

    vkCmdSetScissor(
        command,
        0U,
        1U,
        &scissor);

    PushConstants push{};
    push.verticalFovDegrees =
        std::clamp(
            state.verticalFovDegrees,
            50.0f,
            110.0f);
    push.aspect =
        std::max(
            state.aspect,
            0.25f);
    push.modelX = state.x;
    push.modelY = state.y;
    push.modelZ = state.z;
    push.modelScale =
        std::clamp(
            state.scale,
            0.05f,
            8.0f);
    constexpr float kTwoPi =
        6.28318530717958647692f;
    push.modelYaw =
        std::remainder(
            state.yawRadians,
            kTwoPi);
    push.modelPitch =
        std::remainder(
            state.pitchRadians,
            kTwoPi);
    push.modelRoll =
        std::remainder(
            state.rollRadians,
            kTwoPi);
    push.viewmodelMode = 1.0f;

    vkCmdPushConstants(
        command,
        pipelineLayout_,
        VK_SHADER_STAGE_VERTEX_BIT |
            VK_SHADER_STAGE_FRAGMENT_BIT,
        0U,
        static_cast<std::uint32_t>(
            sizeof(push)),
        &push);

    for (const auto& batch : batches_) {
        if (batch.textureIndex >=
            textures_.size()) {
            continue;
        }

        const auto& texture =
            textures_[batch.textureIndex];

        const VkDeviceSize offset = 0U;

        vkCmdBindVertexBuffers(
            command,
            0U,
            1U,
            &batch.vertexBuffer,
            &offset);

        vkCmdBindIndexBuffer(
            command,
            batch.indexBuffer,
            0U,
            VK_INDEX_TYPE_UINT16);

        vkCmdBindDescriptorSets(
            command,
            VK_PIPELINE_BIND_POINT_GRAPHICS,
            pipelineLayout_,
            0U,
            1U,
            &texture.descriptorSet,
            0U,
            nullptr);

        vkCmdDrawIndexed(
            command,
            batch.indexCount,
            1U,
            0U,
            0,
            0U);
    }
}

bool VulkanStaticMeshRenderer::loadModel(
    AAssetManager* assetManager,
    const char* path,
    StaticMeshAsset& out) noexcept {
    AAsset* asset =
        AAssetManager_open(
            assetManager,
            path,
            AASSET_MODE_BUFFER);

    if (asset == nullptr) {
        return false;
    }

    const off_t length =
        AAsset_getLength(asset);

    if (length <= 0 ||
        static_cast<std::uint64_t>(length) >
            256ULL * 1024ULL * 1024ULL) {
        AAsset_close(asset);
        return false;
    }

    std::vector<std::byte> bytes;

    try {
        bytes.resize(
            static_cast<std::size_t>(
                length));
    } catch (...) {
        AAsset_close(asset);
        return false;
    }

    const int read =
        AAsset_read(
            asset,
            bytes.data(),
            bytes.size());

    AAsset_close(asset);

    if (read < 0 ||
        static_cast<std::size_t>(read) !=
            bytes.size()) {
        return false;
    }

    const auto result =
        parseStaticMeshXzsm(
            std::span<const std::byte>(
                bytes.data(),
                bytes.size()),
            out);

    if (!result.success) {
        return false;
    }

    const std::string modelPath =
        path != nullptr
        ? path
        : "";

    if (modelPath.find("/weapons/") !=
        std::string::npos) {
        StaticMeshQualityMetrics metrics{};

        if (!passesViewmodelStaticMeshSanity(
                out,
                &metrics)) {
            __android_log_print(
                ANDROID_LOG_ERROR,
                kTag,
                "XZIEL_WEAPON_VIEWMODEL_REJECTED "
                "extent=%.3f coverage90=%.3f "
                "robust=%.3f/%.3f/%.3f "
                "batches=%u vertices=%u indices=%u",
                static_cast<double>(
                    metrics.longestExtent),
                static_cast<double>(
                    metrics.robustAxisCoverage90),
                static_cast<double>(
                    metrics.robustLongestExtent90),
                static_cast<double>(
                    metrics.robustSecondExtent90),
                static_cast<double>(
                    metrics.robustThirdExtent90),
                metrics.batchCount,
                metrics.vertexCount,
                metrics.indexCount);

            out = {};
            return false;
        }

        __android_log_print(
            ANDROID_LOG_INFO,
            kTag,
            "XZIEL_WEAPON_VIEWMODEL_SANITY_OK "
            "extent=%.3f coverage90=%.3f "
            "robust=%.3f/%.3f/%.3f "
            "batches=%u vertices=%u indices=%u",
            static_cast<double>(
                metrics.longestExtent),
            static_cast<double>(
                metrics.robustAxisCoverage90),
            static_cast<double>(
                metrics.robustLongestExtent90),
            static_cast<double>(
                metrics.robustSecondExtent90),
            static_cast<double>(
                metrics.robustThirdExtent90),
            metrics.batchCount,
            metrics.vertexCount,
            metrics.indexCount);
    }

    return true;
}

bool VulkanStaticMeshRenderer::createPipeline(
    AAssetManager* assetManager) noexcept {
    VkShaderModule vertex = VK_NULL_HANDLE;
    VkShaderModule fragment = VK_NULL_HANDLE;

    if (!createShaderModule(
            assetManager,
            "shaders/xziel_static_mesh.vert.spv",
            vertex) ||
        !createShaderModule(
            assetManager,
            "shaders/xziel_static_mesh.frag.spv",
            fragment)) {
        if (vertex != VK_NULL_HANDLE) {
            vkDestroyShaderModule(
                device_, vertex, nullptr);
        }
        if (fragment != VK_NULL_HANDLE) {
            vkDestroyShaderModule(
                device_, fragment, nullptr);
        }
        return false;
    }

    VkDescriptorSetLayoutBinding textureBinding{};
    textureBinding.binding = 0U;
    textureBinding.descriptorType =
        VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    textureBinding.descriptorCount = 1U;
    textureBinding.stageFlags =
        VK_SHADER_STAGE_FRAGMENT_BIT;

    VkDescriptorSetLayoutCreateInfo setInfo{
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO
    };
    setInfo.bindingCount = 1U;
    setInfo.pBindings = &textureBinding;

    if (!ok(
            vkCreateDescriptorSetLayout(
                device_,
                &setInfo,
                nullptr,
                &descriptorSetLayout_))) {
        vkDestroyShaderModule(
            device_, fragment, nullptr);
        vkDestroyShaderModule(
            device_, vertex, nullptr);
        return false;
    }

    VkPushConstantRange pushRange{};
    pushRange.stageFlags =
        VK_SHADER_STAGE_VERTEX_BIT |
        VK_SHADER_STAGE_FRAGMENT_BIT;
    pushRange.offset = 0U;
    pushRange.size =
        static_cast<std::uint32_t>(
            sizeof(PushConstants));

    VkPipelineLayoutCreateInfo layoutInfo{
        VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO
    };
    layoutInfo.setLayoutCount = 1U;
    layoutInfo.pSetLayouts =
        &descriptorSetLayout_;
    layoutInfo.pushConstantRangeCount = 1U;
    layoutInfo.pPushConstantRanges =
        &pushRange;

    if (!ok(
            vkCreatePipelineLayout(
                device_,
                &layoutInfo,
                nullptr,
                &pipelineLayout_))) {
        vkDestroyShaderModule(
            device_, fragment, nullptr);
        vkDestroyShaderModule(
            device_, vertex, nullptr);
        return false;
    }

    const std::array<VkPipelineShaderStageCreateInfo, 2>
        stages{{
            {
                VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                nullptr,
                0U,
                VK_SHADER_STAGE_VERTEX_BIT,
                vertex,
                "main",
                nullptr,
            },
            {
                VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,
                nullptr,
                0U,
                VK_SHADER_STAGE_FRAGMENT_BIT,
                fragment,
                "main",
                nullptr,
            },
        }};

    VkVertexInputBindingDescription binding{};
    binding.binding = 0U;
    binding.stride =
        sizeof(StaticMeshVertex);
    binding.inputRate =
        VK_VERTEX_INPUT_RATE_VERTEX;

    const std::array<
        VkVertexInputAttributeDescription,
        4> attributes{{
            {
                0U,
                0U,
                VK_FORMAT_R32G32B32_SFLOAT,
                static_cast<std::uint32_t>(
                    offsetof(
                        StaticMeshVertex,
                        x)),
            },
            {
                1U,
                0U,
                VK_FORMAT_R32G32B32_SFLOAT,
                static_cast<std::uint32_t>(
                    offsetof(
                        StaticMeshVertex,
                        nx)),
            },
            {
                2U,
                0U,
                VK_FORMAT_R32G32_SFLOAT,
                static_cast<std::uint32_t>(
                    offsetof(
                        StaticMeshVertex,
                        u)),
            },
            {
                3U,
                0U,
                VK_FORMAT_R8G8B8A8_UNORM,
                static_cast<std::uint32_t>(
                    offsetof(
                        StaticMeshVertex,
                        rgba)),
            },
        }};

    VkPipelineVertexInputStateCreateInfo vertexInput{
        VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO
    };
    vertexInput.vertexBindingDescriptionCount = 1U;
    vertexInput.pVertexBindingDescriptions =
        &binding;
    vertexInput.vertexAttributeDescriptionCount =
        static_cast<std::uint32_t>(
            attributes.size());
    vertexInput.pVertexAttributeDescriptions =
        attributes.data();

    VkPipelineInputAssemblyStateCreateInfo inputAssembly{
        VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO
    };
    inputAssembly.topology =
        VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;

    VkPipelineViewportStateCreateInfo viewportState{
        VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO
    };
    viewportState.viewportCount = 1U;
    viewportState.scissorCount = 1U;

    VkPipelineRasterizationStateCreateInfo raster{
        VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO
    };
    raster.polygonMode =
        VK_POLYGON_MODE_FILL;
    raster.cullMode =
        VK_CULL_MODE_NONE;
    raster.frontFace =
        VK_FRONT_FACE_COUNTER_CLOCKWISE;
    raster.lineWidth = 1.0f;

    VkPipelineMultisampleStateCreateInfo multisample{
        VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO
    };
    multisample.rasterizationSamples =
        VK_SAMPLE_COUNT_1_BIT;

    VkPipelineDepthStencilStateCreateInfo depthStencil{
        VK_STRUCTURE_TYPE_PIPELINE_DEPTH_STENCIL_STATE_CREATE_INFO
    };
    depthStencil.depthTestEnable = VK_TRUE;
    depthStencil.depthWriteEnable = VK_TRUE;
    depthStencil.depthCompareOp =
        VK_COMPARE_OP_LESS_OR_EQUAL;

    VkPipelineColorBlendAttachmentState attachment{};
    attachment.colorWriteMask =
        VK_COLOR_COMPONENT_R_BIT |
        VK_COLOR_COMPONENT_G_BIT |
        VK_COLOR_COMPONENT_B_BIT |
        VK_COLOR_COMPONENT_A_BIT;

    VkPipelineColorBlendStateCreateInfo blend{
        VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO
    };
    blend.attachmentCount = 1U;
    blend.pAttachments = &attachment;

    constexpr std::array<VkDynamicState, 2>
        dynamicStates{{
            VK_DYNAMIC_STATE_VIEWPORT,
            VK_DYNAMIC_STATE_SCISSOR,
        }};

    VkPipelineDynamicStateCreateInfo dynamic{
        VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO
    };
    dynamic.dynamicStateCount =
        static_cast<std::uint32_t>(
            dynamicStates.size());
    dynamic.pDynamicStates =
        dynamicStates.data();

    VkGraphicsPipelineCreateInfo info{
        VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO
    };
    info.stageCount =
        static_cast<std::uint32_t>(
            stages.size());
    info.pStages = stages.data();
    info.pVertexInputState = &vertexInput;
    info.pInputAssemblyState = &inputAssembly;
    info.pViewportState = &viewportState;
    info.pRasterizationState = &raster;
    info.pMultisampleState = &multisample;
    info.pDepthStencilState = &depthStencil;
    info.pColorBlendState = &blend;
    info.pDynamicState = &dynamic;
    info.layout = pipelineLayout_;
    info.renderPass = renderPass_;
    info.subpass = 0U;

    const VkResult result =
        vkCreateGraphicsPipelines(
            device_,
            VK_NULL_HANDLE,
            1U,
            &info,
            nullptr,
            &pipeline_);

    vkDestroyShaderModule(
        device_, fragment, nullptr);
    vkDestroyShaderModule(
        device_, vertex, nullptr);

    return ok(result);
}

bool VulkanStaticMeshRenderer::createBuffer(
    VkDeviceSize size,
    VkBufferUsageFlags usage,
    VkMemoryPropertyFlags memoryFlags,
    VkBuffer& buffer,
    VkDeviceMemory& memory) noexcept {
    if (size == 0U) {
        return false;
    }

    VkBufferCreateInfo info{
        VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO
    };
    info.size = size;
    info.usage = usage;
    info.sharingMode =
        VK_SHARING_MODE_EXCLUSIVE;

    if (!ok(
            vkCreateBuffer(
                device_,
                &info,
                nullptr,
                &buffer))) {
        return false;
    }

    VkMemoryRequirements requirements{};
    vkGetBufferMemoryRequirements(
        device_,
        buffer,
        &requirements);

    std::uint32_t typeIndex = 0U;

    if (!findMemoryType(
            requirements.memoryTypeBits,
            memoryFlags,
            typeIndex)) {
        vkDestroyBuffer(
            device_, buffer, nullptr);
        buffer = VK_NULL_HANDLE;
        return false;
    }

    VkMemoryAllocateInfo allocation{
        VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO
    };
    allocation.allocationSize =
        requirements.size;
    allocation.memoryTypeIndex =
        typeIndex;

    if (!ok(
            vkAllocateMemory(
                device_,
                &allocation,
                nullptr,
                &memory))) {
        vkDestroyBuffer(
            device_, buffer, nullptr);
        buffer = VK_NULL_HANDLE;
        return false;
    }

    if (!ok(
            vkBindBufferMemory(
                device_,
                buffer,
                memory,
                0U))) {
        vkFreeMemory(
            device_, memory, nullptr);
        vkDestroyBuffer(
            device_, buffer, nullptr);
        memory = VK_NULL_HANDLE;
        buffer = VK_NULL_HANDLE;
        return false;
    }

    return true;
}

bool VulkanStaticMeshRenderer::uploadBatch(
    const StaticMeshBatch& batch,
    std::uint32_t textureIndex,
    GpuBatch& out) noexcept {
    if (batch.vertices.empty() ||
        batch.indices.empty()) {
        return false;
    }

    const VkDeviceSize vertexBytes =
        batch.vertices.size() *
        sizeof(StaticMeshVertex);

    const VkDeviceSize indexBytes =
        batch.indices.size() *
        sizeof(std::uint16_t);

    const auto hostFlags =
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
        VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;

    if (!createBuffer(
            vertexBytes,
            VK_BUFFER_USAGE_VERTEX_BUFFER_BIT,
            hostFlags,
            out.vertexBuffer,
            out.vertexMemory) ||
        !createBuffer(
            indexBytes,
            VK_BUFFER_USAGE_INDEX_BUFFER_BIT,
            hostFlags,
            out.indexBuffer,
            out.indexMemory)) {
        destroyBatch(out);
        return false;
    }

    void* mapped = nullptr;

    if (!ok(
            vkMapMemory(
                device_,
                out.vertexMemory,
                0U,
                vertexBytes,
                0U,
                &mapped))) {
        destroyBatch(out);
        return false;
    }

    std::memcpy(
        mapped,
        batch.vertices.data(),
        static_cast<std::size_t>(
            vertexBytes));

    vkUnmapMemory(
        device_,
        out.vertexMemory);

    mapped = nullptr;

    if (!ok(
            vkMapMemory(
                device_,
                out.indexMemory,
                0U,
                indexBytes,
                0U,
                &mapped))) {
        destroyBatch(out);
        return false;
    }

    std::memcpy(
        mapped,
        batch.indices.data(),
        static_cast<std::size_t>(
            indexBytes));

    vkUnmapMemory(
        device_,
        out.indexMemory);

    out.indexCount =
        static_cast<std::uint32_t>(
            batch.indices.size());
    out.textureIndex =
        textureIndex;
    out.bounds =
        batch.bounds;

    return true;
}

bool VulkanStaticMeshRenderer::createTexture(
    AAssetManager* assetManager,
    const std::string& assetPath,
    GpuTexture& out) noexcept {
    AAsset* asset =
        AAssetManager_open(
            assetManager,
            assetPath.c_str(),
            AASSET_MODE_STREAMING);

    if (asset == nullptr) {
        return false;
    }

    AImageDecoder* decoder = nullptr;

    const int createResult =
        AImageDecoder_createFromAAsset(
            asset,
            &decoder);

    if (createResult !=
            ANDROID_IMAGE_DECODER_SUCCESS ||
        decoder == nullptr) {
        AAsset_close(asset);
        return false;
    }

    (void) AImageDecoder_setAndroidBitmapFormat(
        decoder,
        ANDROID_BITMAP_FORMAT_RGBA_8888);

    const AImageDecoderHeaderInfo* header =
        AImageDecoder_getHeaderInfo(
            decoder);

    const int32_t width =
        AImageDecoderHeaderInfo_getWidth(
            header);

    const int32_t height =
        AImageDecoderHeaderInfo_getHeight(
            header);

    const std::size_t stride =
        AImageDecoder_getMinimumStride(
            decoder);

    if (width <= 0 ||
        height <= 0 ||
        stride <
            static_cast<std::size_t>(width) * 4U) {
        AImageDecoder_delete(decoder);
        AAsset_close(asset);
        return false;
    }

    const std::size_t pixelBytes =
        stride *
        static_cast<std::size_t>(
            height);

    std::vector<std::byte> pixels;

    try {
        pixels.resize(pixelBytes);
    } catch (...) {
        AImageDecoder_delete(decoder);
        AAsset_close(asset);
        return false;
    }

    const int decodeResult =
        AImageDecoder_decodeImage(
            decoder,
            pixels.data(),
            stride,
            pixels.size());

    AImageDecoder_delete(decoder);
    AAsset_close(asset);

    if (decodeResult !=
        ANDROID_IMAGE_DECODER_SUCCESS) {
        return false;
    }

    VkBuffer staging = VK_NULL_HANDLE;
    VkDeviceMemory stagingMemory =
        VK_NULL_HANDLE;

    if (!createBuffer(
            pixelBytes,
            VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
            staging,
            stagingMemory)) {
        return false;
    }

    void* mapped = nullptr;

    if (!ok(
            vkMapMemory(
                device_,
                stagingMemory,
                0U,
                pixelBytes,
                0U,
                &mapped))) {
        vkFreeMemory(
            device_, stagingMemory, nullptr);
        vkDestroyBuffer(
            device_, staging, nullptr);
        return false;
    }

    std::memcpy(
        mapped,
        pixels.data(),
        pixelBytes);

    vkUnmapMemory(
        device_,
        stagingMemory);

    VkImageCreateInfo imageInfo{
        VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO
    };
    imageInfo.imageType =
        VK_IMAGE_TYPE_2D;
    imageInfo.extent.width =
        static_cast<std::uint32_t>(width);
    imageInfo.extent.height =
        static_cast<std::uint32_t>(height);
    imageInfo.extent.depth = 1U;
    imageInfo.mipLevels = 1U;
    imageInfo.arrayLayers = 1U;
    imageInfo.format =
        VK_FORMAT_R8G8B8A8_SRGB;
    imageInfo.tiling =
        VK_IMAGE_TILING_OPTIMAL;
    imageInfo.initialLayout =
        VK_IMAGE_LAYOUT_UNDEFINED;
    imageInfo.usage =
        VK_IMAGE_USAGE_TRANSFER_DST_BIT |
        VK_IMAGE_USAGE_SAMPLED_BIT;
    imageInfo.samples =
        VK_SAMPLE_COUNT_1_BIT;
    imageInfo.sharingMode =
        VK_SHARING_MODE_EXCLUSIVE;

    if (!ok(
            vkCreateImage(
                device_,
                &imageInfo,
                nullptr,
                &out.image))) {
        vkFreeMemory(
            device_, stagingMemory, nullptr);
        vkDestroyBuffer(
            device_, staging, nullptr);
        return false;
    }

    VkMemoryRequirements requirements{};
    vkGetImageMemoryRequirements(
        device_,
        out.image,
        &requirements);

    std::uint32_t memoryType = 0U;

    if (!findMemoryType(
            requirements.memoryTypeBits,
            VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
            memoryType)) {
        vkFreeMemory(
            device_, stagingMemory, nullptr);
        vkDestroyBuffer(
            device_, staging, nullptr);
        destroyTexture(out);
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
                &out.memory)) ||
        !ok(
            vkBindImageMemory(
                device_,
                out.image,
                out.memory,
                0U))) {
        vkFreeMemory(
            device_, stagingMemory, nullptr);
        vkDestroyBuffer(
            device_, staging, nullptr);
        destroyTexture(out);
        return false;
    }

    VkCommandBuffer command =
        beginUploadCommands();

    if (command == VK_NULL_HANDLE) {
        vkFreeMemory(
            device_, stagingMemory, nullptr);
        vkDestroyBuffer(
            device_, staging, nullptr);
        destroyTexture(out);
        return false;
    }

    VkImageMemoryBarrier toTransfer{
        VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER
    };
    toTransfer.oldLayout =
        VK_IMAGE_LAYOUT_UNDEFINED;
    toTransfer.newLayout =
        VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    toTransfer.srcQueueFamilyIndex =
        VK_QUEUE_FAMILY_IGNORED;
    toTransfer.dstQueueFamilyIndex =
        VK_QUEUE_FAMILY_IGNORED;
    toTransfer.image = out.image;
    toTransfer.subresourceRange.aspectMask =
        VK_IMAGE_ASPECT_COLOR_BIT;
    toTransfer.subresourceRange.baseMipLevel = 0U;
    toTransfer.subresourceRange.levelCount = 1U;
    toTransfer.subresourceRange.baseArrayLayer = 0U;
    toTransfer.subresourceRange.layerCount = 1U;
    toTransfer.srcAccessMask = 0U;
    toTransfer.dstAccessMask =
        VK_ACCESS_TRANSFER_WRITE_BIT;

    vkCmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        0U,
        0U,
        nullptr,
        0U,
        nullptr,
        1U,
        &toTransfer);

    VkBufferImageCopy copy{};
    copy.bufferOffset = 0U;
    copy.bufferRowLength =
        static_cast<std::uint32_t>(
            stride / 4U);
    copy.bufferImageHeight =
        static_cast<std::uint32_t>(
            height);
    copy.imageSubresource.aspectMask =
        VK_IMAGE_ASPECT_COLOR_BIT;
    copy.imageSubresource.mipLevel = 0U;
    copy.imageSubresource.baseArrayLayer = 0U;
    copy.imageSubresource.layerCount = 1U;
    copy.imageExtent = {
        static_cast<std::uint32_t>(width),
        static_cast<std::uint32_t>(height),
        1U,
    };

    vkCmdCopyBufferToImage(
        command,
        staging,
        out.image,
        VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
        1U,
        &copy);

    VkImageMemoryBarrier toShader =
        toTransfer;
    toShader.oldLayout =
        VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    toShader.newLayout =
        VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    toShader.srcAccessMask =
        VK_ACCESS_TRANSFER_WRITE_BIT;
    toShader.dstAccessMask =
        VK_ACCESS_SHADER_READ_BIT;

    vkCmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT,
        0U,
        0U,
        nullptr,
        0U,
        nullptr,
        1U,
        &toShader);

    const bool uploadOk =
        endUploadCommands(command);

    vkFreeMemory(
        device_, stagingMemory, nullptr);
    vkDestroyBuffer(
        device_, staging, nullptr);

    if (!uploadOk) {
        destroyTexture(out);
        return false;
    }

    VkImageViewCreateInfo viewInfo{
        VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO
    };
    viewInfo.image = out.image;
    viewInfo.viewType =
        VK_IMAGE_VIEW_TYPE_2D;
    viewInfo.format =
        VK_FORMAT_R8G8B8A8_SRGB;
    viewInfo.subresourceRange.aspectMask =
        VK_IMAGE_ASPECT_COLOR_BIT;
    viewInfo.subresourceRange.baseMipLevel = 0U;
    viewInfo.subresourceRange.levelCount = 1U;
    viewInfo.subresourceRange.baseArrayLayer = 0U;
    viewInfo.subresourceRange.layerCount = 1U;

    if (!ok(
            vkCreateImageView(
                device_,
                &viewInfo,
                nullptr,
                &out.view))) {
        destroyTexture(out);
        return false;
    }

    VkSamplerCreateInfo samplerInfo{
        VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO
    };
    samplerInfo.magFilter =
        VK_FILTER_LINEAR;
    samplerInfo.minFilter =
        VK_FILTER_LINEAR;
    // The church and viewmodel both use atlas/non-tiling UVs. CLAMP prevents
    // bilinear samples on U/V edges from wrapping into unrelated atlas pixels.
    samplerInfo.addressModeU =
        VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    samplerInfo.addressModeV =
        VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    samplerInfo.addressModeW =
        VK_SAMPLER_ADDRESS_MODE_CLAMP_TO_EDGE;
    samplerInfo.anisotropyEnable =
        samplerAnisotropyEnabled_
        ? VK_TRUE
        : VK_FALSE;
    samplerInfo.maxAnisotropy =
        maxSamplerAnisotropy_;
    samplerInfo.borderColor =
        VK_BORDER_COLOR_INT_OPAQUE_BLACK;
    samplerInfo.unnormalizedCoordinates =
        VK_FALSE;
    samplerInfo.mipmapMode =
        VK_SAMPLER_MIPMAP_MODE_LINEAR;
    samplerInfo.minLod = 0.0f;
    samplerInfo.maxLod = 0.0f;

    if (!ok(
            vkCreateSampler(
                device_,
                &samplerInfo,
                nullptr,
                &out.sampler))) {
        destroyTexture(out);
        return false;
    }

    VkDescriptorSetAllocateInfo setAllocation{
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO
    };
    setAllocation.descriptorPool =
        descriptorPool_;
    setAllocation.descriptorSetCount = 1U;
    setAllocation.pSetLayouts =
        &descriptorSetLayout_;

    if (!ok(
            vkAllocateDescriptorSets(
                device_,
                &setAllocation,
                &out.descriptorSet))) {
        destroyTexture(out);
        return false;
    }

    VkDescriptorImageInfo imageDescriptor{};
    imageDescriptor.sampler =
        out.sampler;
    imageDescriptor.imageView =
        out.view;
    imageDescriptor.imageLayout =
        VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;

    VkWriteDescriptorSet write{
        VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET
    };
    write.dstSet =
        out.descriptorSet;
    write.dstBinding = 0U;
    write.descriptorCount = 1U;
    write.descriptorType =
        VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    write.pImageInfo =
        &imageDescriptor;

    vkUpdateDescriptorSets(
        device_,
        1U,
        &write,
        0U,
        nullptr);

    out.assetPath =
        assetPath;
    out.width =
        static_cast<std::uint32_t>(
            width);
    out.height =
        static_cast<std::uint32_t>(
            height);

    return true;
}

bool VulkanStaticMeshRenderer::createShaderModule(
    AAssetManager* assetManager,
    const char* path,
    VkShaderModule& out) noexcept {
    out = VK_NULL_HANDLE;

    AAsset* asset =
        AAssetManager_open(
            assetManager,
            path,
            AASSET_MODE_BUFFER);

    if (asset == nullptr) {
        return false;
    }

    const off_t length =
        AAsset_getLength(asset);

    if (length <= 0 ||
        (length % 4) != 0) {
        AAsset_close(asset);
        return false;
    }

    std::vector<std::uint32_t> words;

    try {
        words.resize(
            static_cast<std::size_t>(
                length) / 4U);
    } catch (...) {
        AAsset_close(asset);
        return false;
    }

    const int read =
        AAsset_read(
            asset,
            words.data(),
            static_cast<std::size_t>(
                length));

    AAsset_close(asset);

    if (read < 0 ||
        static_cast<off_t>(read) !=
            length) {
        return false;
    }

    VkShaderModuleCreateInfo info{
        VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO
    };
    info.codeSize =
        static_cast<std::size_t>(
            length);
    info.pCode =
        words.data();

    return ok(
        vkCreateShaderModule(
            device_,
            &info,
            nullptr,
            &out));
}

bool VulkanStaticMeshRenderer::findMemoryType(
    std::uint32_t typeBits,
    VkMemoryPropertyFlags required,
    std::uint32_t& outIndex) const noexcept {
    VkPhysicalDeviceMemoryProperties properties{};
    vkGetPhysicalDeviceMemoryProperties(
        physicalDevice_,
        &properties);

    for (std::uint32_t i = 0U;
         i < properties.memoryTypeCount;
         ++i) {
        if ((typeBits & (1U << i)) != 0U &&
            (properties.memoryTypes[i].
                 propertyFlags &
             required) == required) {
            outIndex = i;
            return true;
        }
    }

    return false;
}

VkCommandBuffer
VulkanStaticMeshRenderer::beginUploadCommands() noexcept {
    VkCommandBufferAllocateInfo allocation{
        VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO
    };
    allocation.commandPool =
        commandPool_;
    allocation.level =
        VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    allocation.commandBufferCount = 1U;

    VkCommandBuffer command =
        VK_NULL_HANDLE;

    if (!ok(
            vkAllocateCommandBuffers(
                device_,
                &allocation,
                &command))) {
        return VK_NULL_HANDLE;
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
        vkFreeCommandBuffers(
            device_,
            commandPool_,
            1U,
            &command);
        return VK_NULL_HANDLE;
    }

    return command;
}

bool VulkanStaticMeshRenderer::endUploadCommands(
    VkCommandBuffer command) noexcept {
    if (command == VK_NULL_HANDLE) {
        return false;
    }

    if (!ok(
            vkEndCommandBuffer(
                command))) {
        vkFreeCommandBuffers(
            device_,
            commandPool_,
            1U,
            &command);
        return false;
    }

    VkSubmitInfo submit{
        VK_STRUCTURE_TYPE_SUBMIT_INFO
    };
    submit.commandBufferCount = 1U;
    submit.pCommandBuffers =
        &command;

    const bool submitted =
        ok(
            vkQueueSubmit(
                graphicsQueue_,
                1U,
                &submit,
                VK_NULL_HANDLE)) &&
        ok(
            vkQueueWaitIdle(
                graphicsQueue_));

    vkFreeCommandBuffers(
        device_,
        commandPool_,
        1U,
        &command);

    return submitted;
}

void VulkanStaticMeshRenderer::destroyTexture(
    GpuTexture& texture) noexcept {
    if (device_ == VK_NULL_HANDLE) {
        texture = {};
        return;
    }

    if (texture.sampler != VK_NULL_HANDLE) {
        vkDestroySampler(
            device_,
            texture.sampler,
            nullptr);
    }

    if (texture.view != VK_NULL_HANDLE) {
        vkDestroyImageView(
            device_,
            texture.view,
            nullptr);
    }

    if (texture.image != VK_NULL_HANDLE) {
        vkDestroyImage(
            device_,
            texture.image,
            nullptr);
    }

    if (texture.memory != VK_NULL_HANDLE) {
        vkFreeMemory(
            device_,
            texture.memory,
            nullptr);
    }

    texture = {};
}

void VulkanStaticMeshRenderer::destroyBatch(
    GpuBatch& batch) noexcept {
    if (device_ == VK_NULL_HANDLE) {
        batch = {};
        return;
    }

    if (batch.indexBuffer != VK_NULL_HANDLE) {
        vkDestroyBuffer(
            device_,
            batch.indexBuffer,
            nullptr);
    }

    if (batch.indexMemory != VK_NULL_HANDLE) {
        vkFreeMemory(
            device_,
            batch.indexMemory,
            nullptr);
    }

    if (batch.vertexBuffer != VK_NULL_HANDLE) {
        vkDestroyBuffer(
            device_,
            batch.vertexBuffer,
            nullptr);
    }

    if (batch.vertexMemory != VK_NULL_HANDLE) {
        vkFreeMemory(
            device_,
            batch.vertexMemory,
            nullptr);
    }

    batch = {};
}

} // namespace xziel::android
