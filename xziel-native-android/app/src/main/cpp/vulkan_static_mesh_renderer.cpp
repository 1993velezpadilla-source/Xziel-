#include "vulkan_static_mesh_renderer.hpp"

#include "xziel/texture_container.hpp"
#include "xziel/streaming.hpp"
#include "xziel/sanctum.hpp"

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
#include <unordered_set>
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
    const std::string& exportedName,
    const char* extension) {
    std::string path = exportedName;

    if (path.ends_with(".png")) {
        path.resize(
            path.size() - 4U);
    } else if (path.ends_with(".ktx2")) {
        path.resize(
            path.size() - 5U);
    }

    path += extension;
    return path;
}

[[nodiscard]] std::uint64_t
chooseTextureResidentBudget(
    VkPhysicalDevice physicalDevice,
    VkPhysicalDeviceType deviceType) noexcept {
    constexpr std::uint64_t kMiB =
        1024ULL * 1024ULL;
    constexpr std::uint64_t kMinimum =
        96ULL * kMiB;
    constexpr std::uint64_t kMaximum =
        384ULL * kMiB;

    if (deviceType ==
        VK_PHYSICAL_DEVICE_TYPE_CPU) {
        return 128ULL * kMiB;
    }

    VkPhysicalDeviceMemoryProperties memory{};
    vkGetPhysicalDeviceMemoryProperties(
        physicalDevice,
        &memory);

    std::uint64_t largestDeviceLocalHeap = 0U;

    for (std::uint32_t i = 0U;
         i < memory.memoryHeapCount;
         ++i) {
        if ((memory.memoryHeaps[i].flags &
             VK_MEMORY_HEAP_DEVICE_LOCAL_BIT) == 0U) {
            continue;
        }

        largestDeviceLocalHeap =
            std::max<std::uint64_t>(
                largestDeviceLocalHeap,
                static_cast<std::uint64_t>(
                    memory.memoryHeaps[i].size));
    }

    if (largestDeviceLocalHeap == 0U) {
        return 128ULL * kMiB;
    }

    return std::clamp<std::uint64_t>(
        largestDeviceLocalHeap / 8U,
        kMinimum,
        kMaximum);
}

[[nodiscard]] bool assetExists(
    AAssetManager* assetManager,
    const std::string& path) noexcept {
    if (assetManager == nullptr) {
        return false;
    }

    AAsset* asset =
        AAssetManager_open(
            assetManager,
            path.c_str(),
            AASSET_MODE_UNKNOWN);

    if (asset == nullptr) {
        return false;
    }

    AAsset_close(asset);
    return true;
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
    VkSampleCountFlagBits sampleCount,
    AAssetManager* assetManager,
    const char* modelAssetPath) noexcept {
    shutdown();

    if (physicalDevice == VK_NULL_HANDLE ||
        device == VK_NULL_HANDLE ||
        graphicsQueue == VK_NULL_HANDLE ||
        graphicsQueueFamily == UINT32_MAX ||
        commandPool == VK_NULL_HANDLE ||
        renderPass == VK_NULL_HANDLE ||
        sampleCount == 0U ||
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
    astcLdrSupported_ =
        deviceFeatures.textureCompressionASTC_LDR ==
        VK_TRUE;

    maxSamplerAnisotropy_ =
        samplerAnisotropyEnabled_
        ? std::clamp(
              deviceProperties.limits.maxSamplerAnisotropy,
              1.0f,
              8.0f)
        : 1.0f;

    // CPU Vulkan implementations such as CI llvmpipe emulate ASTC decode.
    // Huge all-at-once submits can serialize badly there. Real mobile GPUs
    // keep a much larger batch to minimize queue waits during startup.
    uploadBatchCommandLimit_ =
        deviceProperties.deviceType ==
            VK_PHYSICAL_DEVICE_TYPE_CPU
        ? 2U
        : 16U;

    textureResidentBudgetBytes_ =
        chooseTextureResidentBudget(
            physicalDevice_,
            deviceProperties.deviceType);
    textureResidentBytes_ = 0U;
    textureDegradedCount_ = 0U;

    __android_log_print(
        ANDROID_LOG_INFO,
        kTag,
        "XZIEL_STATIC_TEXTURE_CAPS astc=%d aniso=%.1f upload_batch_commands=%u texture_budget_mb=%.1f",
        astcLdrSupported_ ? 1 : 0,
        static_cast<double>(
            maxSamplerAnisotropy_),
        static_cast<unsigned int>(
            uploadBatchCommandLimit_),
        static_cast<double>(
            textureResidentBudgetBytes_) /
            (1024.0 * 1024.0));

    graphicsQueue_ = graphicsQueue;
    graphicsQueueFamily_ = graphicsQueueFamily;
    commandPool_ = commandPool;
    renderPass_ = renderPass;
    sampleCount_ = sampleCount;

    StaticMeshAsset asset{};
    if (!loadModel(
            assetManager,
            modelAssetPath,
            asset)) {
        shutdown();
        return false;
    }

    const std::string modelPath =
        modelAssetPath != nullptr
        ? modelAssetPath
        : "";

    streamGraphReady_ =
        modelPath.find("/sanctum/") !=
            std::string::npos &&
        configureSanctumStreamingGraph(
            streamGraph_);

    textureMipResidency_.reset();
    streamCellBounds_ = {};
    streamDecisionCount_ = 0U;
    streamPlanFrame_ = 0U;
    lastLoggedStreamCell_ = 0U;
    streamCellCandidate_ = 0U;
    streamCellStableFrames_ = 0U;
    streamCullingActive_ = false;
    streamCullLogged_ = false;
    streamCellCandidate_ = 0U;
    streamCellStableFrames_ = 0U;
    streamCullingActive_ = false;
    streamCullLogged_ = false;

    // Read KTX2 payloads on bounded worker threads while the render thread
    // creates pipelines/descriptors. Vulkan object creation and queue submits
    // stay on this thread; only APK asset I/O moves off-thread.
    asyncPrefetchQueued_ = 0U;

    if (astcLdrSupported_) {
        constexpr std::uint64_t kMiB =
            1024ULL * 1024ULL;

        const std::uint64_t prefetchBudget =
            std::clamp<std::uint64_t>(
                textureResidentBudgetBytes_ / 4U,
                16ULL * kMiB,
                96ULL * kMiB);

        const std::uint32_t workerCount =
            deviceProperties.deviceType ==
                VK_PHYSICAL_DEVICE_TYPE_CPU
            ? 1U
            : 2U;

        if (assetStreamer_.start(
                assetManager,
                workerCount,
                prefetchBudget)) {
            std::unordered_set<std::string>
                queuedPaths;

            const auto queueTexture =
                [&](const std::string& exportedName) {
                    if (exportedName.empty()) {
                        return;
                    }

                    const std::string path =
                        textureAssetPath(
                            exportedName,
                            ".ktx2");

                    if (!assetExists(
                            assetManager,
                            path) ||
                        !queuedPaths.insert(path).second) {
                        return;
                    }

                    if (assetStreamer_.enqueue(path)) {
                        ++asyncPrefetchQueued_;
                    }
                };

            for (const auto& batch : asset.batches) {
                queueTexture(batch.textureName);

                if (!batch.pbrEnabled()) {
                    continue;
                }

                queueTexture(
                    batch.pbr.normalTextureName);
                queueTexture(
                    batch.pbr.ormTextureName);
                queueTexture(
                    batch.pbr.emissiveTextureName);
            }

            __android_log_print(
                ANDROID_LOG_INFO,
                kTag,
                "XZIEL_ASYNC_ASTC_PREFETCH_READY workers=%u queued=%u buffer_mb=%.1f",
                static_cast<unsigned int>(
                    workerCount),
                static_cast<unsigned int>(
                    asyncPrefetchQueued_),
                static_cast<double>(
                    prefetchBudget) /
                    (1024.0 * 1024.0));
        }
    }

    if (!createPipeline(assetManager)) {
        shutdown();
        return false;
    }

    VkDescriptorPoolSize poolSize{};
    poolSize.type =
        VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
    const std::uint32_t materialCount =
        static_cast<std::uint32_t>(
            std::max<std::size_t>(
                asset.batches.size(),
                1U));

    poolSize.descriptorCount =
        materialCount *
        4U *
        kDescriptorFrames;

    VkDescriptorPoolCreateInfo poolInfo{
        VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO
    };
    poolInfo.maxSets =
        materialCount *
        kDescriptorFrames;
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

    std::vector<std::uint32_t>
        batchMaterialIndices;

    std::uint32_t pbrMaterialCount = 0U;
    std::uint32_t normalMapCount = 0U;
    std::uint32_t ormMapCount = 0U;
    std::uint32_t emissiveMapCount = 0U;

    const auto loadTexture =
        [&](const std::string& exportedName,
            bool srgb,
            std::uint32_t& outIndex) noexcept {
            if (exportedName.empty()) {
                return false;
            }

            const std::string cacheKey =
                exportedName +
                (srgb ? "#srgb" : "#linear");

            const auto found =
                textureIndices.find(cacheKey);

            if (found != textureIndices.end()) {
                outIndex = found->second;
                return true;
            }

            GpuTexture texture{};
            if (!createTexture(
                    assetManager,
                    exportedName,
                    srgb,
                    texture)) {
                return false;
            }

            texture.streamResourceId =
                streamResourceId(
                    cacheKey);

            if (texture.sourceMipLevels > 0U &&
                texture.sourceMipLevels <=
                    kMaxStreamedTextureMips) {
                TextureMipChainDesc desc{};
                desc.id =
                    texture.streamResourceId;
                desc.mipCount =
                    texture.sourceMipLevels;
                desc.mipBytes =
                    texture.sourceMipBytes;
                desc.residentBaseMip =
                    std::min(
                        texture.residentBaseMip,
                        desc.mipCount - 1U);
                desc.requestedBaseMip =
                    desc.residentBaseMip;
                desc.pinned = false;

                if (!textureMipResidency_.
                        registerTexture(
                            desc,
                            0U)) {
                    destroyTexture(texture);
                    return false;
                }
            }

            outIndex =
                static_cast<std::uint32_t>(
                    textures_.size());

            textures_.emplace_back(
                std::move(texture));
            textureIndices.emplace(
                cacheKey,
                outIndex);
            return true;
        };

    const auto bindStreamTexture =
        [&](SanctumZone zone,
            std::uint32_t textureIndex) noexcept {
            if (!streamGraphReady_ ||
                zone == SanctumZone::Unknown ||
                textureIndex >= textures_.size()) {
                return;
            }

            const auto& texture =
                textures_[textureIndex];

            std::uint64_t bytes =
                texture.residentPayloadBytes;

            if (bytes == 0U) {
                bytes =
                    texture.allocationBytes;
            }

            if (bytes == 0U) {
                const std::uint64_t pixels =
                    static_cast<std::uint64_t>(
                        texture.width) *
                    static_cast<std::uint64_t>(
                        texture.height);

                bytes =
                    std::max<std::uint64_t>(
                        1U,
                        pixels * 4U);
            }

            (void) streamGraph_.bindResource({
                .cellId =
                    static_cast<std::uint32_t>(
                        zone),
                .resourceId =
                    texture.streamResourceId,
                .kind =
                    StreamResourceKind::Texture,
                .bytes = bytes,
                .pinned = false,
            });
        };

    try {
        batchMaterialIndices.reserve(
            asset.batches.size());
        materials_.reserve(
            asset.batches.size());

        for (const auto& batch : asset.batches) {
            GpuMaterial material{};

            const auto streamZone =
                streamGraphReady_
                ? sanctumZoneForAssetName(
                      batch.textureName)
                : SanctumZone::Unknown;

            if (!loadTexture(
                    batch.textureName,
                    true,
                    material.albedoTextureIndex)) {
                logError(
                    "static mesh albedo texture load failed");
                shutdown();
                return false;
            }

            material.streamResourceId =
                textures_[
                    material.albedoTextureIndex].
                        streamResourceId;

            bindStreamTexture(
                streamZone,
                material.albedoTextureIndex);

            material.normalTextureIndex =
                material.albedoTextureIndex;
            material.ormTextureIndex =
                material.albedoTextureIndex;
            material.emissiveTextureIndex =
                material.albedoTextureIndex;

            material.baseColorFactor =
                batch.pbr.baseColorFactor;
            material.metallicFactor =
                batch.pbr.metallicFactor;
            material.roughnessFactor =
                batch.pbr.roughnessFactor;
            material.emissiveFactor =
                batch.pbr.emissiveFactor;
            material.normalScale =
                batch.pbr.normalScale;
            material.occlusionStrength =
                batch.pbr.occlusionStrength;
            material.pbrEnabled =
                batch.pbrEnabled();

            if (material.pbrEnabled &&
                !batch.pbr.normalTextureName.empty()) {
                if (!loadTexture(
                        batch.pbr.normalTextureName,
                        false,
                        material.normalTextureIndex)) {
                    logError(
                        "static mesh normal texture load failed");
                    shutdown();
                    return false;
                }
                bindStreamTexture(
                    streamZone,
                    material.normalTextureIndex);
                material.hasNormalTexture = true;
                ++normalMapCount;
            }

            if (material.pbrEnabled &&
                !batch.pbr.ormTextureName.empty()) {
                if (!loadTexture(
                        batch.pbr.ormTextureName,
                        false,
                        material.ormTextureIndex)) {
                    logError(
                        "static mesh ORM texture load failed");
                    shutdown();
                    return false;
                }
                bindStreamTexture(
                    streamZone,
                    material.ormTextureIndex);
                material.hasOrmTexture = true;
                ++ormMapCount;
            }

            if (material.pbrEnabled &&
                !batch.pbr.emissiveTextureName.empty()) {
                if (!loadTexture(
                        batch.pbr.emissiveTextureName,
                        true,
                        material.emissiveTextureIndex)) {
                    logError(
                        "static mesh emissive texture load failed");
                    shutdown();
                    return false;
                }
                bindStreamTexture(
                    streamZone,
                    material.emissiveTextureIndex);
                material.hasEmissiveTexture = true;
                ++emissiveMapCount;
            }

            if (!createMaterialDescriptor(
                    material)) {
                logError(
                    "static mesh PBR material descriptor failed");
                shutdown();
                return false;
            }

            if (material.pbrEnabled) {
                ++pbrMaterialCount;
            }

            const std::uint32_t materialIndex =
                static_cast<std::uint32_t>(
                    materials_.size());

            materials_.emplace_back(
                std::move(material));
            batchMaterialIndices.push_back(
                materialIndex);
        }
    } catch (...) {
        logError(
            "static mesh GPU material allocation failed");
        shutdown();
        return false;
    }

    if (asyncPrefetchQueued_ > 0U) {
        const auto streamStats =
            assetStreamer_.stats();

        __android_log_print(
            ANDROID_LOG_INFO,
            kTag,
            "XZIEL_ASYNC_ASTC_PREFETCH_DONE queued=%llu completed=%llu failed=%llu consumed=%llu bytes_mb=%.2f pending=%u",
            static_cast<unsigned long long>(
                streamStats.queued),
            static_cast<unsigned long long>(
                streamStats.completed),
            static_cast<unsigned long long>(
                streamStats.failed),
            static_cast<unsigned long long>(
                streamStats.consumed),
            static_cast<double>(
                streamStats.bytesRead) /
                (1024.0 * 1024.0),
            static_cast<unsigned int>(
                streamStats.pending));
    }

    if (streamGraphReady_ &&
        assetStreamer_.running()) {
        __android_log_print(
            ANDROID_LOG_INFO,
            kTag,
            "XZIEL_RUNTIME_ASSET_STREAMER_READY workers=1+ persistent=1");
    } else {
        assetStreamer_.stop();
    }

    asyncPrefetchQueued_ = 0U;

    if (!flushPendingUploads()) {
        logError(
            "static mesh batched texture upload failed");
        shutdown();
        return false;
    }

    const auto mipRegistryStats =
        textureMipResidency_.stats();

    __android_log_print(
        ANDROID_LOG_INFO,
        kTag,
        "XZIEL_TEXTURE_RESIDENCY_REGISTRY textures=%u degraded=%u resident_mb=%.2f requested_mb=%.2f",
        static_cast<unsigned int>(
            mipRegistryStats.textureCount),
        static_cast<unsigned int>(
            mipRegistryStats.
                degradedTextureCount),
        static_cast<double>(
            mipRegistryStats.
                residentBytes) /
            (1024.0 * 1024.0),
        static_cast<double>(
            mipRegistryStats.
                requestedBytes) /
            (1024.0 * 1024.0));

    __android_log_print(
        ANDROID_LOG_INFO,
        kTag,
        "XZIEL_PBR_MATERIALS_READY materials=%u pbr=%u legacy=%u normal=%u orm=%u emissive=%u textures=%u",
        static_cast<unsigned int>(materials_.size()),
        static_cast<unsigned int>(pbrMaterialCount),
        static_cast<unsigned int>(materials_.size() - pbrMaterialCount),
        static_cast<unsigned int>(normalMapCount),
        static_cast<unsigned int>(ormMapCount),
        static_cast<unsigned int>(emissiveMapCount),
        static_cast<unsigned int>(textures_.size()));

    if (!createGeometryResidency(
            asset,
            batchMaterialIndices)) {
        logError(
            "Sanctum consolidated geometry upload failed");
        shutdown();
        return false;
    }

    totalVertices_ =
        asset.totalVertices;
    totalIndices_ =
        asset.totalIndices;
    ready_ =
        !batches_.empty() &&
        !materials_.empty() &&
        !textures_.empty();

    if (ready_) {
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

    assetStreamer_.stop();
    asyncPrefetchQueued_ = 0U;

    if (device_ != VK_NULL_HANDLE) {
        // Initialization failures can leave recorded-but-unsubmitted uploads.
        // Drop those command/staging resources before destroying their images.
        discardPendingUploads();

        destroyGeometryResidency();

        for (auto& texture : textures_) {
            destroyTexture(texture);
        }

        if (pipeline_ != VK_NULL_HANDLE) {
            vkDestroyPipeline(
                device_,
                pipeline_,
                nullptr);
        }

        if (pipelineDoubleSided_ != VK_NULL_HANDLE) {
            vkDestroyPipeline(
                device_,
                pipelineDoubleSided_,
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
    materials_.clear();
    textures_.clear();

    streamGraph_.reset();
    textureMipResidency_.reset();
    streamGraphReady_ = false;
    streamCellBounds_ = {};
    streamDecisionCount_ = 0U;
    streamPlanFrame_ = 0U;
    lastLoggedStreamCell_ = 0U;
    pendingUploads_.clear();
    pendingUploadBytes_ = 0U;

    pipeline_ = VK_NULL_HANDLE;
    pipelineDoubleSided_ = VK_NULL_HANDLE;
    pipelineLayout_ = VK_NULL_HANDLE;
    descriptorPool_ = VK_NULL_HANDLE;
    descriptorSetLayout_ = VK_NULL_HANDLE;

    totalVertices_ = 0U;
    totalIndices_ = 0U;
    samplerAnisotropyEnabled_ = false;
    astcLdrSupported_ = false;
    maxSamplerAnisotropy_ = 1.0f;
    uploadBatchCommandLimit_ = 16U;
    textureResidentBudgetBytes_ =
        128ULL * 1024ULL * 1024ULL;
    textureResidentBytes_ = 0U;
    textureDegradedCount_ = 0U;

    physicalDevice_ = VK_NULL_HANDLE;
    device_ = VK_NULL_HANDLE;
    graphicsQueue_ = VK_NULL_HANDLE;
    graphicsQueueFamily_ = UINT32_MAX;
    commandPool_ = VK_NULL_HANDLE;
    renderPass_ = VK_NULL_HANDLE;
    sampleCount_ = VK_SAMPLE_COUNT_1_BIT;
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

StaticMeshFrameStats
VulkanStaticMeshRenderer::frameStats() const noexcept {
    return frameStats_;
}

void VulkanStaticMeshRenderer::setStreamingPortalOpen(
    std::uint32_t portalId,
    bool open) noexcept {
    if (!streamGraphReady_ ||
        portalId == 0U) {
        return;
    }

    (void) streamGraph_.setPortalOpen(
        portalId,
        open);
}

void VulkanStaticMeshRenderer::rebuildStreamingCellBounds() noexcept {
    streamCellBounds_ = {};

    for (const auto& batch : batches_) {
        if (batch.streamCellId == 0U) {
            continue;
        }

        StreamCellBounds* slot = nullptr;

        for (auto& candidate : streamCellBounds_) {
            if (candidate.valid &&
                candidate.cellId ==
                    batch.streamCellId) {
                slot = &candidate;
                break;
            }

            if (!candidate.valid &&
                slot == nullptr) {
                slot = &candidate;
            }
        }

        if (slot == nullptr) {
            continue;
        }

        if (!slot->valid) {
            slot->cellId =
                batch.streamCellId;
            slot->bounds =
                batch.bounds;
            slot->valid = true;
            continue;
        }

        for (std::size_t axis = 0U;
             axis < 3U;
             ++axis) {
            slot->bounds.minimum[axis] =
                std::min(
                    slot->bounds.minimum[axis],
                    batch.bounds.minimum[axis]);
            slot->bounds.maximum[axis] =
                std::max(
                    slot->bounds.maximum[axis],
                    batch.bounds.maximum[axis]);
        }
    }
}

std::uint32_t VulkanStaticMeshRenderer::inferStreamingCell(
    const StaticMeshCameraState& camera) const noexcept {
    const std::array<float, 3> point{{
        camera.x,
        camera.y,
        camera.z,
    }};

    std::uint32_t bestCell = 0U;
    float bestDistance =
        std::numeric_limits<float>::infinity();
    float bestVolume =
        std::numeric_limits<float>::infinity();

    for (const auto& cell :
         streamCellBounds_) {
        if (!cell.valid ||
            cell.cellId == 0U) {
            continue;
        }

        float distanceSquared = 0.0f;
        float volume = 1.0f;

        for (std::size_t axis = 0U;
             axis < 3U;
             ++axis) {
            const float minimum =
                cell.bounds.minimum[axis];
            const float maximum =
                cell.bounds.maximum[axis];

            if (point[axis] < minimum) {
                const float d =
                    minimum - point[axis];
                distanceSquared += d * d;
            } else if (
                point[axis] > maximum) {
                const float d =
                    point[axis] - maximum;
                distanceSquared += d * d;
            }

            volume *=
                std::max(
                    0.001f,
                    maximum - minimum);
        }

        if (distanceSquared <
                bestDistance ||
            (distanceSquared ==
                 bestDistance &&
             volume < bestVolume)) {
            bestDistance =
                distanceSquared;
            bestVolume =
                volume;
            bestCell =
                cell.cellId;
        }
    }

    return bestCell;
}

const StreamCellResourceDecision*
VulkanStaticMeshRenderer::streamDecision(
    std::uint64_t resourceId,
    std::size_t count) const noexcept {
    if (resourceId == 0U) {
        return nullptr;
    }

    const std::size_t limit =
        std::min(
            count,
            streamDecisions_.size());

    for (std::size_t i = 0U;
         i < limit;
         ++i) {
        if (streamDecisions_[i].
                resourceId ==
            resourceId) {
            return &streamDecisions_[i];
        }
    }

    return nullptr;
}

void VulkanStaticMeshRenderer::record(
    VkCommandBuffer command,
    VkExtent2D extent,
    std::uint32_t frameSlot,
    const StaticMeshCameraState& camera,
    const StaticMeshEnvironmentState& environment) const noexcept {
    frameStats_ = {};

    if (!ready_ ||
        command == VK_NULL_HANDLE ||
        extent.width == 0U ||
        extent.height == 0U) {
        return;
    }

    if (streamGraphReady_) {
        const std::uint32_t currentCell =
            inferStreamingCell(camera);

        if (currentCell != 0U) {
            if (currentCell !=
                streamCellCandidate_) {
                streamCellCandidate_ =
                    currentCell;
                streamCellStableFrames_ =
                    1U;
                streamCullingActive_ =
                    false;
                streamCullLogged_ =
                    false;
            } else {
                streamCellStableFrames_ =
                    std::min<std::uint32_t>(
                        streamCellStableFrames_ + 1U,
                        1000000U);

                if (streamCellStableFrames_ >= 8U) {
                    streamCullingActive_ =
                        true;
                }
            }

            const auto streamStats =
                streamGraph_.plan(
                    {
                        .currentCell =
                            currentCell,
                        .preloadPortalHops = 1U,
                        .memoryPressure =
                            environment.
                                memoryPressure,
                    },
                    streamDecisions_.data(),
                    streamDecisions_.size(),
                    streamDecisionCount_);

            frameStats_.streamingCell =
                currentCell;
            frameStats_.streamingHotResources =
                streamStats.hotResources;
            frameStats_.
                streamingPreloadResources =
                streamStats.preloadResources;
            frameStats_.
                streamingEvictableBytes =
                streamStats.evictableBytes;

            for (const auto& batch :
                 batches_) {
                const auto* decision =
                    streamDecision(
                        batch.streamResourceId,
                        streamDecisionCount_);

                if (decision != nullptr &&
                    !decision->desiredResident) {
                    ++frameStats_.
                        streamingColdBatches;
                }
            }

            ++streamPlanFrame_;

            if (currentCell !=
                    lastLoggedStreamCell_ ||
                (streamPlanFrame_ % 240U) ==
                    0U) {
                lastLoggedStreamCell_ =
                    currentCell;

                __android_log_print(
                    ANDROID_LOG_INFO,
                    kTag,
                    "XZIEL_WORLD_STREAMING_PLAN current_cell=%u hot_resources=%u preload_resources=%u cold_resources=%u cold_batches=%u desired_mb=%.2f evictable_mb=%.2f pressure=%u",
                    static_cast<unsigned int>(
                        currentCell),
                    static_cast<unsigned int>(
                        streamStats.hotResources),
                    static_cast<unsigned int>(
                        streamStats.preloadResources),
                    static_cast<unsigned int>(
                        streamStats.coldResources),
                    static_cast<unsigned int>(
                        frameStats_.
                            streamingColdBatches),
                    static_cast<double>(
                        streamStats.
                            desiredResidentBytes) /
                        (1024.0 * 1024.0),
                    static_cast<double>(
                        streamStats.
                            evictableBytes) /
                        (1024.0 * 1024.0),
                    static_cast<unsigned int>(
                        environment.
                            memoryPressure));
            }
        } else {
            streamCellCandidate_ = 0U;
            streamCellStableFrames_ = 0U;
            streamCullingActive_ = false;
            streamCullLogged_ = false;
            streamDecisionCount_ = 0U;
        }
    }

    VkPipeline boundPipeline =
        VK_NULL_HANDLE;

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

    const auto applyMaterial =
        [&](const GpuMaterial& material) noexcept {
            PushConstants materialPush = push;

            materialPush.baseColorFactorR =
                material.baseColorFactor[0];
            materialPush.baseColorFactorG =
                material.baseColorFactor[1];
            materialPush.baseColorFactorB =
                material.baseColorFactor[2];
            materialPush.baseColorFactorA =
                material.baseColorFactor[3];
            materialPush.metallicFactor =
                material.metallicFactor;
            materialPush.roughnessFactor =
                material.roughnessFactor;
            materialPush.normalScale =
                material.normalScale;
            materialPush.occlusionStrength =
                material.occlusionStrength;
            materialPush.emissiveFactorR =
                material.emissiveFactor[0];
            materialPush.emissiveFactorG =
                material.emissiveFactor[1];
            materialPush.emissiveFactorB =
                material.emissiveFactor[2];

            std::uint32_t flags = 0U;
            flags |= material.pbrEnabled ? 1U : 0U;
            flags |= material.hasNormalTexture ? 2U : 0U;
            flags |= material.hasOrmTexture ? 4U : 0U;
            flags |= material.hasEmissiveTexture ? 8U : 0U;
            materialPush.materialFlags =
                static_cast<float>(flags);

            vkCmdPushConstants(
                command,
                pipelineLayout_,
                VK_SHADER_STAGE_VERTEX_BIT |
                    VK_SHADER_STAGE_FRAGMENT_BIT,
                0U,
                static_cast<std::uint32_t>(
                    sizeof(materialPush)),
                &materialPush);
        };

    if (geometryVertexBuffer_ == VK_NULL_HANDLE ||
        geometryIndexBuffer_ == VK_NULL_HANDLE) {
        return;
    }

    const VkDeviceSize geometryOffset = 0U;

    vkCmdBindVertexBuffers(
        command,
        0U,
        1U,
        &geometryVertexBuffer_,
        &geometryOffset);

    vkCmdBindIndexBuffer(
        command,
        geometryIndexBuffer_,
        0U,
        VK_INDEX_TYPE_UINT16);

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
        if (batch.materialIndex >=
            materials_.size()) {
            continue;
        }

        if (streamCullingActive_) {
            const auto* decision =
                streamDecision(
                    batch.streamResourceId,
                    streamDecisionCount_);

            if (decision != nullptr &&
                !decision->desiredResident) {
                ++frameStats_.culledBatches;
                ++frameStats_.
                    streamingCulledBatches;
                continue;
            }
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
            ++frameStats_.culledBatches;
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
            ++frameStats_.culledBatches;
            continue;
        }

        ++frameStats_.visibleBatches;

        const VkPipeline desiredPipeline =
            batch.doubleSided
            ? pipelineDoubleSided_
            : pipeline_;

        if (desiredPipeline == VK_NULL_HANDLE) {
            ++frameStats_.culledBatches;
            continue;
        }

        if (boundPipeline != desiredPipeline) {
            vkCmdBindPipeline(
                command,
                VK_PIPELINE_BIND_POINT_GRAPHICS,
                desiredPipeline);
            boundPipeline =
                desiredPipeline;
        }

        const auto& material =
            materials_[batch.materialIndex];

        applyMaterial(material);

        vkCmdBindDescriptorSets(
            command,
            VK_PIPELINE_BIND_POINT_GRAPHICS,
            pipelineLayout_,
            0U,
            1U,
            &material.descriptorSets[
                frameSlot %
                kDescriptorFrames],
            0U,
            nullptr);

        vkCmdDrawIndexed(
            command,
            batch.indexCount,
            1U,
            batch.firstIndex,
            batch.vertexOffset,
            0U);

        ++frameStats_.drawCalls;
        frameStats_.submittedTriangles +=
            static_cast<std::uint64_t>(
                batch.indexCount / 3U);
    }

    if (streamCullingActive_ &&
        !streamCullLogged_ &&
        frameStats_.streamingCell != 0U) {
        streamCullLogged_ = true;

        __android_log_print(
            ANDROID_LOG_INFO,
            kTag,
            "XZIEL_WORLD_STREAMING_CULL_ACTIVE cell=%u stable_frames=%u cold_batches=%u culled_batches=%u draws=%u",
            static_cast<unsigned int>(
                frameStats_.streamingCell),
            static_cast<unsigned int>(
                streamCellStableFrames_),
            static_cast<unsigned int>(
                frameStats_.
                    streamingColdBatches),
            static_cast<unsigned int>(
                frameStats_.
                    streamingCulledBatches),
            static_cast<unsigned int>(
                frameStats_.drawCalls));
    }
}

void VulkanStaticMeshRenderer::recordViewmodel(
    VkCommandBuffer command,
    VkExtent2D extent,
    std::uint32_t frameSlot,
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
        pipelineDoubleSided_ != VK_NULL_HANDLE
            ? pipelineDoubleSided_
            : pipeline_);

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
    push.modelYaw = state.yawRadians;
    push.modelPitch = state.pitchRadians;
    push.modelRoll = state.rollRadians;
    push.viewmodelMode = 1.0f;

    const auto applyMaterial =
        [&](const GpuMaterial& material) noexcept {
            PushConstants materialPush = push;
            materialPush.baseColorFactorR = material.baseColorFactor[0];
            materialPush.baseColorFactorG = material.baseColorFactor[1];
            materialPush.baseColorFactorB = material.baseColorFactor[2];
            materialPush.baseColorFactorA = material.baseColorFactor[3];
            materialPush.metallicFactor = material.metallicFactor;
            materialPush.roughnessFactor = material.roughnessFactor;
            materialPush.normalScale = material.normalScale;
            materialPush.occlusionStrength = material.occlusionStrength;
            materialPush.emissiveFactorR = material.emissiveFactor[0];
            materialPush.emissiveFactorG = material.emissiveFactor[1];
            materialPush.emissiveFactorB = material.emissiveFactor[2];

            std::uint32_t flags = 0U;
            flags |= material.pbrEnabled ? 1U : 0U;
            flags |= material.hasNormalTexture ? 2U : 0U;
            flags |= material.hasOrmTexture ? 4U : 0U;
            flags |= material.hasEmissiveTexture ? 8U : 0U;
            materialPush.materialFlags =
                static_cast<float>(flags);

            vkCmdPushConstants(
                command,
                pipelineLayout_,
                VK_SHADER_STAGE_VERTEX_BIT |
                    VK_SHADER_STAGE_FRAGMENT_BIT,
                0U,
                static_cast<std::uint32_t>(
                    sizeof(materialPush)),
                &materialPush);
        };

    if (geometryVertexBuffer_ == VK_NULL_HANDLE ||
        geometryIndexBuffer_ == VK_NULL_HANDLE) {
        return;
    }

    const VkDeviceSize geometryOffset = 0U;

    vkCmdBindVertexBuffers(
        command,
        0U,
        1U,
        &geometryVertexBuffer_,
        &geometryOffset);

    vkCmdBindIndexBuffer(
        command,
        geometryIndexBuffer_,
        0U,
        VK_INDEX_TYPE_UINT16);

    for (const auto& batch : batches_) {
        if (batch.materialIndex >=
            materials_.size()) {
            continue;
        }

        const auto& material =
            materials_[batch.materialIndex];

        applyMaterial(material);

        vkCmdBindDescriptorSets(
            command,
            VK_PIPELINE_BIND_POINT_GRAPHICS,
            pipelineLayout_,
            0U,
            1U,
            &material.descriptorSets[
                frameSlot %
                kDescriptorFrames],
            0U,
            nullptr);

        vkCmdDrawIndexed(
            command,
            batch.indexCount,
            1U,
            batch.firstIndex,
            batch.vertexOffset,
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

    return result.success;
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

    std::array<VkDescriptorSetLayoutBinding, 4>
        textureBindings{};

    for (std::uint32_t binding = 0U;
         binding < textureBindings.size();
         ++binding) {
        textureBindings[binding].binding = binding;
        textureBindings[binding].descriptorType =
            VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
        textureBindings[binding].descriptorCount = 1U;
        textureBindings[binding].stageFlags =
            VK_SHADER_STAGE_FRAGMENT_BIT;
    }

    VkDescriptorSetLayoutCreateInfo setInfo{
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO
    };
    setInfo.bindingCount =
        static_cast<std::uint32_t>(
            textureBindings.size());
    setInfo.pBindings =
        textureBindings.data();

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
        sampleCount_;

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

    // glTF's default is single-sided: back-face culling enabled.
    raster.cullMode =
        VK_CULL_MODE_BACK_BIT;

    const VkResult culledResult =
        vkCreateGraphicsPipelines(
            device_,
            VK_NULL_HANDLE,
            1U,
            &info,
            nullptr,
            &pipeline_);

    VkResult doubleSidedResult =
        VK_ERROR_INITIALIZATION_FAILED;

    if (ok(culledResult)) {
        raster.cullMode =
            VK_CULL_MODE_NONE;

        doubleSidedResult =
            vkCreateGraphicsPipelines(
                device_,
                VK_NULL_HANDLE,
                1U,
                &info,
                nullptr,
                &pipelineDoubleSided_);
    }

    vkDestroyShaderModule(
        device_, fragment, nullptr);
    vkDestroyShaderModule(
        device_, vertex, nullptr);

    return
        ok(culledResult) &&
        ok(doubleSidedResult);
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

bool VulkanStaticMeshRenderer::createGeometryResidency(
    const StaticMeshAsset& asset,
    const std::vector<std::uint32_t>& materialIndices) noexcept {
    destroyGeometryResidency();

    if (asset.batches.empty() ||
        materialIndices.size() !=
            asset.batches.size() ||
        asset.totalVertices == 0U ||
        asset.totalIndices == 0U ||
        asset.totalVertices >
            static_cast<std::uint32_t>(
                std::numeric_limits<std::int32_t>::max())) {
        return false;
    }

    geometryVertexBytes_ =
        static_cast<VkDeviceSize>(
            asset.totalVertices) *
        sizeof(StaticMeshVertex);

    geometryIndexBytes_ =
        static_cast<VkDeviceSize>(
            asset.totalIndices) *
        sizeof(std::uint16_t);

    const VkMemoryPropertyFlags hostFlags =
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
        VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;

    const VkMemoryPropertyFlags preferredFlags =
        hostFlags |
        VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT;

    const auto destroyPartial =
        [&]() noexcept {
            if (geometryIndexBuffer_ != VK_NULL_HANDLE) {
                vkDestroyBuffer(
                    device_,
                    geometryIndexBuffer_,
                    nullptr);
                geometryIndexBuffer_ =
                    VK_NULL_HANDLE;
            }

            if (geometryIndexMemory_ != VK_NULL_HANDLE) {
                vkFreeMemory(
                    device_,
                    geometryIndexMemory_,
                    nullptr);
                geometryIndexMemory_ =
                    VK_NULL_HANDLE;
            }

            if (geometryVertexBuffer_ != VK_NULL_HANDLE) {
                vkDestroyBuffer(
                    device_,
                    geometryVertexBuffer_,
                    nullptr);
                geometryVertexBuffer_ =
                    VK_NULL_HANDLE;
            }

            if (geometryVertexMemory_ != VK_NULL_HANDLE) {
                vkFreeMemory(
                    device_,
                    geometryVertexMemory_,
                    nullptr);
                geometryVertexMemory_ =
                    VK_NULL_HANDLE;
            }
        };

    auto createPair =
        [&](VkMemoryPropertyFlags flags) noexcept {
            if (!createBuffer(
                    geometryVertexBytes_,
                    VK_BUFFER_USAGE_VERTEX_BUFFER_BIT |
                        VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                    flags,
                    geometryVertexBuffer_,
                    geometryVertexMemory_)) {
                return false;
            }

            if (!createBuffer(
                    geometryIndexBytes_,
                    VK_BUFFER_USAGE_INDEX_BUFFER_BIT |
                        VK_BUFFER_USAGE_TRANSFER_DST_BIT,
                    flags,
                    geometryIndexBuffer_,
                    geometryIndexMemory_)) {
                destroyPartial();
                return false;
            }

            return true;
        };

    geometryDeviceLocalHostVisible_ =
        createPair(preferredFlags);

    if (!geometryDeviceLocalHostVisible_ &&
        !createPair(hostFlags)) {
        geometryVertexBytes_ = 0U;
        geometryIndexBytes_ = 0U;
        return false;
    }

    void* mappedVertices = nullptr;
    void* mappedIndices = nullptr;

    if (!ok(
            vkMapMemory(
                device_,
                geometryVertexMemory_,
                0U,
                geometryVertexBytes_,
                0U,
                &mappedVertices)) ||
        !ok(
            vkMapMemory(
                device_,
                geometryIndexMemory_,
                0U,
                geometryIndexBytes_,
                0U,
                &mappedIndices))) {
        if (mappedVertices != nullptr) {
            vkUnmapMemory(
                device_,
                geometryVertexMemory_);
        }
        destroyGeometryResidency();
        return false;
    }

    auto* vertexBytes =
        static_cast<std::byte*>(
            mappedVertices);

    auto* indexBytes =
        static_cast<std::byte*>(
            mappedIndices);

    std::uint64_t vertexCursor = 0U;
    std::uint64_t indexCursor = 0U;

    try {
        batches_.clear();
        batches_.reserve(
            asset.batches.size());

        for (std::size_t batchIndex = 0U;
             batchIndex < asset.batches.size();
             ++batchIndex) {
            const auto& batch =
                asset.batches[batchIndex];

            if (batch.vertices.empty() ||
                batch.indices.empty() ||
                vertexCursor +
                        batch.vertices.size() >
                    asset.totalVertices ||
                indexCursor +
                        batch.indices.size() >
                    asset.totalIndices) {
                vkUnmapMemory(
                    device_,
                    geometryIndexMemory_);
                vkUnmapMemory(
                    device_,
                    geometryVertexMemory_);
                destroyGeometryResidency();
                return false;
            }

            const VkDeviceSize vertexOffsetBytes =
                static_cast<VkDeviceSize>(
                    vertexCursor) *
                sizeof(StaticMeshVertex);

            const VkDeviceSize indexOffsetBytes =
                static_cast<VkDeviceSize>(
                    indexCursor) *
                sizeof(std::uint16_t);

            std::memcpy(
                vertexBytes +
                    vertexOffsetBytes,
                batch.vertices.data(),
                batch.vertices.size() *
                    sizeof(StaticMeshVertex));

            std::memcpy(
                indexBytes +
                    indexOffsetBytes,
                batch.indices.data(),
                batch.indices.size() *
                    sizeof(std::uint16_t));

            GpuBatch gpuBatch{};
            gpuBatch.materialIndex =
                materialIndices[batchIndex];

            if (gpuBatch.materialIndex <
                materials_.size()) {
                gpuBatch.streamResourceId =
                    materials_[
                        gpuBatch.materialIndex].
                            streamResourceId;
            }

            gpuBatch.streamCellId =
                static_cast<std::uint32_t>(
                    sanctumZoneForAssetName(
                        batch.textureName));
            gpuBatch.firstIndex =
                static_cast<std::uint32_t>(
                    indexCursor);
            gpuBatch.vertexOffset =
                static_cast<std::int32_t>(
                    vertexCursor);
            gpuBatch.indexCount =
                static_cast<std::uint32_t>(
                    batch.indices.size());
            gpuBatch.bounds =
                batch.bounds;
            gpuBatch.doubleSided =
                batch.doubleSided();

            batches_.emplace_back(
                gpuBatch);

            vertexCursor +=
                batch.vertices.size();

            indexCursor +=
                batch.indices.size();
        }
    } catch (...) {
        vkUnmapMemory(
            device_,
            geometryIndexMemory_);
        vkUnmapMemory(
            device_,
            geometryVertexMemory_);
        destroyGeometryResidency();
        return false;
    }

    vkUnmapMemory(
        device_,
        geometryIndexMemory_);

    vkUnmapMemory(
        device_,
        geometryVertexMemory_);

    if (vertexCursor != asset.totalVertices ||
        indexCursor != asset.totalIndices) {
        destroyGeometryResidency();
        return false;
    }

    rebuildStreamingCellBounds();

    __android_log_print(
        ANDROID_LOG_INFO,
        kTag,
        "XZIEL_STATIC_GEOMETRY_RESIDENCY buffers=2 batches=%u vertex_mb=%.2f index_mb=%.2f device_local_host_visible=%d",
        static_cast<unsigned int>(
            batches_.size()),
        static_cast<double>(
            geometryVertexBytes_) /
            (1024.0 * 1024.0),
        static_cast<double>(
            geometryIndexBytes_) /
            (1024.0 * 1024.0),
        geometryDeviceLocalHostVisible_
            ? 1
            : 0);

    return true;
}

bool VulkanStaticMeshRenderer::createTexture(
    AAssetManager* assetManager,
    const std::string& exportedName,
    bool srgb,
    GpuTexture& out) noexcept {
    const std::string ktxPath =
        textureAssetPath(
            exportedName,
            ".ktx2");

    if (astcLdrSupported_ &&
        assetExists(
            assetManager,
            ktxPath)) {
        if (!createKtx2Texture(
                assetManager,
                ktxPath,
                srgb,
                out)) {
            logError(
                "ASTC KTX2 texture exists but failed validation/upload");
            return false;
        }

        return true;
    }

    const std::string pngPath =
        textureAssetPath(
            exportedName,
            ".png");

    return createPngTexture(
        assetManager,
        pngPath,
        srgb,
        out);
}

bool VulkanStaticMeshRenderer::createKtx2Texture(
    AAssetManager* assetManager,
    const std::string& assetPath,
    bool srgb,
    GpuTexture& out) noexcept {
    std::vector<std::byte> bytes;

    const bool asyncRead =
        assetStreamer_.take(
            assetPath,
            bytes);

    if (!asyncRead) {
        AAsset* asset =
            AAssetManager_open(
                assetManager,
                assetPath.c_str(),
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
    }

    Ktx2Texture texture{};
    const auto parsed =
        parseKtx2Astc(
            std::span<const std::byte>(
                bytes.data(),
                bytes.size()),
            texture);

    if (!parsed.success ||
        texture.levels.empty() ||
        texture.srgb != srgb) {
        return false;
    }

    const VkFormat textureFormat =
        static_cast<VkFormat>(
            texture.vkFormat);

    VkFormatProperties properties{};
    vkGetPhysicalDeviceFormatProperties(
        physicalDevice_,
        textureFormat,
        &properties);

    if ((properties.optimalTilingFeatures &
         VK_FORMAT_FEATURE_SAMPLED_IMAGE_BIT) == 0U) {
        return false;
    }

    std::uint32_t residentBaseMip = 0U;

    const auto fullRange =
        planKtx2ResidentMipRange(
            texture,
            0U);

    if (!fullRange.valid) {
        return false;
    }

    const std::uint64_t budgetRemaining =
        textureResidentBytes_ <
                textureResidentBudgetBytes_
        ? textureResidentBudgetBytes_ -
            textureResidentBytes_
        : 0U;

    if (fullRange.payloadBytes >
            budgetRemaining &&
        texture.levels.size() > 1U &&
        texture.levels.size() <=
            kMaxStreamedTextureMips) {
        try {
            TextureMipChainDesc desc{};
            desc.id = 1U;
            desc.mipCount =
                static_cast<std::uint32_t>(
                    texture.levels.size());

            for (std::uint32_t mip = 0U;
                 mip < desc.mipCount;
                 ++mip) {
                desc.mipBytes[mip] =
                    texture.levels[mip].
                        byteLength;
            }

            TextureMipResidencyManager planner(
                1U);

            if (planner.registerTexture(
                    desc,
                    0U)) {
                TextureMipChange change{};
                const std::uint64_t target =
                    fullRange.payloadBytes -
                    std::min(
                        fullRange.payloadBytes,
                        budgetRemaining);

                if (planner.planDemotions(
                        target,
                        0U,
                        0U,
                        &change,
                        1U) == 1U) {
                    // Startup quality guard: never discard more than the top
                    // two mips automatically. Runtime streaming can become
                    // more aggressive later if telemetry proves it necessary.
                    residentBaseMip =
                        std::min<std::uint32_t>(
                            change.newBaseMip,
                            std::min<std::uint32_t>(
                                2U,
                                desc.mipCount - 1U));
                }
            }
        } catch (...) {
            residentBaseMip = 0U;
        }
    }

    const auto residentRange =
        planKtx2ResidentMipRange(
            texture,
            residentBaseMip);

    if (!residentRange.valid) {
        return false;
    }

    std::vector<VkDeviceSize> stagingOffsets;
    std::vector<VkBufferImageCopy> regions;

    VkDeviceSize stagingBytes = 0U;

    try {
        stagingOffsets.reserve(
            residentRange.mipCount);
        regions.reserve(
            residentRange.mipCount);

        for (std::size_t sourceMip =
                 residentBaseMip;
             sourceMip < texture.levels.size();
             ++sourceMip) {
            const auto& level =
                texture.levels[sourceMip];

            stagingBytes =
                (stagingBytes + 15U) &
                ~VkDeviceSize{15U};

            stagingOffsets.push_back(
                stagingBytes);

            if (level.byteLength >
                std::numeric_limits<VkDeviceSize>::max() -
                stagingBytes) {
                return false;
            }

            stagingBytes +=
                static_cast<VkDeviceSize>(
                    level.byteLength);
        }
    } catch (...) {
        return false;
    }

    if (stagingBytes == 0U) {
        return false;
    }

    VkBuffer staging = VK_NULL_HANDLE;
    VkDeviceMemory stagingMemory = VK_NULL_HANDLE;

    if (!createBuffer(
            stagingBytes,
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
                stagingBytes,
                0U,
                &mapped))) {
        vkFreeMemory(
            device_, stagingMemory, nullptr);
        vkDestroyBuffer(
            device_, staging, nullptr);
        return false;
    }

    auto* destination =
        static_cast<std::byte*>(mapped);

    for (std::size_t sourceMip =
             residentBaseMip;
         sourceMip < texture.levels.size();
         ++sourceMip) {
        const std::size_t residentMip =
            sourceMip -
            residentBaseMip;
        const auto& level =
            texture.levels[sourceMip];

        std::memcpy(
            destination +
                stagingOffsets[residentMip],
            bytes.data() +
                static_cast<std::size_t>(
                    level.byteOffset),
            static_cast<std::size_t>(
                level.byteLength));

        VkBufferImageCopy copy{};
        copy.bufferOffset =
            stagingOffsets[residentMip];
        copy.bufferRowLength = 0U;
        copy.bufferImageHeight = 0U;
        copy.imageSubresource.aspectMask =
            VK_IMAGE_ASPECT_COLOR_BIT;
        copy.imageSubresource.mipLevel =
            static_cast<std::uint32_t>(
                residentMip);
        copy.imageSubresource.baseArrayLayer = 0U;
        copy.imageSubresource.layerCount = 1U;
        copy.imageExtent = {
            level.width,
            level.height,
            1U,
        };

        regions.push_back(copy);
    }

    vkUnmapMemory(
        device_,
        stagingMemory);

    VkImageCreateInfo imageInfo{
        VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO
    };
    imageInfo.imageType = VK_IMAGE_TYPE_2D;
    imageInfo.extent = {
        residentRange.width,
        residentRange.height,
        1U,
    };
    imageInfo.mipLevels =
        residentRange.mipCount;
    imageInfo.arrayLayers = 1U;
    imageInfo.format = textureFormat;
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
    toTransfer.subresourceRange.levelCount =
        imageInfo.mipLevels;
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
        0U, nullptr,
        0U, nullptr,
        1U, &toTransfer);

    vkCmdCopyBufferToImage(
        command,
        staging,
        out.image,
        VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
        static_cast<std::uint32_t>(
            regions.size()),
        regions.data());

    VkImageMemoryBarrier toShader{
        VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER
    };
    toShader.oldLayout =
        VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    toShader.newLayout =
        VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    toShader.srcQueueFamilyIndex =
        VK_QUEUE_FAMILY_IGNORED;
    toShader.dstQueueFamilyIndex =
        VK_QUEUE_FAMILY_IGNORED;
    toShader.image = out.image;
    toShader.subresourceRange.aspectMask =
        VK_IMAGE_ASPECT_COLOR_BIT;
    toShader.subresourceRange.baseMipLevel = 0U;
    toShader.subresourceRange.levelCount =
        imageInfo.mipLevels;
    toShader.subresourceRange.baseArrayLayer = 0U;
    toShader.subresourceRange.layerCount = 1U;
    toShader.srcAccessMask =
        VK_ACCESS_TRANSFER_WRITE_BIT;
    toShader.dstAccessMask =
        VK_ACCESS_SHADER_READ_BIT;

    vkCmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT,
        0U,
        0U, nullptr,
        0U, nullptr,
        1U, &toShader);

    if (!queueUploadCommands(
            command,
            staging,
            stagingMemory,
            stagingBytes)) {
        destroyTexture(out);
        return false;
    }

    VkImageViewCreateInfo viewInfo{
        VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO
    };
    viewInfo.image = out.image;
    viewInfo.viewType =
        VK_IMAGE_VIEW_TYPE_2D;
    viewInfo.format = textureFormat;
    viewInfo.subresourceRange.aspectMask =
        VK_IMAGE_ASPECT_COLOR_BIT;
    viewInfo.subresourceRange.baseMipLevel = 0U;
    viewInfo.subresourceRange.levelCount =
        imageInfo.mipLevels;
    viewInfo.subresourceRange.baseArrayLayer = 0U;
    viewInfo.subresourceRange.layerCount = 1U;

    if (!ok(
            vkCreateImageView(
                device_,
                &viewInfo,
                nullptr,
                &out.view)) ||
        !createTextureSampler(
            imageInfo.mipLevels,
            out)) {
        // The upload has not been submitted yet. Drop the pending batch before
        // invalidating an image referenced by its recorded command buffer.
        discardPendingUploads();
        destroyTexture(out);
        return false;
    }

    out.assetPath = assetPath;
    out.width = texture.width;
    out.height = texture.height;
    out.residentWidth =
        residentRange.width;
    out.residentHeight =
        residentRange.height;
    out.mipLevels =
        residentRange.mipCount;
    out.residentBaseMip =
        residentBaseMip;
    out.sourceMipLevels =
        static_cast<std::uint32_t>(
            std::min<std::size_t>(
                texture.levels.size(),
                kMaxStreamedTextureMips));
    out.sourceMipBytes.fill(0U);

    for (std::uint32_t mip = 0U;
         mip < out.sourceMipLevels;
         ++mip) {
        out.sourceMipBytes[mip] =
            texture.levels[mip].
                byteLength;
    }

    out.residentPayloadBytes =
        residentRange.payloadBytes;
    out.allocationBytes =
        static_cast<std::uint64_t>(
            requirements.size);

    if (residentRange.payloadBytes >
        std::numeric_limits<std::uint64_t>::max() -
            textureResidentBytes_) {
        discardPendingUploads();
        destroyTexture(out);
        return false;
    }

    textureResidentBytes_ +=
        residentRange.payloadBytes;

    if (residentBaseMip > 0U) {
        ++textureDegradedCount_;

        __android_log_print(
            ANDROID_LOG_INFO,
            kTag,
            "XZIEL_TEXTURE_MIP_RESIDENCY path=%s base_mip=%u source=%ux%u resident=%ux%u saved_payload_bytes=%llu resident_total_mb=%.2f budget_mb=%.2f degraded=%u",
            assetPath.c_str(),
            static_cast<unsigned int>(
                residentBaseMip),
            texture.width,
            texture.height,
            residentRange.width,
            residentRange.height,
            static_cast<unsigned long long>(
                fullRange.payloadBytes -
                residentRange.payloadBytes),
            static_cast<double>(
                textureResidentBytes_) /
                (1024.0 * 1024.0),
            static_cast<double>(
                textureResidentBudgetBytes_) /
                (1024.0 * 1024.0),
            static_cast<unsigned int>(
                textureDegradedCount_));
    }

    __android_log_print(
        ANDROID_LOG_INFO,
        kTag,
        "XZIEL_KTX2_ASTC_TEXTURE path=%s format=%u source=%ux%u resident=%ux%u base_mip=%u mips=%u/%u payload_bytes=%llu gpu_bytes=%llu",
        assetPath.c_str(),
        static_cast<unsigned int>(
            texture.vkFormat),
        texture.width,
        texture.height,
        residentRange.width,
        residentRange.height,
        static_cast<unsigned int>(
            residentBaseMip),
        residentRange.mipCount,
        static_cast<unsigned int>(
            texture.levels.size()),
        static_cast<unsigned long long>(
            residentRange.payloadBytes),
        static_cast<unsigned long long>(
            requirements.size));

    return true;
}

bool VulkanStaticMeshRenderer::createTextureSampler(
    std::uint32_t mipLevels,
    GpuTexture& out) noexcept {
    if (mipLevels == 0U) {
        return false;
    }

    VkSamplerCreateInfo samplerInfo{
        VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO
    };
    samplerInfo.magFilter = VK_FILTER_LINEAR;
    samplerInfo.minFilter = VK_FILTER_LINEAR;
    samplerInfo.mipmapMode =
        VK_SAMPLER_MIPMAP_MODE_LINEAR;
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
    samplerInfo.mipLodBias = 0.0f;
    samplerInfo.minLod = 0.0f;
    samplerInfo.maxLod =
        static_cast<float>(
            mipLevels - 1U);

    return ok(
        vkCreateSampler(
            device_,
            &samplerInfo,
            nullptr,
            &out.sampler));
}

bool VulkanStaticMeshRenderer::createPngTexture(
    AAssetManager* assetManager,
    const std::string& assetPath,
    bool srgb,
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

    if (createResult != ANDROID_IMAGE_DECODER_SUCCESS ||
        decoder == nullptr) {
        AAsset_close(asset);
        return false;
    }

    (void) AImageDecoder_setAndroidBitmapFormat(
        decoder,
        ANDROID_BITMAP_FORMAT_RGBA_8888);

    const AImageDecoderHeaderInfo* header =
        AImageDecoder_getHeaderInfo(decoder);

    const int32_t width =
        AImageDecoderHeaderInfo_getWidth(header);
    const int32_t height =
        AImageDecoderHeaderInfo_getHeight(header);
    const std::size_t stride =
        AImageDecoder_getMinimumStride(decoder);

    if (width <= 0 ||
        height <= 0 ||
        stride < static_cast<std::size_t>(width) * 4U) {
        AImageDecoder_delete(decoder);
        AAsset_close(asset);
        return false;
    }

    const std::size_t pixelBytes =
        stride * static_cast<std::size_t>(height);

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

    if (decodeResult != ANDROID_IMAGE_DECODER_SUCCESS) {
        return false;
    }

    const VkFormat textureFormat =
        srgb
        ? VK_FORMAT_R8G8B8A8_SRGB
        : VK_FORMAT_R8G8B8A8_UNORM;

    VkFormatProperties formatProperties{};
    vkGetPhysicalDeviceFormatProperties(
        physicalDevice_,
        textureFormat,
        &formatProperties);

    const bool linearBlitSupported =
        (formatProperties.optimalTilingFeatures &
         VK_FORMAT_FEATURE_SAMPLED_IMAGE_FILTER_LINEAR_BIT) != 0U;

    const std::uint32_t maxDimension =
        static_cast<std::uint32_t>(
            std::max(width, height));

    const std::uint32_t mipLevels =
        linearBlitSupported
        ? 1U +
              static_cast<std::uint32_t>(
                  std::floor(
                      std::log2(
                          static_cast<double>(
                              std::max(maxDimension, 1U)))))
        : 1U;

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
    imageInfo.imageType = VK_IMAGE_TYPE_2D;
    imageInfo.extent.width =
        static_cast<std::uint32_t>(width);
    imageInfo.extent.height =
        static_cast<std::uint32_t>(height);
    imageInfo.extent.depth = 1U;
    imageInfo.mipLevels = mipLevels;
    imageInfo.arrayLayers = 1U;
    imageInfo.format = textureFormat;
    imageInfo.tiling = VK_IMAGE_TILING_OPTIMAL;
    imageInfo.initialLayout =
        VK_IMAGE_LAYOUT_UNDEFINED;
    imageInfo.usage =
        VK_IMAGE_USAGE_TRANSFER_DST_BIT |
        VK_IMAGE_USAGE_SAMPLED_BIT |
        (mipLevels > 1U
            ? VK_IMAGE_USAGE_TRANSFER_SRC_BIT
            : 0U);
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
    allocation.allocationSize = requirements.size;
    allocation.memoryTypeIndex = memoryType;

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

    VkImageMemoryBarrier initialBarrier{
        VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER
    };
    initialBarrier.oldLayout =
        VK_IMAGE_LAYOUT_UNDEFINED;
    initialBarrier.newLayout =
        VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    initialBarrier.srcQueueFamilyIndex =
        VK_QUEUE_FAMILY_IGNORED;
    initialBarrier.dstQueueFamilyIndex =
        VK_QUEUE_FAMILY_IGNORED;
    initialBarrier.image = out.image;
    initialBarrier.subresourceRange.aspectMask =
        VK_IMAGE_ASPECT_COLOR_BIT;
    initialBarrier.subresourceRange.baseMipLevel = 0U;
    initialBarrier.subresourceRange.levelCount =
        mipLevels;
    initialBarrier.subresourceRange.baseArrayLayer = 0U;
    initialBarrier.subresourceRange.layerCount = 1U;
    initialBarrier.srcAccessMask = 0U;
    initialBarrier.dstAccessMask =
        VK_ACCESS_TRANSFER_WRITE_BIT;

    vkCmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        0U,
        0U, nullptr,
        0U, nullptr,
        1U, &initialBarrier);

    VkBufferImageCopy copy{};
    copy.bufferOffset = 0U;
    copy.bufferRowLength =
        static_cast<std::uint32_t>(
            stride / 4U);
    copy.bufferImageHeight =
        static_cast<std::uint32_t>(height);
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

    std::int32_t mipWidth = width;
    std::int32_t mipHeight = height;

    for (std::uint32_t level = 1U;
         level < mipLevels;
         ++level) {
        VkImageMemoryBarrier previousToSource{
            VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER
        };
        previousToSource.oldLayout =
            VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
        previousToSource.newLayout =
            VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        previousToSource.srcQueueFamilyIndex =
            VK_QUEUE_FAMILY_IGNORED;
        previousToSource.dstQueueFamilyIndex =
            VK_QUEUE_FAMILY_IGNORED;
        previousToSource.image = out.image;
        previousToSource.subresourceRange.aspectMask =
            VK_IMAGE_ASPECT_COLOR_BIT;
        previousToSource.subresourceRange.baseMipLevel =
            level - 1U;
        previousToSource.subresourceRange.levelCount = 1U;
        previousToSource.subresourceRange.baseArrayLayer = 0U;
        previousToSource.subresourceRange.layerCount = 1U;
        previousToSource.srcAccessMask =
            VK_ACCESS_TRANSFER_WRITE_BIT;
        previousToSource.dstAccessMask =
            VK_ACCESS_TRANSFER_READ_BIT;

        vkCmdPipelineBarrier(
            command,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            0U,
            0U, nullptr,
            0U, nullptr,
            1U, &previousToSource);

        const std::int32_t nextWidth =
            std::max(mipWidth / 2, 1);
        const std::int32_t nextHeight =
            std::max(mipHeight / 2, 1);

        VkImageBlit blit{};
        blit.srcOffsets[0] = {0, 0, 0};
        blit.srcOffsets[1] = {
            mipWidth,
            mipHeight,
            1,
        };
        blit.srcSubresource.aspectMask =
            VK_IMAGE_ASPECT_COLOR_BIT;
        blit.srcSubresource.mipLevel =
            level - 1U;
        blit.srcSubresource.baseArrayLayer = 0U;
        blit.srcSubresource.layerCount = 1U;
        blit.dstOffsets[0] = {0, 0, 0};
        blit.dstOffsets[1] = {
            nextWidth,
            nextHeight,
            1,
        };
        blit.dstSubresource.aspectMask =
            VK_IMAGE_ASPECT_COLOR_BIT;
        blit.dstSubresource.mipLevel = level;
        blit.dstSubresource.baseArrayLayer = 0U;
        blit.dstSubresource.layerCount = 1U;

        vkCmdBlitImage(
            command,
            out.image,
            VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
            out.image,
            VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
            1U,
            &blit,
            VK_FILTER_LINEAR);

        VkImageMemoryBarrier previousToShader{
            VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER
        };
        previousToShader.oldLayout =
            VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
        previousToShader.newLayout =
            VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
        previousToShader.srcQueueFamilyIndex =
            VK_QUEUE_FAMILY_IGNORED;
        previousToShader.dstQueueFamilyIndex =
            VK_QUEUE_FAMILY_IGNORED;
        previousToShader.image = out.image;
        previousToShader.subresourceRange.aspectMask =
            VK_IMAGE_ASPECT_COLOR_BIT;
        previousToShader.subresourceRange.baseMipLevel =
            level - 1U;
        previousToShader.subresourceRange.levelCount = 1U;
        previousToShader.subresourceRange.baseArrayLayer = 0U;
        previousToShader.subresourceRange.layerCount = 1U;
        previousToShader.srcAccessMask =
            VK_ACCESS_TRANSFER_READ_BIT;
        previousToShader.dstAccessMask =
            VK_ACCESS_SHADER_READ_BIT;

        vkCmdPipelineBarrier(
            command,
            VK_PIPELINE_STAGE_TRANSFER_BIT,
            VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT,
            0U,
            0U, nullptr,
            0U, nullptr,
            1U, &previousToShader);

        mipWidth = nextWidth;
        mipHeight = nextHeight;
    }

    VkImageMemoryBarrier finalToShader{
        VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER
    };
    finalToShader.oldLayout =
        VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
    finalToShader.newLayout =
        VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    finalToShader.srcQueueFamilyIndex =
        VK_QUEUE_FAMILY_IGNORED;
    finalToShader.dstQueueFamilyIndex =
        VK_QUEUE_FAMILY_IGNORED;
    finalToShader.image = out.image;
    finalToShader.subresourceRange.aspectMask =
        VK_IMAGE_ASPECT_COLOR_BIT;
    finalToShader.subresourceRange.baseMipLevel =
        mipLevels - 1U;
    finalToShader.subresourceRange.levelCount = 1U;
    finalToShader.subresourceRange.baseArrayLayer = 0U;
    finalToShader.subresourceRange.layerCount = 1U;
    finalToShader.srcAccessMask =
        VK_ACCESS_TRANSFER_WRITE_BIT;
    finalToShader.dstAccessMask =
        VK_ACCESS_SHADER_READ_BIT;

    vkCmdPipelineBarrier(
        command,
        VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT,
        0U,
        0U, nullptr,
        0U, nullptr,
        1U, &finalToShader);

    if (!queueUploadCommands(
            command,
            staging,
            stagingMemory,
            pixelBytes)) {
        destroyTexture(out);
        return false;
    }

    VkImageViewCreateInfo viewInfo{
        VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO
    };
    viewInfo.image = out.image;
    viewInfo.viewType =
        VK_IMAGE_VIEW_TYPE_2D;
    viewInfo.format = textureFormat;
    viewInfo.subresourceRange.aspectMask =
        VK_IMAGE_ASPECT_COLOR_BIT;
    viewInfo.subresourceRange.baseMipLevel = 0U;
    viewInfo.subresourceRange.levelCount =
        mipLevels;
    viewInfo.subresourceRange.baseArrayLayer = 0U;
    viewInfo.subresourceRange.layerCount = 1U;

    if (!ok(
            vkCreateImageView(
                device_,
                &viewInfo,
                nullptr,
                &out.view))) {
        discardPendingUploads();
        destroyTexture(out);
        return false;
    }

    if (!createTextureSampler(
            mipLevels,
            out)) {
        discardPendingUploads();
        destroyTexture(out);
        return false;
    }

    out.assetPath = assetPath;
    out.width =
        static_cast<std::uint32_t>(width);
    out.height =
        static_cast<std::uint32_t>(height);
    out.residentWidth = out.width;
    out.residentHeight = out.height;
    out.mipLevels = mipLevels;
    out.residentBaseMip = 0U;
    out.sourceMipLevels =
        std::min<std::uint32_t>(
            mipLevels,
            static_cast<std::uint32_t>(
                kMaxStreamedTextureMips));
    out.sourceMipBytes.fill(0U);

    std::uint32_t mipWidth =
        out.width;
    std::uint32_t mipHeight =
        out.height;

    for (std::uint32_t mip = 0U;
         mip < out.sourceMipLevels;
         ++mip) {
        out.sourceMipBytes[mip] =
            std::max<std::uint64_t>(
                1U,
                static_cast<std::uint64_t>(
                    mipWidth) *
                static_cast<std::uint64_t>(
                    mipHeight) *
                4U);

        mipWidth =
            std::max<std::uint32_t>(
                1U,
                mipWidth / 2U);
        mipHeight =
            std::max<std::uint32_t>(
                1U,
                mipHeight / 2U);
    }

    out.residentPayloadBytes =
        static_cast<std::uint64_t>(
            pixelBytes);
    out.allocationBytes =
        static_cast<std::uint64_t>(
            requirements.size);

    return true;
}

bool VulkanStaticMeshRenderer::createMaterialDescriptor(
    GpuMaterial& material) noexcept {
    if (descriptorPool_ == VK_NULL_HANDLE ||
        descriptorSetLayout_ == VK_NULL_HANDLE ||
        material.albedoTextureIndex >= textures_.size() ||
        material.normalTextureIndex >= textures_.size() ||
        material.ormTextureIndex >= textures_.size() ||
        material.emissiveTextureIndex >= textures_.size()) {
        return false;
    }

    std::array<VkDescriptorSetLayout, kDescriptorFrames>
        layouts{};
    layouts.fill(
        descriptorSetLayout_);

    VkDescriptorSetAllocateInfo allocation{
        VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO
    };
    allocation.descriptorPool = descriptorPool_;
    allocation.descriptorSetCount =
        kDescriptorFrames;
    allocation.pSetLayouts =
        layouts.data();

    material.descriptorSets.fill(
        VK_NULL_HANDLE);

    if (!ok(
            vkAllocateDescriptorSets(
                device_,
                &allocation,
                material.descriptorSets.data()))) {
        material.descriptorSets.fill(
            VK_NULL_HANDLE);
        return false;
    }

    const std::array<std::uint32_t, 4> indices{{
        material.albedoTextureIndex,
        material.normalTextureIndex,
        material.ormTextureIndex,
        material.emissiveTextureIndex,
    }};

    std::array<VkDescriptorImageInfo, 4> images{};

    for (std::uint32_t binding = 0U;
         binding < indices.size();
         ++binding) {
        const auto& texture =
            textures_[indices[binding]];

        images[binding].sampler =
            texture.sampler;
        images[binding].imageView =
            texture.view;
        images[binding].imageLayout =
            VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;
    }

    for (std::uint32_t frame = 0U;
         frame < kDescriptorFrames;
         ++frame) {
        std::array<VkWriteDescriptorSet, 4>
            writes{};

        for (std::uint32_t binding = 0U;
             binding < indices.size();
             ++binding) {
            writes[binding] = {
                VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET
            };
            writes[binding].dstSet =
                material.descriptorSets[frame];
            writes[binding].dstBinding =
                binding;
            writes[binding].descriptorCount =
                1U;
            writes[binding].descriptorType =
                VK_DESCRIPTOR_TYPE_COMBINED_IMAGE_SAMPLER;
            writes[binding].pImageInfo =
                &images[binding];
        }

        vkUpdateDescriptorSets(
            device_,
            static_cast<std::uint32_t>(
                writes.size()),
            writes.data(),
            0U,
            nullptr);
    }

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

bool VulkanStaticMeshRenderer::queueUploadCommands(
    VkCommandBuffer command,
    VkBuffer stagingBuffer,
    VkDeviceMemory stagingMemory,
    VkDeviceSize stagingBytes) noexcept {
    constexpr VkDeviceSize kSoftBatchLimit =
        96ULL * 1024ULL * 1024ULL;

    const auto releaseCurrent =
        [&]() noexcept {
            if (command != VK_NULL_HANDLE) {
                vkFreeCommandBuffers(
                    device_,
                    commandPool_,
                    1U,
                    &command);
            }
            if (stagingBuffer != VK_NULL_HANDLE) {
                vkDestroyBuffer(
                    device_,
                    stagingBuffer,
                    nullptr);
            }
            if (stagingMemory != VK_NULL_HANDLE) {
                vkFreeMemory(
                    device_,
                    stagingMemory,
                    nullptr);
            }
        };

    if (command == VK_NULL_HANDLE ||
        stagingBuffer == VK_NULL_HANDLE ||
        stagingMemory == VK_NULL_HANDLE ||
        stagingBytes == 0U) {
        releaseCurrent();
        return false;
    }

    if (!pendingUploads_.empty() &&
        (pendingUploads_.size() >=
             std::max<std::uint32_t>(
                 uploadBatchCommandLimit_,
                 1U) ||
         pendingUploadBytes_ >
             kSoftBatchLimit ||
         stagingBytes >
             kSoftBatchLimit -
                 std::min(
                     pendingUploadBytes_,
                     kSoftBatchLimit))) {
        if (!flushPendingUploads()) {
            releaseCurrent();
            return false;
        }
    }

    if (!ok(
            vkEndCommandBuffer(
                command))) {
        releaseCurrent();
        return false;
    }

    try {
        pendingUploads_.push_back({
            .command = command,
            .stagingBuffer = stagingBuffer,
            .stagingMemory = stagingMemory,
            .stagingBytes = stagingBytes,
        });
    } catch (...) {
        releaseCurrent();
        return false;
    }

    if (stagingBytes >
        std::numeric_limits<VkDeviceSize>::max() -
            pendingUploadBytes_) {
        // The command is owned by the pending list now; discard all rather
        // than leaving a partially-accounted batch.
        discardPendingUploads();
        return false;
    }

    pendingUploadBytes_ +=
        stagingBytes;

    return true;
}

bool VulkanStaticMeshRenderer::flushPendingUploads() noexcept {
    if (pendingUploads_.empty()) {
        pendingUploadBytes_ = 0U;
        return true;
    }

    std::vector<VkCommandBuffer> commands;

    try {
        commands.reserve(
            pendingUploads_.size());

        for (const auto& upload :
             pendingUploads_) {
            commands.push_back(
                upload.command);
        }
    } catch (...) {
        discardPendingUploads();
        return false;
    }

    VkSubmitInfo submit{
        VK_STRUCTURE_TYPE_SUBMIT_INFO
    };
    submit.commandBufferCount =
        static_cast<std::uint32_t>(
            commands.size());
    submit.pCommandBuffers =
        commands.data();

    const VkResult submitResult =
        vkQueueSubmit(
            graphicsQueue_,
            1U,
            &submit,
            VK_NULL_HANDLE);

    VkResult waitResult =
        submitResult;

    if (ok(submitResult)) {
        waitResult =
            vkQueueWaitIdle(
                graphicsQueue_);

        if (!ok(waitResult)) {
            // Initialization is still single-threaded here. Make one best
            // effort device wait before tearing down resources referenced by
            // a failed queue wait.
            (void) vkDeviceWaitIdle(
                device_);
        }
    }

    const std::size_t commandCount =
        pendingUploads_.size();
    const VkDeviceSize batchBytes =
        pendingUploadBytes_;

    for (auto& upload : pendingUploads_) {
        if (upload.command != VK_NULL_HANDLE) {
            vkFreeCommandBuffers(
                device_,
                commandPool_,
                1U,
                &upload.command);
        }
        if (upload.stagingBuffer != VK_NULL_HANDLE) {
            vkDestroyBuffer(
                device_,
                upload.stagingBuffer,
                nullptr);
        }
        if (upload.stagingMemory != VK_NULL_HANDLE) {
            vkFreeMemory(
                device_,
                upload.stagingMemory,
                nullptr);
        }
    }

    pendingUploads_.clear();
    pendingUploadBytes_ = 0U;

    if (!ok(submitResult) ||
        !ok(waitResult)) {
        return false;
    }

    __android_log_print(
        ANDROID_LOG_INFO,
        kTag,
        "XZIEL_TEXTURE_UPLOAD_BATCH commands=%u limit=%u staging_mb=%.2f",
        static_cast<unsigned int>(
            commandCount),
        static_cast<unsigned int>(
            uploadBatchCommandLimit_),
        static_cast<double>(
            batchBytes) /
            (1024.0 * 1024.0));

    return true;
}

void VulkanStaticMeshRenderer::discardPendingUploads() noexcept {
    if (device_ == VK_NULL_HANDLE) {
        pendingUploads_.clear();
        pendingUploadBytes_ = 0U;
        return;
    }

    for (auto& upload : pendingUploads_) {
        if (upload.command != VK_NULL_HANDLE) {
            vkFreeCommandBuffers(
                device_,
                commandPool_,
                1U,
                &upload.command);
        }
        if (upload.stagingBuffer != VK_NULL_HANDLE) {
            vkDestroyBuffer(
                device_,
                upload.stagingBuffer,
                nullptr);
        }
        if (upload.stagingMemory != VK_NULL_HANDLE) {
            vkFreeMemory(
                device_,
                upload.stagingMemory,
                nullptr);
        }
    }

    pendingUploads_.clear();
    pendingUploadBytes_ = 0U;
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

void VulkanStaticMeshRenderer::destroyGeometryResidency() noexcept {
    batches_.clear();

    if (device_ != VK_NULL_HANDLE) {
        if (geometryIndexBuffer_ != VK_NULL_HANDLE) {
            vkDestroyBuffer(
                device_,
                geometryIndexBuffer_,
                nullptr);
        }

        if (geometryIndexMemory_ != VK_NULL_HANDLE) {
            vkFreeMemory(
                device_,
                geometryIndexMemory_,
                nullptr);
        }

        if (geometryVertexBuffer_ != VK_NULL_HANDLE) {
            vkDestroyBuffer(
                device_,
                geometryVertexBuffer_,
                nullptr);
        }

        if (geometryVertexMemory_ != VK_NULL_HANDLE) {
            vkFreeMemory(
                device_,
                geometryVertexMemory_,
                nullptr);
        }
    }

    geometryVertexBuffer_ =
        VK_NULL_HANDLE;
    geometryVertexMemory_ =
        VK_NULL_HANDLE;
    geometryIndexBuffer_ =
        VK_NULL_HANDLE;
    geometryIndexMemory_ =
        VK_NULL_HANDLE;
    geometryDeviceLocalHostVisible_ = false;
    geometryVertexBytes_ = 0U;
    geometryIndexBytes_ = 0U;
}

} // namespace xziel::android
