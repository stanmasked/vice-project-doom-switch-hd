#pragma once
#include "driving_preview.hpp"
#include "driving_source_scroll_review.hpp"
#include "driving_simulation.hpp"

// Single ROM-free adapter shared by the libnx NRO and host raster tests.
// Owns no state: each visual field comes from the SAME vehicle tick.
// It is not a recreation of the original NES driving renderer or physics.
namespace vpd {
inline DrivingPreviewView makeDrivingSceneView(const DrivingState& drive) {
    DrivingPreviewView view{};
    view.frame=drive.frame;
    view.road_phase=drive.road_phase;
    view.ticks=drive.frame;
    view.health=drive.health;
    view.car_x=drive.car_x;
    view.obstacle_x=drive.obstacle_x;
    view.obstacle_y=drive.obstacle_y;
    view.show_obstacle=true; // fixture only; not extracted NES traffic
    view.impact_flash=drive.hit_cooldown>0 &&
                      (drive.frame/4u)%2u==0u;
    view.speed=static_cast<uint8_t>(drive.speed);
    view.obstacles_passed=drive.obstacles_passed;
    return view;
}
// Stage362: explicit diagnostics-only wrapper for the real shared NRO/host
// presentation mapping. Even an ACCEPTED observational source pair leaves
// the synthetic vehicle simulation and invented road_phase exactly as-is.
inline SourceScrollReviewResult makeDrivingSceneSourceScrollReview(
    const DrivingState& drive, SourceScrollReviewGate& gate,
    bool manual_opt_in, const SourceScrollPairWitness& witness) noexcept {
    return gate.observe(manual_opt_in,makeDrivingSceneView(drive),witness);
}
} // namespace vpd
