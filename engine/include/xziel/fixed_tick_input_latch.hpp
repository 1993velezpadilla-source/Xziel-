#pragma once

namespace xziel {

struct FixedTickInputPulses {
    bool fire = false;
    bool reload = false;
    bool interact = false;
    bool jump = false;
    bool stance = false;
};

class FixedTickInputPulseLatch final {
public:
    void capture(
        FixedTickInputPulses pulses) noexcept {
        pending_.fire =
            pending_.fire ||
            pulses.fire;

        pending_.reload =
            pending_.reload ||
            pulses.reload;

        pending_.interact =
            pending_.interact ||
            pulses.interact;

        pending_.jump =
            pending_.jump ||
            pulses.jump;

        pending_.stance =
            pending_.stance ||
            pulses.stance;
    }

    [[nodiscard]] const FixedTickInputPulses&
    pending() const noexcept {
        return pending_;
    }

    [[nodiscard]] bool any() const noexcept {
        return pending_.fire ||
            pending_.reload ||
            pending_.interact ||
            pending_.jump ||
            pending_.stance;
    }

    void acknowledge() noexcept {
        pending_ = {};
    }

    void reset() noexcept {
        pending_ = {};
    }

private:
    FixedTickInputPulses pending_{};
};

} // namespace xziel
