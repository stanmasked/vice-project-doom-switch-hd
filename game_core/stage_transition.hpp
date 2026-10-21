#pragma once
#include <cstdint>

// ROM-free scene-transition timing contract. Stage labels and absolute reference
// frame numbers come from private original FCEUX frame observation; no game
// artwork, source ROM, original FM2, or reconstructed NES code is embedded.
// This stand-alone state machine is not wired into a Switch NRO yet.
namespace vpd {
namespace stage_transition {
constexpr std::uint32_t kOriginalLastDrivingFrame = 3606;
constexpr std::uint32_t kOriginalFirstBlackFrame = 3607;
constexpr std::uint32_t kOriginalLastBlackFrame = 3647;
constexpr std::uint32_t kOriginalFirstPlatformFrame = 3648;
constexpr std::uint32_t kBlackFrames = 41;
static_assert(kOriginalFirstBlackFrame == kOriginalLastDrivingFrame + 1,
              "driving-to-black reference frame gap");
static_assert(kOriginalLastBlackFrame - kOriginalFirstBlackFrame + 1 == kBlackFrames,
              "black interval reference length");
static_assert(kOriginalFirstPlatformFrame == kOriginalLastBlackFrame + 1,
              "black-to-platform reference frame gap");

enum class Scene : std::uint8_t { Driving, Black, Platform };

class Timeline {
public:
    // Call requestExit *after* presenting the last driving frame. The next
    // presentation is the first black frame. Duplicate requests are ignored.
    bool requestExit() noexcept {
        if (next_ != Scene::Driving || pending_) return false;
        pending_ = true;
        return true;
    }
    Scene present() noexcept {
        if (next_ == Scene::Driving && pending_) {
            next_ = Scene::Black;
            remaining_ = kBlackFrames;
            pending_ = false;
        }
        const Scene shown = next_;
        if (shown == Scene::Black) {
            ++black_presented_;
            --remaining_;
            if (remaining_ == 0) next_ = Scene::Platform;
        }
        return shown;
    }
    Scene nextScene() const noexcept { return next_; }
    std::uint32_t remainingBlackFrames() const noexcept { return remaining_; }
    std::uint32_t presentedBlackFrames() const noexcept { return black_presented_; }
    void reset() noexcept {
        next_ = Scene::Driving;
        remaining_ = 0;
        black_presented_ = 0;
        pending_ = false;
    }
private:
    Scene next_ = Scene::Driving;
    std::uint32_t remaining_ = 0;
    std::uint32_t black_presented_ = 0;
    bool pending_ = false;
};
} // namespace stage_transition
} // namespace vpd
