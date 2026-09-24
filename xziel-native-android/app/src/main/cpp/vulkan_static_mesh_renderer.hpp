#pragma once

#include <android/asset_manager.h>
#include <vulkan/vulkan.h>

#include "android_asset_streamer.hpp"
#include "xziel/static_mesh.hpp"
#include "xziel/world_streaming.hpp"

#include <cstdint>
#include <string>
#include <vector>

namespace xziel::android {

struct StaticMeshCameraState {
    float x = 0.0f;
    float y = 0.0f;
    float z = 0.0f;
    float yawRadians = 0.0f;
    float pitchRadians = 0.0f;
    float verticalFovDegrees = 72.0f;
    float aspect = 1.0f;
};

struct StaticMeshEnvironmentState {
    float fogDensity = 0.0f;
    float lightningFlash = 0.0f;
    MemoryPressure memoryPressure =
        MemoryPressure::Normal;
};

struct StaticMeshFrameStats {
    std::uint32_t visibleBatches = 0U;
    std::uint32_t culledBatches = 0U;
    // Logical visible mesh draws. This stays comparable across direct and
    // multi-draw-indirect paths.
    std::uint32_t drawCalls = 0U;
    // Actual Vulkan draw commands recorded into the command buffer.
    std::uint32_t drawSubmissions = 0U;
    // Logical draws carried by vkCmdDrawIndexedIndirect submissions.
    std::uint32_t indirectDraws = 0U;
    std::uint32_t materialBinds = 0U;
    std::uint32_t geometryBinds = 0U;
    std::uint32_t pipelineBinds = 0U;
    std::uint32_t submissionGroups = 0U;
    std::uint64_t submittedTriangles = 0U;
    std::uint32_t cellFrustumTests = 0U;
    std::uint32_t cellFrustumCulled = 0U;
    std::uint32_t cellRangeSkippedBatches = 0U;
    std::uint32_t cellFrustumSkippedBatches = 0U;
    std::uint32_t batchFrustumTests = 0U;

    std::uint32_t streamingCell = 0U;
    std::uint32_t streamingColdBatches = 0U;
    std::uint32_t streamingCulledBatches = 0U;
    std::uint32_t streamingHotResources = 0U;
    std::uint32_t streamingPreloadResources = 0U;
    std::uint64_t streamingEvictableBytes = 0U;
};

struct StaticMeshViewmodelState {
    float x = 0.0f;
    float y = -0.18f;
    float z = 0.18f;
    float scale = 1.0f;

    float yawRadians = 0.0f;
    float pitchRadians = 0.0f;
    float rollRadians = 0.0f;

    float verticalFovDegrees = 72.0f;
    float aspect = 1.0f;
};

class VulkanStaticMeshRenderer final {
public:
    VulkanStaticMeshRenderer() = default;
    ~VulkanStaticMeshRenderer();

    VulkanStaticMeshRenderer(
        const VulkanStaticMeshRenderer&) = delete;
    VulkanStaticMeshRenderer& operator=(
        const VulkanStaticMeshRenderer&) = delete;

    [[nodiscard]] bool initialize(
        VkPhysicalDevice physicalDevice,
        VkDevice device,
        VkQueue graphicsQueue,
        std::uint32_t graphicsQueueFamily,
        VkCommandPool commandPool,
        VkRenderPass renderPass,
        VkSampleCountFlagBits sampleCount,
        AAssetManager* assetManager,
        const char* modelAssetPath) noexcept;

    void shutdown() noexcept;

    [[nodiscard]] bool ready() const noexcept;
    [[nodiscard]] std::uint32_t batchCount() const noexcept;
    [[nodiscard]] std::uint32_t totalVertices() const noexcept;
    [[nodiscard]] std::uint32_t totalIndices() const noexcept;
    [[nodiscard]] StaticMeshFrameStats frameStats() const noexcept;

    void setStreamingPortalOpen(
        std::uint32_t portalId,
        bool open) noexcept;

    void record(
        VkCommandBuffer command,
        VkExtent2D extent,
        std::uint32_t frameSlot,
        const StaticMeshCameraState& camera,
        const StaticMeshEnvironmentState& environment) noexcept;

    void recordViewmodel(
        VkCommandBuffer command,
        VkExtent2D extent,
        std::uint32_t frameSlot,
        const StaticMeshViewmodelState& state) const noexcept;

private:
    static constexpr std::uint32_t
        kDescriptorFrames = 2U;

    struct GpuTexture {
        std::string assetPath{};
        std::uint64_t streamResourceId = 0U;
        VkImage image = VK_NULL_HANDLE;
        VkDeviceMemory memory = VK_NULL_HANDLE;
        VkImageView view = VK_NULL_HANDLE;
        VkSampler sampler = VK_NULL_HANDLE;
        std::uint32_t width = 0U;
        std::uint32_t height = 0U;
        std::uint32_t residentWidth = 0U;
        std::uint32_t residentHeight = 0U;
        std::uint32_t mipLevels = 0U;
        std::uint32_t residentBaseMip = 0U;
        std::uint32_t sourceMipLevels = 0U;
        std::array<std::uint64_t, kMaxStreamedTextureMips>
            sourceMipBytes{};
        std::uint64_t residentPayloadBytes = 0U;
        std::uint64_t allocationBytes = 0U;
        bool srgb = false;
        bool physicallyResident = true;
        bool runtimeLoadQueued = false;
        std::uint8_t descriptorResidentMask = 0x3U;
    };

    struct RuntimeTextureUpload {
        std::uint32_t textureIndex = UINT32_MAX;
        std::uint32_t targetBaseMip = 0U;
        GpuTexture replacement{};
        VkCommandBuffer command = VK_NULL_HANDLE;
        VkBuffer stagingBuffer = VK_NULL_HANDLE;
        VkDeviceMemory stagingMemory = VK_NULL_HANDLE;
        VkFence fence = VK_NULL_HANDLE;
        std::uint8_t descriptorSwapMask = 0U;
        bool uploadComplete = false;
        bool active = false;
    };

    struct GpuMaterial {
        std::uint64_t streamResourceId = 0U;
        std::uint32_t albedoTextureIndex = 0U;
        std::uint32_t normalTextureIndex = 0U;
        std::uint32_t ormTextureIndex = 0U;
        std::uint32_t emissiveTextureIndex = 0U;
        std::array<VkDescriptorSet, 2> descriptorSets{
            VK_NULL_HANDLE,
            VK_NULL_HANDLE};

        std::array<float, 4> baseColorFactor{
            1.0f, 1.0f, 1.0f, 1.0f};
        float metallicFactor = 0.0f;
        float roughnessFactor = 1.0f;
        std::array<float, 3> emissiveFactor{
            0.0f, 0.0f, 0.0f};
        float normalScale = 1.0f;
        float occlusionStrength = 1.0f;

        bool pbrEnabled = false;
        bool hasNormalTexture = false;
        bool hasOrmTexture = false;
        bool hasEmissiveTexture = false;
    };

    struct PendingUpload {
        VkCommandBuffer command = VK_NULL_HANDLE;
        VkBuffer stagingBuffer = VK_NULL_HANDLE;
        VkDeviceMemory stagingMemory = VK_NULL_HANDLE;
        VkDeviceSize stagingBytes = 0U;
    };

    struct StreamCellBounds {
        std::uint32_t cellId = 0U;
        StaticMeshBounds bounds{};
        float cullCenterX = 0.0f;
        float cullCenterY = 0.0f;
        float cullCenterZ = 0.0f;
        float cullRadius = 0.0f;
        bool valid = false;
    };

    static constexpr std::size_t
        kGeometryReloadWindow = 4U;

    static constexpr VkDeviceSize
        kGeometryRestorePreloadBudgetBytes =
            2ULL * 1024ULL * 1024ULL;
    static constexpr VkDeviceSize
        kGeometryRestoreHotBudgetBytes =
            4ULL * 1024ULL * 1024ULL;

    enum class GeometryRestoreResult : std::uint8_t {
        InProgress,
        Complete,
        Failed,
    };

    struct GeometryRangeInFlight {
        std::uint32_t batchIndex = UINT32_MAX;
        std::string key{};
        std::vector<std::byte> readyBytes{};
        std::size_t copyCursor = 0U;
        bool resultReady = false;
        bool active = false;
    };

    struct GeometryCellResidency {
        std::uint32_t cellId = 0U;
        VkBuffer vertexBuffer = VK_NULL_HANDLE;
        VkDeviceMemory vertexMemory = VK_NULL_HANDLE;
        VkBuffer indexBuffer = VK_NULL_HANDLE;
        VkDeviceMemory indexMemory = VK_NULL_HANDLE;
        VkDeviceSize vertexBytes = 0U;
        VkDeviceSize indexBytes = 0U;
        std::uint32_t vertexCount = 0U;
        std::uint32_t indexCount = 0U;
        std::uint32_t firstBatch = UINT32_MAX;
        std::uint32_t batchCount = 0U;
        bool deviceLocalHostVisible = false;
        bool pinned = false;
        bool physicallyResident = false;
        StreamCellHeat heat = StreamCellHeat::Cold;
        std::uint8_t retireMask = 0U;
        bool reloadActive = false;
        bool reloadFailed = false;
        bool budgetBlockedLogged = false;
        std::size_t reloadScanCursor = 0U;
        std::array<
            GeometryRangeInFlight,
            kGeometryReloadWindow> reloadRanges{};
        std::uint32_t reloadPendingCount = 0U;
        std::uint32_t reloadPeakPendingCount = 0U;
        VkDeviceSize reloadPeakCopyBytesPerFrame = 0U;
        std::uint64_t reloadStartFrame = 0U;
        std::vector<std::byte> reloadVertexBytes{};
        std::vector<std::byte> reloadIndexBytes{};

        // GPU restoration is intentionally split across frames. The APK range
        // reads may finish together, but copying an entire streamed cell into
        // mapped Vulkan memory in one render frame can create a visible hitch.
        void* restoreMappedVertices = nullptr;
        void* restoreMappedIndices = nullptr;
        VkDeviceSize restoreVertexCursor = 0U;
        VkDeviceSize restoreIndexCursor = 0U;
        std::uint32_t restoreCopyFrames = 0U;
        bool restorePrepared = false;
    };

    struct GpuBatch {
        std::uint64_t streamResourceId = 0U;
        std::uint32_t streamCellId = 0U;
        std::uint32_t geometryCellSlot = UINT32_MAX;
        std::uint32_t sourceBatchIndex = UINT32_MAX;
        std::uint32_t firstIndex = 0U;
        std::int32_t vertexOffset = 0;
        std::uint32_t indexCount = 0U;
        std::uint32_t materialIndex = 0U;
        StaticMeshBounds bounds{};

        // Derived once when the XZSM is uploaded. Frustum culling touches every
        // batch every frame, so keep its sphere out of the hot loop.
        float cullCenterX = 0.0f;
        float cullCenterY = 0.0f;
        float cullCenterZ = 0.0f;
        float cullRadius = 0.0f;

        bool doubleSided = true;
    };

    struct IndirectDrawFrame {
        VkBuffer buffer = VK_NULL_HANDLE;
        VkDeviceMemory memory = VK_NULL_HANDLE;
        void* mapped = nullptr;
        VkDeviceSize bytes = 0U;
    };

    struct StaticDrawGroup {
        std::uint32_t firstCommand = 0U;
        std::uint32_t commandCount = 0U;
        std::uint32_t materialIndex = UINT32_MAX;
        std::uint32_t geometryCellSlot = UINT32_MAX;
        bool doubleSided = true;
    };

    struct PushConstants {
        float cameraX = 0.0f;
        float cameraY = 0.0f;
        float cameraZ = 0.0f;
        float cameraYaw = 0.0f;

        float cameraPitch = 0.0f;
        float verticalFovDegrees = 72.0f;
        float aspect = 1.0f;
        float fogDensity = 0.0f;

        float lightningFlash = 0.0f;
        float pad0 = 0.0f;
        float pad1 = 0.0f;
        float pad2 = 0.0f;

        float modelX = 0.0f;
        float modelY = 0.0f;
        float modelZ = 0.0f;
        float modelScale = 1.0f;

        float modelYaw = 0.0f;
        float modelPitch = 0.0f;
        float modelRoll = 0.0f;
        float viewmodelMode = 0.0f;

        float baseColorFactorR = 1.0f;
        float baseColorFactorG = 1.0f;
        float baseColorFactorB = 1.0f;
        float baseColorFactorA = 1.0f;

        float metallicFactor = 0.0f;
        float roughnessFactor = 1.0f;
        float normalScale = 1.0f;
        float occlusionStrength = 1.0f;

        float emissiveFactorR = 0.0f;
        float emissiveFactorG = 0.0f;
        float emissiveFactorB = 0.0f;
        float materialFlags = 0.0f;
    };

    static_assert(
        sizeof(PushConstants) == 128U,
        "static mesh push constants must fit Vulkan's guaranteed 128-byte minimum");

    [[nodiscard]] bool loadModel(
        AAssetManager* assetManager,
        const char* path,
        StaticMeshAsset& out) noexcept;

    [[nodiscard]] bool createPipeline(
        AAssetManager* assetManager) noexcept;

    [[nodiscard]] bool createBuffer(
        VkDeviceSize size,
        VkBufferUsageFlags usage,
        VkMemoryPropertyFlags memoryFlags,
        VkBuffer& buffer,
        VkDeviceMemory& memory) noexcept;

    [[nodiscard]] bool createGeometryResidency(
        const StaticMeshAsset& asset,
        const std::vector<std::uint32_t>& materialIndices) noexcept;

    [[nodiscard]] bool createTexture(
        AAssetManager* assetManager,
        const std::string& exportedName,
        bool srgb,
        GpuTexture& out) noexcept;

    [[nodiscard]] bool createPngTexture(
        AAssetManager* assetManager,
        const std::string& assetPath,
        bool srgb,
        GpuTexture& out) noexcept;

    [[nodiscard]] bool createKtx2Texture(
        AAssetManager* assetManager,
        const std::string& assetPath,
        bool srgb,
        GpuTexture& out) noexcept;

    [[nodiscard]] bool createTextureSampler(
        std::uint32_t mipLevels,
        GpuTexture& out) noexcept;

    [[nodiscard]] bool createMaterialDescriptor(
        GpuMaterial& material) noexcept;

    [[nodiscard]] bool createShaderModule(
        AAssetManager* assetManager,
        const char* path,
        VkShaderModule& out) noexcept;

    [[nodiscard]] bool findMemoryType(
        std::uint32_t typeBits,
        VkMemoryPropertyFlags required,
        std::uint32_t& outIndex) const noexcept;

    [[nodiscard]] VkCommandBuffer beginUploadCommands() noexcept;

    // Texture uploads are recorded independently but submitted together.
    // queueUploadCommands takes ownership of command + staging resources on
    // both success and failure.
    [[nodiscard]] bool queueUploadCommands(
        VkCommandBuffer command,
        VkBuffer stagingBuffer,
        VkDeviceMemory stagingMemory,
        VkDeviceSize stagingBytes) noexcept;

    [[nodiscard]] bool flushPendingUploads() noexcept;
    void discardPendingUploads() noexcept;

    void destroyTexture(GpuTexture& texture) noexcept;
    void destroyGeometryResidency() noexcept;

    [[nodiscard]] bool createIndirectDrawBuffers() noexcept;
    void destroyIndirectDrawBuffers() noexcept;

    static void cacheGpuBatchCullingSphere(
        GpuBatch& batch) noexcept;

    void rebuildStreamingCellBounds() noexcept;

    [[nodiscard]] std::uint32_t inferStreamingCell(
        const StaticMeshCameraState& camera) const noexcept;

    [[nodiscard]] const StreamCellResourceDecision*
    streamDecision(
        std::uint64_t resourceId,
        std::size_t count) const noexcept;

    [[nodiscard]] bool updateTextureDescriptorForFrame(
        std::uint32_t textureIndex,
        std::uint32_t frameSlot,
        std::uint32_t replacementTextureIndex) noexcept;

    [[nodiscard]] bool updateTextureDescriptorForFrame(
        std::uint32_t textureIndex,
        std::uint32_t frameSlot,
        const GpuTexture& replacement) noexcept;

    [[nodiscard]] std::uint64_t texturePayloadFromMip(
        const GpuTexture& texture,
        std::uint32_t baseMip) const noexcept;

    [[nodiscard]] bool materialStreamingReady(
        const GpuMaterial& material,
        std::uint32_t frameSlot) const noexcept;

    void releaseTextureGpuResidency(
        GpuTexture& texture) noexcept;

    void destroyRuntimeTextureUpload() noexcept;

    [[nodiscard]] bool beginRuntimeKtx2Upload(
        std::uint32_t textureIndex,
        std::uint32_t targetBaseMip,
        std::vector<std::byte>&& bytes) noexcept;

    void serviceRuntimeTextureResidency(
        std::uint32_t frameSlot,
        MemoryPressure memoryPressure) noexcept;

    void releaseGeometryCellGpuResidency(
        GeometryCellResidency& cell) noexcept;

    [[nodiscard]] GeometryRestoreResult
    restoreGeometryCellGpuResidency(
        GeometryCellResidency& cell,
        VkDeviceSize copyBudgetBytes) noexcept;

    void serviceRuntimeGeometryResidency(
        std::uint32_t frameSlot,
        const StreamCellPlanInput& input) noexcept;

    [[nodiscard]] std::string geometryRangeRequestKey(
        std::uint32_t cellSlot,
        std::uint32_t batchIndex) const;

    VkPhysicalDevice physicalDevice_ = VK_NULL_HANDLE;
    VkDevice device_ = VK_NULL_HANDLE;
    VkQueue graphicsQueue_ = VK_NULL_HANDLE;
    std::uint32_t graphicsQueueFamily_ = UINT32_MAX;
    VkCommandPool commandPool_ = VK_NULL_HANDLE;
    VkRenderPass renderPass_ = VK_NULL_HANDLE;
    VkSampleCountFlagBits sampleCount_ =
        VK_SAMPLE_COUNT_1_BIT;

    VkDescriptorSetLayout descriptorSetLayout_ = VK_NULL_HANDLE;
    VkDescriptorPool descriptorPool_ = VK_NULL_HANDLE;
    VkPipelineLayout pipelineLayout_ = VK_NULL_HANDLE;
    VkPipeline pipeline_ = VK_NULL_HANDLE;
    VkPipeline pipelineDoubleSided_ = VK_NULL_HANDLE;

    AndroidAssetStreamer assetStreamer_{};
    std::uint32_t asyncPrefetchQueued_ = 0U;

    StreamCellGraph streamGraph_{};
    TextureMipResidencyManager textureMipResidency_{
        1024U};
    bool streamGraphReady_ = false;
    std::array<StreamCellBounds, kMaxStreamCells>
        streamCellBounds_{};
    mutable std::array<
        StreamCellResourceDecision,
        kMaxStreamBindings> streamDecisions_{};
    mutable std::size_t streamDecisionCount_ = 0U;
    StreamCellPlanStats cachedStreamPlanStats_{};
    std::uint32_t cachedStreamPlanCell_ = 0U;
    MemoryPressure cachedStreamPlanPressure_ =
        MemoryPressure::Normal;
    std::uint32_t cachedStreamColdBatches_ = 0U;
    std::uint64_t streamPlanBuildCount_ = 0U;
    std::uint64_t streamPlanCacheHitCount_ = 0U;
    std::uint64_t streamCellHeatRefreshCount_ = 0U;
    bool streamPlanDirty_ = true;
    mutable std::uint64_t streamPlanFrame_ = 0U;
    mutable std::uint32_t lastLoggedStreamCell_ = 0U;
    mutable std::uint32_t streamCellCandidate_ = 0U;
    mutable std::uint32_t streamCellStableFrames_ = 0U;
    mutable bool streamCullingActive_ = false;
    mutable bool streamCullLogged_ = false;
    std::uint32_t streamFallbackTextureIndex_ = UINT32_MAX;
    RuntimeTextureUpload runtimeTextureUpload_{};
    std::uint64_t runtimeTextureTransitionFrame_ = 0U;
    bool streamResidencyProbeEnabled_ = false;
    bool streamResidencyProbeComplete_ = false;
    bool streamResidencyProbeReloadComplete_ = false;
    std::uint32_t streamResidencyProbeTextureIndex_ = UINT32_MAX;
    std::uint64_t streamResidencyProbeReloadFrame_ = 0U;

    std::vector<GpuTexture> textures_{};
    std::vector<GpuMaterial> materials_{};
    std::vector<GpuBatch> batches_{};
    std::vector<VkDrawIndexedIndirectCommand> drawCommands_{};
    std::vector<StaticDrawGroup> drawGroups_{};
    std::array<IndirectDrawFrame, kDescriptorFrames>
        indirectDrawFrames_{};
    std::vector<PendingUpload> pendingUploads_{};
    VkDeviceSize pendingUploadBytes_ = 0U;
    std::uint32_t uploadBatchCommandLimit_ = 16U;
    std::uint64_t textureResidentBudgetBytes_ =
        128ULL * 1024ULL * 1024ULL;
    std::uint64_t textureResidentBytes_ = 0U;
    std::uint32_t textureDegradedCount_ = 0U;

    std::array<
        GeometryCellResidency,
        kMaxStreamCells + 1U> geometryCells_{};
    std::size_t geometryCellCount_ = 0U;
    VkDeviceSize geometryCellVertexBytes_ = 0U;
    VkDeviceSize geometryCellIndexBytes_ = 0U;
    StaticMeshDirectory geometryDirectory_{};
    std::string geometryAssetPath_{};
    std::uint32_t geometryReloadCellSlot_ = UINT32_MAX;
    std::uint64_t geometryResidentBudgetBytes_ =
        96ULL * 1024ULL * 1024ULL;
    std::uint64_t geometryResidentBytes_ = 0U;
    bool geometryResidencyProbeEnabled_ = false;
    bool geometryResidencyProbeComplete_ = false;
    std::uint32_t geometryResidencyProbeCellSlot_ = UINT32_MAX;
    std::uint64_t geometryResidencyProbeReloadFrame_ = 0U;

    VkBuffer geometryVertexBuffer_ = VK_NULL_HANDLE;
    VkDeviceMemory geometryVertexMemory_ = VK_NULL_HANDLE;
    VkBuffer geometryIndexBuffer_ = VK_NULL_HANDLE;
    VkDeviceMemory geometryIndexMemory_ = VK_NULL_HANDLE;
    bool geometryDeviceLocalHostVisible_ = false;
    VkDeviceSize geometryVertexBytes_ = 0U;
    VkDeviceSize geometryIndexBytes_ = 0U;

    std::uint32_t totalVertices_ = 0U;
    std::uint32_t totalIndices_ = 0U;
    bool samplerAnisotropyEnabled_ = false;
    bool astcLdrSupported_ = false;
    bool multiDrawIndirectEnabled_ = false;
    std::uint32_t maxDrawIndirectCount_ = 1U;
    float maxSamplerAnisotropy_ = 1.0f;
    mutable StaticMeshFrameStats frameStats_{};
    bool ready_ = false;
};

} // namespace xziel::android
