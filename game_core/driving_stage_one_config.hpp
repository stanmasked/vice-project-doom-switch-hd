#pragma once
#include <cstdint>

namespace vpd {
// Explicitly prototype-only route parameters. Replace only after private
// original-game measurements establish the authentic route/clear condition.
struct DrivingStageOneConfig {
    static constexpr std::uint32_t route_frames=1800;
    static constexpr std::uint32_t required_obstacles=8;

    static constexpr bool routeProgressComplete(
        std::uint32_t frame, std::uint32_t passed,
        std::uint32_t frameThreshold=route_frames,
        std::uint32_t obstacleThreshold=required_obstacles) noexcept {
        return frame>=frameThreshold && passed>=obstacleThreshold;
    }
};
} // namespace vpd
