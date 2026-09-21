#pragma once

#include <android/asset_manager.h>
#include <android/native_window.h>
#include <jni.h>
#include <vulkan/vulkan.h>

#include <array>
#include <cstdint>
#include <vector>

namespace xziel::android {

struct VulkanCamera {
    float x = 0.0f;
    float y = 0.14f;
    float z = -2.55f;

    float yawRadians = 0.0f;
    float pitchRadians = 0.0f;
    float verticalFovDegrees = 72.0f;
};

struct VulkanZombieState {
    float x = 0.0f;
    float y = -1.48f;
    float z = 2.45f;

    float yawRadians = 0.0f;
    float stridePhase = 0.0f;
    float healthRatio = 1.0f;

    bool visible = false;
    bool staggered = false;
    bool attack = false;
};

struct VulkanSceneState {
    std::array<VulkanZombieState, 8> zombies{};
    std::size_t zombieCount = 0;

    float roundProgress = 0.0f;
    bool interRound = false;

    float impactX = 0.0f;
    float impactY = 0.0f;
    float impactZ = 0.0f;
    float impactAlpha = 0.0f;
    bool impactCritical = false;

    float decapOriginX = 0.0f;
    float decapOriginY = 0.0f;
    float decapOriginZ = 0.0f;

    float decapDirectionX = 0.0f;
    float decapDirectionY = 0.0f;
    float decapDirectionZ = 1.0f;

    float decapAlpha = 0.0f;

    float interactionX = 0.0f;
    float interactionY = 0.0f;
    float interactionZ = 0.0f;

    bool interactionVisible = false;
    bool interactionActive = false;

    float doorOpenAlpha = 0.0f;
};

struct VulkanEnvironmentState {
    float rainIntensity = 0.0f;
    float fogDensity = 0.0f;
    float lightningFlash = 0.0f;
    float wetness = 0.0f;

    float windX = 0.0f;
    float windZ = 0.0f;

    float particleDensityScale = 1.0f;
    float fogQualityScale = 1.0f;
    float postProcessScale = 1.0f;

    float waterWavePhase = 0.0f;
    float waterFoamStrength = 0.0f;
    float waterReflectionStrength = 0.0f;
    float waterRefractionStrength = 0.0f;
    float waterRoughness = 0.10f;

    // Explicit reflection workload controls carried from PerformanceGovernor
    // into the Vulkan backend. The renderer can now decide whether an
    // offscreen planar pass is legal without guessing from visual quality.
    std::uint32_t maxPlanarReflectionPasses = 0;
    float planarReflectionScale = 0.0f;
    float reflectionDistanceMeters = 0.0f;
    bool ssrEnabled = false;
    float ssrResolutionScale = 0.0f;
    std::uint32_t ssrMaxSteps = 0;
};

struct VulkanHudState {
    float moveX = 0.0f;
    float moveY = 0.0f;

    float moveAnchorX = 0.17f;
    float moveAnchorY = 0.78f;

    bool moveActive = false;
    bool fire = false;
    bool aim = false;
    bool reload = false;
    bool jump = false;
    bool stance = false;
    bool gyroAvailable = false;

    bool interactAvailable = false;
    bool interactHeld = false;
    float interactProgress = 0.0f;

    std::uint32_t interactionCost = 0;
    bool interactionAffordable = true;
    float interactionDeniedAlpha = 0.0f;

    float hitMarkerAlpha = 0.0f;
    float criticalHitAlpha = 0.0f;
    bool targetAlive = true;

    float weaponAdsAlpha = 0.0f;
    float weaponReloadAlpha = 0.0f;
    float weaponFireAlpha = 0.0f;
    float weaponMagazineRatio = 1.0f;
    float viewmodelLowering = 0.0f;

    float playerHealthRatio = 1.0f;
    float damageFlashAlpha = 0.0f;
    float deathAlpha = 0.0f;
    float horrorVignette = 0.0f;

    std::uint64_t scoreTotal = 0;
    float scorePulseAlpha = 0.0f;
};

class VulkanClearRenderer final {
public:
    VulkanClearRenderer() = default;
    ~VulkanClearRenderer();

    VulkanClearRenderer(const VulkanClearRenderer&) = delete;
    VulkanClearRenderer& operator=(const VulkanClearRenderer&) = delete;

    [[nodiscard]] bool initialize(
        ANativeWindow* window,
        AAssetManager* assetManager,
        JNIEnv* env,
        jobject javaActivity) noexcept;

    void shutdown() noexcept;

    void setPreferredFrameRate(
        float framesPerSecond) noexcept;

    [[nodiscard]] bool drawFrame(
        float timeSeconds,
        const VulkanCamera& camera,
        const VulkanHudState& hud,
        const VulkanSceneState& scene,
        const VulkanEnvironmentState& environment) noexcept;
    [[nodiscard]] bool ready() const noexcept;

private:
    struct FrameSync {
        VkSemaphore imageAvailable = VK_NULL_HANDLE;
        VkSemaphore renderFinished = VK_NULL_HANDLE;
        VkFence inFlight = VK_NULL_HANDLE;
    };

    struct UiPushConstants {
        float centerX = 0.0f;
        float centerY = 0.0f;
        float halfWidth = 0.1f;
        float halfHeight = 0.1f;

        float colorR = 1.0f;
        float colorG = 1.0f;
        float colorB = 1.0f;
        float colorA = 1.0f;

        float shape = 0.0f;
        float ringWidth = 0.15f;
        float padding0 = 0.0f;
        float padding1 = 0.0f;
    };

    struct PushConstants {
        float timeSeconds = 0.0f;
        float aspect = 1.0f;
        float horrorPulse = 0.0f;
        float materialId = 0.0f;

        float translationX = 0.0f;
        float translationY = 0.0f;
        float translationZ = 0.0f;
        float translationPadding = 0.0f;

        float scaleX = 1.0f;
        float scaleY = 1.0f;
        float scaleZ = 1.0f;
        float scalePadding = 0.0f;

        float cameraX = 0.0f;
        float cameraY = 0.14f;
        float cameraZ = -2.55f;
        float cameraYawRadians = 0.0f;

        float cameraPitchRadians = 0.0f;
        float verticalFovDegrees = 72.0f;
        float cameraPadding0 = 0.0f;
        float cameraPadding1 = 0.0f;

        float fogDensity = 0.0f;
        float lightningFlash = 0.0f;
        float wetness = 0.0f;
        float rainIntensity = 0.0f;

        float waterWavePhase = 0.0f;
        float waterFoamStrength = 0.0f;
        float waterReflectionStrength = 0.0f;
        float waterRefractionStrength = 0.0f;

        float waterRoughness = 0.10f;
        float waterQualityScale = 1.0f;
        float waterParticleScale = 1.0f;
        float waterFogScale = 1.0f;
    };

    [[nodiscard]] bool createInstance() noexcept;
    [[nodiscard]] bool createSurface(ANativeWindow* window) noexcept;
    [[nodiscard]] bool selectPhysicalDevice() noexcept;
    [[nodiscard]] bool createDevice() noexcept;
    [[nodiscard]] bool createSwapchain() noexcept;
    [[nodiscard]] bool initializeFramePacing() noexcept;

    [[nodiscard]] bool chooseSurfaceFormat(
        VkSurfaceFormatKHR& out) const noexcept;

    [[nodiscard]] bool chooseDepthFormat(
        VkFormat& out) const noexcept;

    [[nodiscard]] bool findMemoryType(
        std::uint32_t typeBits,
        VkMemoryPropertyFlags required,
        std::uint32_t& outIndex) const noexcept;

    [[nodiscard]] bool createRenderPass() noexcept;
    [[nodiscard]] bool createGraphicsPipeline() noexcept;
    [[nodiscard]] bool createUiPipeline() noexcept;

    [[nodiscard]] bool createShaderModuleFromAsset(
        const char* assetPath,
        VkShaderModule& outModule) noexcept;

    [[nodiscard]] bool createImageViews() noexcept;
    [[nodiscard]] bool createDepthResources() noexcept;
    [[nodiscard]] bool createReflectionTarget(
        float resolutionScale) noexcept;
    [[nodiscard]] bool createReflectionPassResources() noexcept;
    void destroyReflectionPassResources() noexcept;
    void destroyReflectionTarget() noexcept;
    [[nodiscard]] bool createFramebuffers() noexcept;
    [[nodiscard]] bool createCommandResources() noexcept;
    [[nodiscard]] bool createSyncObjects() noexcept;

    void destroySwapchainResources() noexcept;

    [[nodiscard]] bool recreateSwapchain() noexcept;

    [[nodiscard]] bool recordDrawCommand(
        std::uint32_t imageIndex,
        float timeSeconds,
        const VulkanCamera& camera,
        const VulkanHudState& hud,
        const VulkanSceneState& scene,
        const VulkanEnvironmentState& environment) noexcept;

    VkInstance instance_ = VK_NULL_HANDLE;
    VkSurfaceKHR surface_ = VK_NULL_HANDLE;
    VkPhysicalDevice physicalDevice_ = VK_NULL_HANDLE;
    VkDevice device_ = VK_NULL_HANDLE;

    std::uint32_t graphicsQueueFamily_ = UINT32_MAX;
    VkQueue graphicsQueue_ = VK_NULL_HANDLE;

    VkSwapchainKHR swapchain_ = VK_NULL_HANDLE;
    VkFormat swapchainFormat_ = VK_FORMAT_UNDEFINED;
    VkFormat depthFormat_ = VK_FORMAT_UNDEFINED;
    VkExtent2D swapchainExtent_{};

    VkRenderPass renderPass_ = VK_NULL_HANDLE;
    VkPipelineLayout pipelineLayout_ = VK_NULL_HANDLE;
    VkPipeline graphicsPipeline_ = VK_NULL_HANDLE;

    VkPipelineLayout uiPipelineLayout_ = VK_NULL_HANDLE;
    VkPipeline uiPipeline_ = VK_NULL_HANDLE;

    VkCommandPool commandPool_ = VK_NULL_HANDLE;

    std::vector<VkImage> swapchainImages_;
    std::vector<VkImageView> imageViews_;

    std::vector<VkImage> depthImages_;
    std::vector<VkDeviceMemory> depthMemory_;
    std::vector<VkImageView> depthViews_;

    // Single bounded offscreen planar-reflection target. It is intentionally
    // shared/reused rather than allocating one texture per reflective surface.
    VkImage reflectionColorImage_ = VK_NULL_HANDLE;
    VkDeviceMemory reflectionColorMemory_ = VK_NULL_HANDLE;
    VkImageView reflectionColorView_ = VK_NULL_HANDLE;
    VkImage reflectionDepthImage_ = VK_NULL_HANDLE;
    VkDeviceMemory reflectionDepthMemory_ = VK_NULL_HANDLE;
    VkImageView reflectionDepthView_ = VK_NULL_HANDLE;
    VkExtent2D reflectionExtent_{};
    float reflectionTargetScale_ = 0.0f;
    VkRenderPass reflectionRenderPass_ = VK_NULL_HANDLE;
    VkFramebuffer reflectionFramebuffer_ = VK_NULL_HANDLE;
    VkPipeline reflectionPipeline_ = VK_NULL_HANDLE;

    std::vector<VkFramebuffer> framebuffers_;
    std::vector<VkCommandBuffer> commandBuffers_;
    std::vector<VkFence> imageFences_;

    static constexpr std::uint32_t kFramesInFlight = 2;
    FrameSync frames_[kFramesInFlight]{};
    std::uint32_t frameIndex_ = 0;

    ANativeWindow* window_ = nullptr;
    AAssetManager* assetManager_ = nullptr;
    JNIEnv* jniEnv_ = nullptr;
    jobject javaActivity_ = nullptr;

    std::uint64_t refreshDurationNs_ = 0;
    std::uint64_t requestedSwapIntervalNs_ = 0;

    float preferredFrameRate_ = 0.0f;

    bool swappyInitialized_ = false;
    bool initialized_ = false;
};

} // namespace xziel::android
