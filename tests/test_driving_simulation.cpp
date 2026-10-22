#include "driving_simulation.hpp"
#include "simulation.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>

static void check(bool ok,const char* reason) {
    if(!ok)throw std::runtime_error(reason);
}
static bool equal(const vpd::DrivingState& a,const vpd::DrivingState& b) {
    return a.frame==b.frame && a.car_x==b.car_x &&
        a.lateral_velocity==b.lateral_velocity && a.speed==b.speed &&
        a.road_phase==b.road_phase && a.obstacle_x==b.obstacle_x &&
        a.obstacle_y==b.obstacle_y && a.health==b.health &&
        a.hit_cooldown==b.hit_cooldown && a.impacts==b.impacts &&
        a.last_impact==b.last_impact;
}
int main() {
    vpd::Simulation platform;
    const uint64_t platformFingerprintBefore=platform.fingerprint();
    vpd::DrivingState drive;
    check(drive.car_x==640 && drive.health==5 && drive.speed==3,
          "invented car initial state");
    drive.tick({false,false,true,false});
    check(drive.speed==4,"throttle not applied");
    drive.tick({false,false,true,true});
    check(drive.speed==2,"brake must override throttle");
    const int startX=drive.car_x;
    for(int i=0;i<10;++i)drive.tick({false,true,true,false});
    check(drive.car_x>startX,"right steering did not move");
    check(drive.lateral_velocity<=6,"right steering velocity limit");
    for(int i=0;i<100;++i)drive.tick({false,true,false,false});
    check(drive.car_x==918 && drive.lateral_velocity==0,
          "road-right boundary missing");
    for(int i=0;i<180;++i)drive.tick({true,false,false,true});
    check(drive.car_x==362 && drive.lateral_velocity==0,
          "road-left boundary missing");
    check(drive.speed==0,"brake failed to stop");

    vpd::DrivingState collision;
    bool hit=false;
    for(int i=0;i<120;++i) {
        collision.tick({});
        if(collision.last_impact) {
            check(!hit,"same obstacle applied repeated damage");
            hit=true;
            check(collision.health==4 && collision.impacts==1,
                  "first obstacle damage incorrect");
            check(collision.hit_cooldown==45,
                  "collision invulnerability not initialized");
        }
    }
    check(hit,"stationary car did not collide with centered fixture");
    check(collision.impacts==1,"fixture caused a second phantom hit");
    // After reset the entire event sequence must reproduce byte-for-byte.
    vpd::DrivingState seqA,seqB;
    for(int i=0;i<300;++i) {
        const vpd::DriveInput input{
            (i%33)<6,(i%33)>26,(i%20)<3,(i%40)==17};
        seqA.tick(input);
        seqB.tick(input);
        check(equal(seqA,seqB),"separate identical driving replays diverged");
        check(seqA.car_x>=362 && seqA.car_x<=918,
              "driving replay left roadway limits");
        check(seqA.speed>=0 && seqA.speed<=8,
              "driving speed saturation failed");
        check(seqA.road_phase>=0 && seqA.road_phase<72,
              "scroll phase out of bounds");
        check(seqA.health<=5,"health overflow");
    }
    seqA.reset();
    check(equal(seqA,vpd::DrivingState{}),"driving reset incomplete");
    // A stopped/dead driving run cannot mutate legacy platform state.
    vpd::DrivingState stopped;
    stopped.health=0;
    const auto car=stopped.car_x;
    for(int i=0;i<10;++i)stopped.tick({false,true,true,false});
    check(stopped.speed==0 && stopped.car_x==car,
          "vehicle still responding after health=0");
    // Saturating frame counter must never wrap and dead-state ticks stay inert.
    vpd::DrivingState saturated;
    saturated.frame=UINT32_MAX;
    const auto saturatedX=saturated.car_x;
    saturated.tick({false,true,true,false});
    check(saturated.frame==UINT32_MAX,
          "driving frame counter wrapped");
    check(saturated.car_x>saturatedX,
          "frame saturation incorrectly disabled active simulation");

    vpd::DrivingState dead;
    dead.health=1;
    dead.obstacle_x=640;
    dead.obstacle_y=433;
    dead.tick({});
    check(dead.health==0 && dead.last_impact,
          "final collision did not transition to dead state");
    const auto deadFrame=dead.frame;
    const auto deadX=dead.car_x;
    const auto deadRoad=dead.road_phase;
    for(int i=0;i<12;++i) dead.tick({false,true,true,false});
    check(dead.health==0 && dead.speed==0 && dead.car_x==deadX &&
          dead.road_phase==deadRoad && dead.frame==deadFrame+12 &&
          dead.impacts==1 && !dead.last_impact,
          "dead state changed gameplay motion or repeated fatal damage");

    vpd::DrivingState opposed;
    const auto opposedX=opposed.car_x;
    for(int i=0;i<5;++i) opposed.tick({true,true,false,false});
    check(opposed.car_x==opposedX && opposed.lateral_velocity==0,
          "simultaneous left and right should cancel steering");
    check(platform.fingerprint()==platformFingerprintBefore,
          "independent driving model changed legacy platform simulation");
    std::cout<<"VPD_ROMFREE_DRIVING_CONTROL_PASS"
             <<" deterministic=1 steering=1 speed=1"
             <<" road_bounds=1 obstacle_collision=1 reset=1"
             <<" original_driving_physics_proven=0\n";
}
