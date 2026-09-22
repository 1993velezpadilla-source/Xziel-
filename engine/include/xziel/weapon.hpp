#pragma once

#include <cstdint>

namespace xziel {

enum class WeaponPhase : std::uint8_t {
    Ready,
    Reloading,
};

struct WeaponConfig {
    std::uint32_t magazineSize = 30;
    std::uint32_t startingReserve = 120;

    float fireIntervalSeconds = 0.095f;
    float reloadSeconds = 1.85f;

    float adsInSeconds = 0.15f;
    float adsOutSeconds = 0.11f;

    // Per-weapon option for marksman/sniper behavior: a tap can be buffered
    // while the weapon finishes ADS instead of firing from the hip first.
    bool fireRequiresAds = false;
    float minimumAdsAlphaToFire = 0.92f;
    float triggerBufferSeconds = 0.18f;

    float recoilPitchDegrees = 0.78f;
    float recoilYawDegrees = 0.26f;

    bool automatic = true;
};

struct WeaponInput {
    bool fireHeld = false;
    bool firePressed = false;
    bool reloadPressed = false;
    bool aimHeld = false;
};

struct WeaponFrame {
    WeaponPhase phase = WeaponPhase::Ready;

    std::uint32_t magazine = 0;
    std::uint32_t reserve = 0;
    std::uint64_t shotCounter = 0;

    float adsAlpha = 0.0f;
    float reloadAlpha = 0.0f;

    bool firedThisTick = false;
    bool dryFireThisTick = false;
    bool reloadStartedThisTick = false;
    bool reloadCompletedThisTick = false;
    bool triggerBuffered = false;

    float recoilPitchImpulse = 0.0f;
    float recoilYawImpulse = 0.0f;
};

class WeaponController final {
public:
    explicit WeaponController(
        WeaponConfig config = {});

    void reset() noexcept;

    void equip(
        WeaponConfig config) noexcept;

    void refillAmmo(
        bool includeMagazine = false) noexcept;

    [[nodiscard]] WeaponFrame step(
        const WeaponInput& input,
        float deltaSeconds) noexcept;

    [[nodiscard]] const WeaponFrame&
    frame() const noexcept;

    [[nodiscard]] const WeaponConfig&
    config() const noexcept;

private:
    void startReload() noexcept;
    void completeReload() noexcept;

    [[nodiscard]] bool wantsShot(
        const WeaponInput& input) const noexcept;

    WeaponConfig config_{};
    WeaponFrame frame_{};

    float fireCooldownSeconds_ = 0.0f;
    float reloadElapsedSeconds_ = 0.0f;
    float triggerBufferRemaining_ = 0.0f;
};

} // namespace xziel
