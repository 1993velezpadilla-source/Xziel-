#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <type_traits>

namespace xziel {

template <typename T, std::size_t Capacity>
class SpscQueue final {
    static_assert(Capacity >= 2, "SpscQueue requires Capacity >= 2");
    static_assert(
        std::is_trivially_copyable_v<T>,
        "SpscQueue command payloads must be trivially copyable");

public:
    [[nodiscard]] bool tryPush(const T& value) noexcept {
        const std::size_t head =
            head_.load(std::memory_order_relaxed);
        const std::size_t next =
            increment(head);

        if (next ==
            tail_.load(std::memory_order_acquire)) {
            return false;
        }

        buffer_[head] = value;
        head_.store(next, std::memory_order_release);
        return true;
    }

    [[nodiscard]] bool tryPop(T& value) noexcept {
        const std::size_t tail =
            tail_.load(std::memory_order_relaxed);

        if (tail ==
            head_.load(std::memory_order_acquire)) {
            return false;
        }

        value = buffer_[tail];
        tail_.store(
            increment(tail),
            std::memory_order_release);
        return true;
    }

    [[nodiscard]] bool empty() const noexcept {
        return head_.load(std::memory_order_acquire) ==
            tail_.load(std::memory_order_acquire);
    }

    [[nodiscard]] std::size_t usableCapacity() const noexcept {
        return Capacity - 1U;
    }

private:
    [[nodiscard]] static constexpr std::size_t increment(
        std::size_t value) noexcept {
        return (value + 1U) % Capacity;
    }

    std::array<T, Capacity> buffer_{};

    alignas(64) std::atomic<std::size_t> head_{0};
    alignas(64) std::atomic<std::size_t> tail_{0};
};

} // namespace xziel
