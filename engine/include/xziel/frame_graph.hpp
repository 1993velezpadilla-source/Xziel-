#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace xziel {

constexpr std::size_t kMaxFrameGraphResources = 64;
constexpr std::size_t kMaxFrameGraphPasses = 64;

struct FrameGraphResourceDesc {
    std::uint32_t id = 0;
    std::uint64_t bytes = 0;

    bool transient = true;
    bool external = false;
};

struct FrameGraphPassDesc {
    std::uint32_t id = 0;

    // Resource bit i corresponds to resource slot i in the graph.
    std::uint64_t reads = 0;
    std::uint64_t writes = 0;

    bool enabled = true;
};

struct FrameGraphResourcePlan {
    std::uint32_t id = 0;
    std::uint32_t firstPass = 0;
    std::uint32_t lastPass = 0;

    std::uint32_t aliasGroup = 0;
    std::uint64_t bytes = 0;

    bool used = false;
    bool transient = true;
};

struct FrameGraphCompileResult {
    bool valid = true;
    bool readBeforeWrite = false;
    bool duplicateResourceId = false;
    bool duplicatePassId = false;

    std::uint32_t enabledPassCount = 0;
    std::uint32_t usedResourceCount = 0;
    std::uint32_t aliasGroupCount = 0;

    std::uint64_t unaliasedTransientBytes = 0;
    std::uint64_t aliasedTransientBytes = 0;

    std::array<FrameGraphResourcePlan, kMaxFrameGraphResources> resources{};
};

class FrameGraph final {
public:
    void reset() noexcept;

    [[nodiscard]] bool addResource(
        const FrameGraphResourceDesc& resource) noexcept;

    [[nodiscard]] bool addPass(
        const FrameGraphPassDesc& pass) noexcept;

    [[nodiscard]] FrameGraphCompileResult compile() const noexcept;

    [[nodiscard]] std::size_t resourceCount() const noexcept;
    [[nodiscard]] std::size_t passCount() const noexcept;

private:
    std::array<FrameGraphResourceDesc, kMaxFrameGraphResources> resources_{};
    std::array<FrameGraphPassDesc, kMaxFrameGraphPasses> passes_{};

    std::size_t resourceCount_ = 0;
    std::size_t passCount_ = 0;
};

} // namespace xziel
