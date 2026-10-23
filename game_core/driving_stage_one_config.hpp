#pragma once
#include <cstdint>

namespace vpd {
// Reference-playback duration measured in a private, read-only FCEUX run:
// Stage 1-1 is visible at after-frame 410 through 3606 (inclusive), followed
// by 41 black frames and Stage 2-1 at 3648. This anchors the ROM-free preview
// to that route duration; it does NOT establish a universal clear predicate.
// The obstacle threshold remains a prototype gate pending original logic work.
struct DrivingStageOneConfig {
    static constexpr std::uint32_t reference_first_road_frame=410;
    static constexpr std::uint32_t reference_last_road_frame=3606;
    static constexpr std::uint32_t route_frames=
        reference_last_road_frame-reference_first_road_frame+1;
    static constexpr std::uint32_t required_obstacles=8;

    static constexpr bool routeProgressComplete(
        std::uint32_t frame, std::uint32_t passed,
        std::uint32_t frameThreshold=route_frames,
        std::uint32_t obstacleThreshold=required_obstacles) noexcept {
        return frame>=frameThreshold && passed>=obstacleThreshold;
    }

    static constexpr bool shouldRequestExit(
        bool previewActive, std::uint8_t health, bool exitActive,
        bool manualExitPressed, std::uint32_t frame,
        std::uint32_t passed,
        std::uint32_t frameThreshold=route_frames,
        std::uint32_t obstacleThreshold=required_obstacles) noexcept {
        return previewActive && health>0 && !exitActive &&
            (manualExitPressed || routeProgressComplete(
                frame,passed,frameThreshold,obstacleThreshold));
    }
};
} // namespace vpd
