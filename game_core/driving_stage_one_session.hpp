#pragma once
#include "driving_simulation.hpp"
#include "driving_stage_exit.hpp"
#include "driving_stage_one_config.hpp"

namespace vpd {

// ROM-free lifecycle controller for the Stage 1-1 driving prototype.
// Completion is accepted only as an explicit host/gameplay event; this class
// does not pretend that the private reference frame number is a proven trigger.
class DrivingStageOneSession {
public:
    // Default route length is a tunable prototype value, not original-game data.
    static constexpr std::uint32_t kPrototypeRouteFrames=DrivingStageOneConfig::route_frames;
    static constexpr std::uint32_t kPrototypeRequiredObstacles=DrivingStageOneConfig::required_obstacles;
    DrivingStageOneSession() noexcept = default;
    explicit DrivingStageOneSession(std::uint32_t routeFrames,
                                    std::uint32_t requiredObstacles=kPrototypeRequiredObstacles) noexcept
        : route_frames_(routeFrames ? routeFrames : 1),
          required_obstacles_(requiredObstacles) {}
    explicit DrivingStageOneSession(const DrivingState& initial,
                                    std::uint32_t routeFrames=kPrototypeRouteFrames,
                                    std::uint32_t requiredObstacles=kPrototypeRequiredObstacles) noexcept
        : state_(initial), route_frames_(routeFrames ? routeFrames : 1),
          required_obstacles_(requiredObstacles) {}

    enum class Mode : unsigned char { Driving, Defeated, Transition, Platform };

    void tick(const DriveInput& input, bool finishConfirmed=false,
              bool restartPressed=false) noexcept {
        if (mode_==Mode::Defeated) {
            if (restartPressed) reset();
            return;
        }
        if (mode_!=Mode::Driving) return;
        state_.tick(input);
        if (state_.health==0) {
            mode_=Mode::Defeated;
            return;
        }
        if ((finishConfirmed || state_.frame>=route_frames_) &&
            exit_.requestAfterDrivingFrame(true,true)) {
            mode_=Mode::Transition;
        }
    }

    Mode presentFrame() noexcept {
        if (mode_!=Mode::Transition) return mode_;
        const auto scene=exit_.present();
        if (scene==DrivingStageExit::Scene::Black) return mode_;
        mode_=Mode::Platform;
        return mode_;
    }

    void reset() noexcept {
        state_.reset();
        exit_.reset();
        mode_=Mode::Driving;
    }

    const DrivingState& state() const noexcept { return state_; }
    Mode mode() const noexcept { return mode_; }
    std::uint32_t blackFramesPresented() const noexcept {
        return exit_.blackFramesPresented();
    }

private:
    DrivingState state_{};
    DrivingStageExit exit_{};
    std::uint32_t route_frames_=kPrototypeRouteFrames;
    Mode mode_=Mode::Driving;
};

} // namespace vpd
