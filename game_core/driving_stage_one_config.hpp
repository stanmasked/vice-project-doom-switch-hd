#pragma once
#include <cstdint>

namespace vpd {
// Explicitly prototype-only route parameters. Replace only after private
// original-game measurements establish the authentic route/clear condition.
struct DrivingStageOneConfig {
    static constexpr std::uint32_t route_frames=1800;
    static constexpr std::uint32_t required_obstacles=8;
};
} // namespace vpd
