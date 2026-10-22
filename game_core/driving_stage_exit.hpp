#pragma once
#include "stage_transition.hpp"

// ROM-free driving -> blackout -> platform presentation gate.
// The 41-frame interval is grounded in private FCEUX visual evidence. The
// caller supplies an already-validated completion request; route thresholds
// remain prototype-only and are not the original game's proven clear condition.
namespace vpd {
class DrivingStageExit {
public:
    using Scene=stage_transition::Scene;
    bool requestAfterDrivingFrame(bool driving_mode, bool completion_requested) noexcept {
        if (!driving_mode || !completion_requested || active_)return false;
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
