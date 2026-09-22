#include "xziel/gameplay_events.hpp"

namespace xziel {

void GameplayEventQueue::clear() noexcept {
    read_ = 0;
    write_ = 0;
    size_ = 0;
    dropped_ = 0;
}

bool GameplayEventQueue::push(
    const GameplayEvent& event) noexcept {
    if (event.type == GameplayEventType::None) {
        return false;
    }

    if (size_ >= events_.size()) {
        ++dropped_;
        return false;
    }

    events_[write_] = event;
    write_ = (write_ + 1U) % events_.size();
    ++size_;
    return true;
}

bool GameplayEventQueue::pop(
    GameplayEvent& destination) noexcept {
    if (size_ == 0) {
        return false;
    }

    destination = events_[read_];
    read_ = (read_ + 1U) % events_.size();
    --size_;
    return true;
}

std::size_t GameplayEventQueue::size() const noexcept {
    return size_;
}

bool GameplayEventQueue::empty() const noexcept {
    return size_ == 0;
}

std::uint64_t GameplayEventQueue::droppedCount() const noexcept {
    return dropped_;
}

} // namespace xziel
