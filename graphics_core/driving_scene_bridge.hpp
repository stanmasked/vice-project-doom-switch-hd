#pragma once
#include "driving_preview.hpp"
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
    return view;
}
} // namespace vpd
