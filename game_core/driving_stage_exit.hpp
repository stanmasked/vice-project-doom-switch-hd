#pragma once
#include "stage_transition.hpp"

// Manual-only ROM-free driving -> blackout -> platform presentation gate.
// The 41-frame interval is grounded in owner-private FCEUX visual evidence,
// while the trigger is an invented test-only Minus gesture. It is NOT the
// original game's stage-clear condition or real frame-3606 alignment.
namespace vpd {
class DrivingStageExit {
public:
    using Scene=stage_transition::Scene;
    bool requestAfterDrivingFrame(bool driving_mode, bool pressed_minus) noexcept {
        if (!driving_mode || !pressed_minus || active_)return false;
        if (!timeline_.requestExit())return false;
        active_=true;
        return true;
    }
    Scene present() noexcept {
        return active_?timeline_.present():Scene::Driving;
    }
    bool active() const noexcept {return active_;}
    std::uint32_t blackFramesPresented() const noexcept {
        return timeline_.presentedBlackFrames();
    }
    void reset() noexcept {
        timeline_.reset();
        active_=false;
    }
private:
    stage_transition::Timeline timeline_{};
    bool active_=false;
};
} // namespace vpd
