#pragma once
#include "driving_simulation.hpp"
#include <cstdint>
#include <cstdio>
#include <limits>

namespace vpd {

struct DrivingRouteRecord {
    bool valid=false;
    unsigned seq=0;
    const char* event="";
    std::uint32_t frame=0;
    int car_x=0;
    int lateral_velocity=0;
    int speed=0;
    std::uint32_t obstacles_passed=0;
    std::uint32_t obstacle_serial=0;
    int obstacle_x=0;
    int obstacle_y=0;
    std::uint8_t health=0;
    std::uint8_t hit_cooldown=0;
    std::uint32_t impacts=0;
    DriveInput input{};
    std::uint64_t platform_fingerprint=0;
    const char* source="";
    bool manual_exit=false;
    bool route_complete=false;
};

class DrivingRouteProof {
public:
    void reset() noexcept {
        seq_=0;
        last_frame_=kUnknown;
        last_serial_=kUnknown;
        exit_logged_=false;
    }

    DrivingRouteRecord sample(const DriveInput& input,
                              const DrivingState& state,
                              std::uint64_t platformFingerprint) noexcept {
        if(exit_logged_ || state.frame==last_frame_) return {};
        const bool interval=state.frame!=0 && state.frame%16u==0;
        const bool obstacleChanged=last_serial_!=kUnknown &&
                                   state.obstacle_serial!=last_serial_;
        if(!interval && !obstacleChanged) return {};
        last_frame_=state.frame;
        last_serial_=state.obstacle_serial;
        return make("sample",state,platformFingerprint,input,
                    "libnx_pad",false,false);
    }

    DrivingRouteRecord exitRequest(const DrivingState& state,
                                   std::uint64_t platformFingerprint,
                                   bool manualExit,
                                   bool routeComplete) noexcept {
        if(exit_logged_) return {};
        exit_logged_=true;
        last_frame_=state.frame;
        last_serial_=state.obstacle_serial;
        return make("exit_request",state,platformFingerprint,DriveInput{},
                    "libnx_frame",manualExit,routeComplete);
    }

private:
    static constexpr std::uint32_t kUnknown=
        std::numeric_limits<std::uint32_t>::max();

    DrivingRouteRecord make(const char* event,const DrivingState& state,
                            std::uint64_t platformFingerprint,
                            const DriveInput& input,const char* source,
                            bool manualExit,bool routeComplete) noexcept {
        if(seq_==std::numeric_limits<unsigned>::max()) return {};
        DrivingRouteRecord r{};
        r.valid=true;
        r.seq=++seq_;
        r.event=event;
        r.frame=state.frame;
        r.car_x=state.car_x;
        r.lateral_velocity=state.lateral_velocity;
        r.speed=state.speed;
        r.obstacles_passed=state.obstacles_passed;
        r.obstacle_serial=state.obstacle_serial;
        r.obstacle_x=state.obstacle_x;
        r.obstacle_y=state.obstacle_y;
        r.health=state.health;
        r.hit_cooldown=state.hit_cooldown;
        r.impacts=state.impacts;
        r.input=input;
        r.platform_fingerprint=platformFingerprint;
        r.source=source;
        r.manual_exit=manualExit;
        r.route_complete=routeComplete;
        return r;
    }

    unsigned seq_=0;
    std::uint32_t last_frame_=kUnknown;
    std::uint32_t last_serial_=kUnknown;
    bool exit_logged_=false;
};

inline void resetDrivingRouteWitness(bool hasSd) {
    if(!hasSd) return;
    if(auto* file=std::fopen(
        "sdmc:/switch/vice_project_doom/driving_route_guest.txt","w"))
        std::fclose(file);
}

inline bool appendDrivingRouteWitness(bool hasSd,
                                      const DrivingRouteRecord& r) {
    if(!hasSd || !r.valid) return false;
    auto* file=std::fopen(
        "sdmc:/switch/vice_project_doom/driving_route_guest.txt","a");
    if(!file) return false;
    const int n=std::fprintf(file,
        "VPD_DRIVING_ROUTE_V1 seq=%u event=%s frame=%u car_x=%d "
        "lateral_velocity=%d speed=%d health=%u cooldown=%u impacts=%u "
        "obstacles_passed=%u obstacle_serial=%u obstacle_x=%d obstacle_y=%d "
        "left=%u right=%u throttle=%u brake=%u platform_fp=%016llx "
        "source=%s manual_exit=%u route_complete=%u "
        "original_stage_clear_proven=0\n",
        r.seq,r.event,r.frame,r.car_x,r.lateral_velocity,r.speed,
        static_cast<unsigned>(r.health),
        static_cast<unsigned>(r.hit_cooldown),r.impacts,r.obstacles_passed,
        r.obstacle_serial,r.obstacle_x,r.obstacle_y,
        static_cast<unsigned>(r.input.left),static_cast<unsigned>(r.input.right),
        static_cast<unsigned>(r.input.throttle),static_cast<unsigned>(r.input.brake),
        static_cast<unsigned long long>(r.platform_fingerprint),r.source,
        static_cast<unsigned>(r.manual_exit),
        static_cast<unsigned>(r.route_complete));
    const bool closed=std::fclose(file)==0;
    return n>0 && closed;
}

} // namespace vpd
