#include "android_asset_streamer.hpp"

#include <algorithm>
#include <cstdio>
#include <limits>
#include <utility>

namespace xziel::android {

AndroidAssetStreamer::~AndroidAssetStreamer() {
    stop();
}

bool AndroidAssetStreamer::start(
    AAssetManager* assetManager,
    std::uint32_t workerCount,
    std::uint64_t maxBufferedBytes) noexcept {
    stop();

    if (assetManager == nullptr ||
        workerCount == 0U ||
        maxBufferedBytes == 0U) {
        return false;
    }

    workerCount =
        std::clamp<std::uint32_t>(
            workerCount,
            1U,
            4U);

    {
        std::lock_guard lock(mutex_);
        assetManager_ = assetManager;
        maxBufferedBytes_ =
            std::max<std::uint64_t>(
                maxBufferedBytes,
                1024ULL * 1024ULL);
        bufferedBytes_ = 0U;
        stats_ = {};
        running_ = true;
    }

    try {
        workers_.reserve(workerCount);

        for (std::uint32_t i = 0U;
             i < workerCount;
             ++i) {
            workers_.emplace_back(
                &AndroidAssetStreamer::workerMain,
                this);
        }
    } catch (...) {
        stop();
        return false;
    }

    return true;
}

void AndroidAssetStreamer::stop() noexcept {
    {
        std::lock_guard lock(mutex_);
        running_ = false;
    }

    workCv_.notify_all();
    resultCv_.notify_all();

    for (auto& worker : workers_) {
        if (worker.joinable()) {
            worker.join();
        }
    }

    workers_.clear();

    {
        std::lock_guard lock(mutex_);
        requests_.clear();
        results_.clear();
        scheduled_.clear();
        bufferedBytes_ = 0U;
        assetManager_ = nullptr;
        stats_.bufferedBytes = 0U;
        stats_.pending = 0U;
    }
}

bool AndroidAssetStreamer::enqueue(
    const std::string& assetPath,
    std::uint64_t maxBytes) noexcept {
    if (assetPath.empty() ||
        maxBytes == 0U) {
        return false;
    }

    try {
        std::lock_guard lock(mutex_);

        if (!running_ ||
            assetManager_ == nullptr ||
            scheduled_.contains(assetPath)) {
            return false;
        }

        scheduled_.insert(assetPath);
        requests_.push_back(
            Request{
                .key = assetPath,
                .path = assetPath,
                .offset = 0U,
                .size = 0U,
                .maxBytes = maxBytes,
                .range = false,
            });

        ++stats_.queued;
        stats_.pending =
            static_cast<std::uint32_t>(
                std::min<std::size_t>(
                    requests_.size(),
                    std::numeric_limits<std::uint32_t>::max()));
    } catch (...) {
        return false;
    }

    workCv_.notify_one();
    return true;
}

bool AndroidAssetStreamer::enqueueRange(
    const std::string& assetPath,
    std::uint64_t offset,
    std::uint64_t size,
    const std::string& requestKey) noexcept {
    if (assetPath.empty() ||
        requestKey.empty() ||
        size == 0U ||
        size >
            256ULL * 1024ULL * 1024ULL ||
        offset >
            std::numeric_limits<std::uint64_t>::max() -
                size) {
        return false;
    }

    try {
        std::lock_guard lock(mutex_);

        if (!running_ ||
            assetManager_ == nullptr ||
            scheduled_.contains(requestKey)) {
            return false;
        }

        scheduled_.insert(requestKey);
        requests_.push_back(
            Request{
                .key = requestKey,
                .path = assetPath,
                .offset = offset,
                .size = size,
                .maxBytes = size,
                .range = true,
            });

        ++stats_.queued;
        stats_.pending =
            static_cast<std::uint32_t>(
                std::min<std::size_t>(
                    requests_.size(),
                    std::numeric_limits<std::uint32_t>::max()));
    } catch (...) {
        return false;
    }

    workCv_.notify_one();
    return true;
}

bool AndroidAssetStreamer::take(
    const std::string& assetPath,
    std::vector<std::byte>& destination) noexcept {
    destination.clear();

    std::unique_lock lock(mutex_);

    if (!scheduled_.contains(assetPath)) {
        return false;
    }

    resultCv_.wait(
        lock,
        [&]() noexcept {
            return
                !running_ ||
                !scheduled_.contains(assetPath) ||
                results_.contains(assetPath);
        });

    const auto found =
        results_.find(assetPath);

    if (found == results_.end()) {
        scheduled_.erase(assetPath);
        return false;
    }

    const bool success =
        found->second.success;

    if (success) {
        const std::uint64_t resultBytes =
            static_cast<std::uint64_t>(
                found->second.bytes.size());

        destination =
            std::move(found->second.bytes);

        bufferedBytes_ =
            resultBytes <= bufferedBytes_
            ? bufferedBytes_ - resultBytes
            : 0U;

        ++stats_.consumed;
    }

    results_.erase(found);
    scheduled_.erase(assetPath);

    stats_.bufferedBytes =
        bufferedBytes_;
    stats_.pending =
        static_cast<std::uint32_t>(
            std::min<std::size_t>(
                requests_.size(),
                std::numeric_limits<std::uint32_t>::max()));

    lock.unlock();
    resultCv_.notify_all();

    return success;
}

bool AndroidAssetStreamer::tryTake(
    const std::string& assetPath,
    std::vector<std::byte>& destination,
    bool& finished) noexcept {
    destination.clear();
    finished = false;

    std::unique_lock lock(mutex_);

    const auto found =
        results_.find(assetPath);

    if (found == results_.end()) {
        if (!scheduled_.contains(assetPath) ||
            !running_) {
            finished = true;
        }
        return false;
    }

    finished = true;
    const bool success =
        found->second.success;

    if (success) {
        const std::uint64_t resultBytes =
            static_cast<std::uint64_t>(
                found->second.bytes.size());

        destination =
            std::move(found->second.bytes);

        bufferedBytes_ =
            resultBytes <= bufferedBytes_
            ? bufferedBytes_ - resultBytes
            : 0U;

        ++stats_.consumed;
    }

    results_.erase(found);
    scheduled_.erase(assetPath);

    stats_.bufferedBytes =
        bufferedBytes_;
    stats_.pending =
        static_cast<std::uint32_t>(
            std::min<std::size_t>(
                requests_.size(),
                std::numeric_limits<std::uint32_t>::max()));

    lock.unlock();
    resultCv_.notify_all();

    return success;
}

bool AndroidAssetStreamer::running() const noexcept {
    std::lock_guard lock(mutex_);
    return running_;
}

AndroidAssetStreamStats
AndroidAssetStreamer::stats() const noexcept {
    std::lock_guard lock(mutex_);

    AndroidAssetStreamStats out =
        stats_;

    out.bufferedBytes =
        bufferedBytes_;
    out.pending =
        static_cast<std::uint32_t>(
            std::min<std::size_t>(
                requests_.size(),
                std::numeric_limits<std::uint32_t>::max()));

    return out;
}

void AndroidAssetStreamer::workerMain() noexcept {
    for (;;) {
        Request request{};

        {
            std::unique_lock lock(mutex_);

            workCv_.wait(
                lock,
                [&]() noexcept {
                    return
                        !running_ ||
                        !requests_.empty();
                });

            if (!running_ &&
                requests_.empty()) {
                return;
            }

            request =
                std::move(requests_.front());
            requests_.pop_front();

            stats_.pending =
                static_cast<std::uint32_t>(
                    std::min<std::size_t>(
                        requests_.size(),
                        std::numeric_limits<std::uint32_t>::max()));
        }

        Result result{};

        AAsset* asset =
            AAssetManager_open(
                assetManager_,
                request.path.c_str(),
                AASSET_MODE_RANDOM);

        if (asset != nullptr) {
            const off64_t length =
                AAsset_getLength64(asset);

            std::uint64_t readOffset = 0U;
            std::uint64_t readBytes = 0U;

            if (length > 0) {
                const std::uint64_t assetBytes =
                    static_cast<std::uint64_t>(
                        length);

                if (request.range) {
                    if (request.offset <= assetBytes &&
                        request.size <=
                            assetBytes - request.offset) {
                        readOffset =
                            request.offset;
                        readBytes =
                            request.size;
                    }
                } else if (
                    assetBytes <= request.maxBytes) {
                    readBytes =
                        assetBytes;
                }
            }

            if (readBytes > 0U &&
                readBytes <= request.maxBytes &&
                readBytes <=
                    static_cast<std::uint64_t>(
                        std::numeric_limits<std::size_t>::max())) {
                try {
                    if (request.range) {
                        const off64_t seekResult =
                            AAsset_seek64(
                                asset,
                                static_cast<off64_t>(
                                    readOffset),
                                SEEK_SET);

                        if (seekResult !=
                            static_cast<off64_t>(
                                readOffset)) {
                            readBytes = 0U;
                        }
                    }

                    if (readBytes > 0U) {
                        result.bytes.resize(
                            static_cast<std::size_t>(
                                readBytes));

                        std::size_t totalRead = 0U;

                        while (totalRead <
                               result.bytes.size()) {
                            const int read =
                                AAsset_read(
                                    asset,
                                    result.bytes.data() +
                                        totalRead,
                                    result.bytes.size() -
                                        totalRead);

                            if (read <= 0) {
                                break;
                            }

                            totalRead +=
                                static_cast<std::size_t>(
                                    read);
                        }

                        result.success =
                            totalRead ==
                            result.bytes.size();
                    }
                } catch (...) {
                    result.bytes.clear();
                    result.success = false;
                }
            }

            AAsset_close(asset);
        }

        if (!result.success) {
            result.bytes.clear();
        }

        const std::uint64_t resultBytes =
            static_cast<std::uint64_t>(
                result.bytes.size());

        std::unique_lock lock(mutex_);

        if (!running_) {
            return;
        }

        if (result.success) {
            resultCv_.wait(
                lock,
                [&]() noexcept {
                    return
                        !running_ ||
                        bufferedBytes_ == 0U ||
                        resultBytes <=
                            maxBufferedBytes_ -
                                std::min(
                                    bufferedBytes_,
                                    maxBufferedBytes_);
                });

            if (!running_) {
                return;
            }

            bufferedBytes_ +=
                resultBytes;
            stats_.bytesRead +=
                resultBytes;
            ++stats_.completed;
        } else {
            ++stats_.failed;
        }

        try {
            results_.insert_or_assign(
                request.key,
                std::move(result));
        } catch (...) {
            if (resultBytes <= bufferedBytes_) {
                bufferedBytes_ -= resultBytes;
            }
            ++stats_.failed;
            scheduled_.erase(request.key);
        }

        stats_.bufferedBytes =
            bufferedBytes_;

        lock.unlock();
        resultCv_.notify_all();
    }
}

} // namespace xziel::android
