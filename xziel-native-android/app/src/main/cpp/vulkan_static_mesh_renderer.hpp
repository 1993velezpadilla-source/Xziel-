#pragma once

#include <android/asset_manager.h>
#include <vulkan/vulkan.h>

#include "xziel/static_mesh.hpp"

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
};

struct StaticMeshFrameStats {
    std::uint32_t visibleBatches = 0U;
    std::uint32_t culledBatches = 0U;
    std::uint32_t drawCalls = 0U;
    std::uint64_t submittedTriangles = 0U;
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

    void record(
        VkCommandBuffer command,
        VkExtent2D extent,
        const StaticMeshCameraState& camera,
        const StaticMeshEnvironmentState& environment) const noexcept;

    void recordViewmodel(
        VkCommandBuffer command,
        VkExtent2D extent,
        const StaticMeshViewmodelState& state) const noexcept;

private:
    struct GpuTexture {
        std::string assetPath{};
        VkImage image = VK_NULL_HANDLE;
        VkDeviceMemory memory = VK_NULL_HANDLE;
        VkImageView view = VK_NULL_HANDLE;
        VkSampler sampler = VK_NULL_HANDLE;
        std::uint32_t width = 0U;
        std::uint32_t height = 0U;
    };

    struct GpuMaterial {
        std::uint32_t albedoTextureIndex = 0U;
        std::uint32_t normalTextureIndex = 0U;
        std::uint32_t ormTextureIndex = 0U;
        std::uint32_t emissiveTextureIndex = 0U;
        VkDescriptorSet descriptorSet = VK_NULL_HANDLE;

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

    struct GpuBatch {
        std::uint32_t firstIndex = 0U;
        std::int32_t vertexOffset = 0;
        std::uint32_t indexCount = 0U;
        std::uint32_t materialIndex = 0U;
        StaticMeshBounds bounds{};
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
        const std::string& assetPath,
        bool srgb,
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
    [[nodiscard]] bool endUploadCommands(
        VkCommandBuffer command) noexcept;

    void destroyTexture(GpuTexture& texture) noexcept;
    void destroyGeometryResidency() noexcept;

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

    std::vector<GpuTexture> textures_{};
    std::vector<GpuMaterial> materials_{};
    std::vector<GpuBatch> batches_{};

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
    float maxSamplerAnisotropy_ = 1.0f;
    mutable StaticMeshFrameStats frameStats_{};
    bool ready_ = false;
};

} // namespace xziel::android
