#pragma once
#include <algorithm>
#include <cstdint>

// Standalone ROM-free *prototype* car controls. All constants and obstacle
// placement are invented test fixtures, NOT recovered NES gameplay data.
// No renderer access, heap allocations, RNG, ROM, FM2 or platform APIs.
namespace vpd {
struct DriveInput {
    bool left=false;
    bool right=false;
    bool throttle=false;
    bool brake=false;
};
struct DrivingState {
    uint32_t frame=0;
    int car_x=640;
    int lateral_velocity=0;
    int speed=3; // prototype units per frame [0,8]
    int road_phase=0;
    int obstacle_x=640;
    int obstacle_y=20;
    uint8_t health=5;
    uint8_t hit_cooldown=0;
    uint32_t impacts=0;
    bool last_impact=false;

    void reset() { *this=DrivingState{}; }

    void tick(const DriveInput& input) {
        last_impact=false;
        if(frame != UINT32_MAX) ++frame;
        if(health==0) {
            speed=0;
            lateral_velocity=0;
            return;
        }
        if(input.brake)speed=std::max(0,speed-2);
        else if(input.throttle) speed=std::min(8,speed+1);
        // In absence of steering, decay the lateral motion deterministically.
        if(input.left != input.right) {
            lateral_velocity=std::max(-6,std::min(6,lateral_velocity+
                                       (input.left?-2:2)));
        } else if(lateral_velocity>0) {
            --lateral_velocity;
        } else if(lateral_velocity<0) {
            ++lateral_velocity;
        }
        car_x=std::max(362,std::min(918,car_x+lateral_velocity));
        if(car_x==362 || car_x==918)lateral_velocity=0;
        road_phase=(road_phase+speed*2)%72;
        obstacle_y+=speed*2+1;
        if(hit_cooldown>0)--hit_cooldown;
        // Simple invented AABB, independent from the original platformer.
        // Obstacle is 70x80; placeholder car 88x105 at fixed road y=433.
        const bool x_hit=(car_x-44<obstacle_x+35 &&
                          car_x+44>obstacle_x-35);
        const bool y_hit=(433<obstacle_y+40 && 538>obstacle_y-40);
        if(x_hit && y_hit && hit_cooldown==0) {
            --health;
            if(impacts!=UINT32_MAX)++impacts;
            hit_cooldown=45;
            last_impact=true;
            speed=std::max(0,speed-2);
            // Remove the hit obstacle to make damage one-shot.
            obstacle_y=-110;
            obstacle_x=(frame%2u==0u)?520:760;
        }
        if(obstacle_y>650) {
            obstacle_y=-110;
            obstacle_x=(frame%2u==0u)?520:760;
        }
    }
};
} // namespace vpd
