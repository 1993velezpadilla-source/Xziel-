#include "xziel/frame_graph.hpp"

#include <algorithm>
#include <array>
#include <limits>

namespace xziel {

namespace {

bool lifetimesOverlap(
    const FrameGraphResourcePlan& a,
    const FrameGraphResourcePlan& b) noexcept {
    if (!a.used || !b.used) {
        return false;
    }
    return !(a.lastPass < b.firstPass || b.lastPass < a.firstPass);
}

} // namespace

void FrameGraph::reset() noexcept {
    resourceCount_ = 0;
    passCount_ = 0;
    resources_ = {};
    passes_ = {};
}

bool FrameGraph::addResource(
    const FrameGraphResourceDesc& resource) noexcept {
    if (resourceCount_ >= resources_.size() ||
        resource.id == 0 ||
        resource.bytes == 0) {
        return false;
    }

    for (std::size_t i = 0; i < resourceCount_; ++i) {
        if (resources_[i].id == resource.id) {
            return false;
        }
    }

    resources_[resourceCount_++] = resource;
    return true;
}

bool FrameGraph::addPass(
    const FrameGraphPassDesc& pass) noexcept {
    if (passCount_ >= passes_.size() ||
        pass.id == 0) {
        return false;
    }

    for (std::size_t i = 0; i < passCount_; ++i) {
        if (passes_[i].id == pass.id) {
            return false;
        }
    }

    passes_[passCount_++] = pass;
    return true;
}

FrameGraphCompileResult FrameGraph::compile() const noexcept {
    FrameGraphCompileResult out{};

    std::array<bool, kMaxFrameGraphResources> everWritten{};
    std::array<std::uint32_t, kMaxFrameGraphResources> firstUse{};
    std::array<std::uint32_t, kMaxFrameGraphResources> lastUse{};

    firstUse.fill(std::numeric_limits<std::uint32_t>::max());

    std::uint32_t enabledPassIndex = 0;

    for (std::size_t p = 0; p < passCount_; ++p) {
        const auto& pass = passes_[p];
        if (!pass.enabled) {
            continue;
        }

        ++out.enabledPassCount;

        for (std::size_t r = 0; r < resourceCount_; ++r) {
            const std::uint64_t bit = 1ULL << r;
            const bool reads = (pass.reads & bit) != 0;
            const bool writes = (pass.writes & bit) != 0;
            if (!reads && !writes) {
                continue;
            }

            firstUse[r] = std::min(firstUse[r], enabledPassIndex);
            lastUse[r] = enabledPassIndex;

            if (reads &&
                !everWritten[r] &&
                !resources_[r].external) {
                out.readBeforeWrite = true;
                out.valid = false;
            }

            if (writes) {
                everWritten[r] = true;
            }
        }

        ++enabledPassIndex;
    }

    for (std::size_t r = 0; r < resourceCount_; ++r) {
        auto& plan = out.resources[r];
        plan.id = resources_[r].id;
        plan.bytes = resources_[r].bytes;
        plan.transient = resources_[r].transient;

        if (firstUse[r] ==
            std::numeric_limits<std::uint32_t>::max()) {
            continue;
        }

        plan.used = true;
        plan.firstPass = firstUse[r];
        plan.lastPass = lastUse[r];
        ++out.usedResourceCount;

        if (resources_[r].transient) {
            out.unaliasedTransientBytes += resources_[r].bytes;
        }
    }

    // Greedy alias groups. Resources can share the same transient block only
    // when their lifetimes do not overlap. Group size is the largest resource
    // placed in that group.
    std::array<std::uint64_t, kMaxFrameGraphResources> groupBytes{};
    std::array<std::uint64_t, kMaxFrameGraphResources> groupMembers{};
    std::uint32_t groupCount = 0;

    for (std::size_t r = 0; r < resourceCount_; ++r) {
        auto& plan = out.resources[r];
        if (!plan.used || !plan.transient) {
            continue;
        }

        bool placed = false;

        for (std::uint32_t g = 0; g < groupCount; ++g) {
            bool overlaps = false;
            const std::uint64_t members = groupMembers[g];

            for (std::size_t other = 0;
                 other < resourceCount_;
                 ++other) {
                const std::uint64_t bit = 1ULL << other;
                if ((members & bit) == 0) {
                    continue;
                }

                if (lifetimesOverlap(
                        plan,
                        out.resources[other])) {
                    overlaps = true;
                    break;
                }
            }

            if (!overlaps) {
                plan.aliasGroup = g + 1U;
                groupMembers[g] |= 1ULL << r;
                groupBytes[g] =
                    std::max(groupBytes[g], plan.bytes);
                placed = true;
                break;
            }
        }

        if (!placed) {
            if (groupCount >= kMaxFrameGraphResources) {
                out.valid = false;
                continue;
            }

            plan.aliasGroup = groupCount + 1U;
            groupMembers[groupCount] = 1ULL << r;
            groupBytes[groupCount] = plan.bytes;
            ++groupCount;
        }
    }

    out.aliasGroupCount = groupCount;
    for (std::uint32_t g = 0; g < groupCount; ++g) {
        out.aliasedTransientBytes += groupBytes[g];
    }

    return out;
}

std::size_t FrameGraph::resourceCount() const noexcept {
    return resourceCount_;
}

std::size_t FrameGraph::passCount() const noexcept {
    return passCount_;
}

} // namespace xziel
