#pragma once

#include <android/asset_manager.h>

#include <cstddef>
#include <cstdint>
#include <condition_variable>
#include <deque>
#include <mutex>
#include <string>
#include <thread>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace xziel::android {

struct AndroidAssetStreamStats {
    std::uint64_t queued = 0U;
    std::uint64_t completed = 0U;
    std::uint64_t failed = 0U;
    std::uint64_t consumed = 0U;
    std::uint64_t bytesRead = 0U;
    std::uint64_t bufferedBytes = 0U;
    std::uint32_t pending = 0U;
};

class AndroidAssetStreamer final {
public:
    AndroidAssetStreamer() = default;
    ~AndroidAssetStreamer();

    AndroidAssetStreamer(
        const AndroidAssetStreamer&) = delete;
    AndroidAssetStreamer& operator=(
        const AndroidAssetStreamer&) = delete;

    [[nodiscard]] bool start(
        AAssetManager* assetManager,
        std::uint32_t workerCount,
        std::uint64_t maxBufferedBytes) noexcept;

    void stop() noexcept;

    [[nodiscard]] bool enqueue(
        const std::string& assetPath,
        std::uint64_t maxBytes =
            256ULL * 1024ULL * 1024ULL) noexcept;

    // Blocks only for a path that was already scheduled. Vulkan object
    // creation remains on the render thread; workers perform APK asset I/O.
    [[nodiscard]] bool take(
        const std::string& assetPath,
        std::vector<std::byte>& destination) noexcept;

    // Non-blocking runtime poll. "finished" distinguishes a pending request
    // from a completed failure. Returns true only when bytes were consumed.
    [[nodiscard]] bool tryTake(
        const std::string& assetPath,
        std::vector<std::byte>& destination,
        bool& finished) noexcept;

    [[nodiscard]] bool running() const noexcept;

    [[nodiscard]] AndroidAssetStreamStats
    stats() const noexcept;

private:
    struct Request {
        std::string path{};
        std::uint64_t maxBytes = 0U;
    };

    struct Result {
        std::vector<std::byte> bytes{};
        bool success = false;
    };

    void workerMain() noexcept;

    AAssetManager* assetManager_ = nullptr;
    std::uint64_t maxBufferedBytes_ =
        32ULL * 1024ULL * 1024ULL;
    std::uint64_t bufferedBytes_ = 0U;

    mutable std::mutex mutex_{};
    std::condition_variable workCv_{};
    std::condition_variable resultCv_{};

    std::deque<Request> requests_{};
    std::unordered_map<std::string, Result> results_{};
    std::unordered_set<std::string> scheduled_{};
    std::vector<std::thread> workers_{};

    AndroidAssetStreamStats stats_{};
    bool running_ = false;
};

} // namespace xziel::android
