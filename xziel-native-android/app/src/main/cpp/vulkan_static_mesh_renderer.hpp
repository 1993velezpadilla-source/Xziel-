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
        AAssetManager* assetManager,
        const char* modelAssetPath) noexcept;

    void shutdown() noexcept;

    [[nodiscard]] bool ready() const noexcept;
    [[nodiscard]] std::uint32_t batchCount() const noexcept;
    [[nodiscard]] std::uint32_t totalVertices() const noexcept;
    [[nodiscard]] std::uint32_t totalIndices() const noexcept;

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
        VkDescriptorSet descriptorSet = VK_NULL_HANDLE;
        std::uint32_t width = 0U;
        std::uint32_t height = 0U;
    };

    struct GpuBatch {
        VkBuffer vertexBuffer = VK_NULL_HANDLE;
        VkDeviceMemory vertexMemory = VK_NULL_HANDLE;
        VkBuffer indexBuffer = VK_NULL_HANDLE;
        VkDeviceMemory indexMemory = VK_NULL_HANDLE;
        std::uint32_t indexCount = 0U;
        std::uint32_t textureIndex = 0U;
        StaticMeshBounds bounds{};
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
    };

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

    [[nodiscard]] bool uploadBatch(
        const StaticMeshBatch& batch,
        std::uint32_t textureIndex,
        GpuBatch& out) noexcept;

    [[nodiscard]] bool createTexture(
        AAssetManager* assetManager,
        const std::string& assetPath,
        GpuTexture& out) noexcept;

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
    void destroyBatch(GpuBatch& batch) noexcept;

    VkPhysicalDevice physicalDevice_ = VK_NULL_HANDLE;
    VkDevice device_ = VK_NULL_HANDLE;
    VkQueue graphicsQueue_ = VK_NULL_HANDLE;
    std::uint32_t graphicsQueueFamily_ = UINT32_MAX;
    VkCommandPool commandPool_ = VK_NULL_HANDLE;
    VkRenderPass renderPass_ = VK_NULL_HANDLE;

    VkDescriptorSetLayout descriptorSetLayout_ = VK_NULL_HANDLE;
    VkDescriptorPool descriptorPool_ = VK_NULL_HANDLE;
    VkPipelineLayout pipelineLayout_ = VK_NULL_HANDLE;
    VkPipeline pipeline_ = VK_NULL_HANDLE;

    std::vector<GpuTexture> textures_{};
    std::vector<GpuBatch> batches_{};

    std::uint32_t totalVertices_ = 0U;
    std::uint32_t totalIndices_ = 0U;
    bool samplerAnisotropyEnabled_ = false;
    float maxSamplerAnisotropy_ = 1.0f;
    bool ready_ = false;
};

} // namespace xziel::android
