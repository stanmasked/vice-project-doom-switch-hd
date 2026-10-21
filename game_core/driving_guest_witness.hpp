#pragma once
#include "driving_simulation.hpp"
#include <cstdint>
#include <cstdio>
// ROM-free source-owned state machine: live libnx input is required; a
// host key event by itself cannot produce a valid guest witness.
namespace vpd {
struct DrivingGuestRecord {
 unsigned seq=0; const char* name="";
 DrivingState before{},after{};
 uint64_t baseline=0,current=0;
 DriveInput input{};
};
struct DrivingGuestProof {
 unsigned seq=0; bool active=false; uint64_t baseline=0;
 DrivingGuestRecord enter(bool manual,bool chord,const DrivingState& car,uint64_t fp) {
  if(seq || !manual || !chord || car.frame || car.health!=5 ||
     car.speed!=3 || car.car_x!=640)return {};
  active=true;baseline=fp;seq=1;
  return {seq,"enter",car,car,baseline,fp,{}};
 }
 DrivingGuestRecord tick(const DriveInput& in,const DrivingState& before,
                         const DrivingState& after,uint64_t fp) {
  if(!active || fp!=baseline || after.frame!=before.frame+1u || !after.frame)return {};
  if(seq==1 && in.right && in.throttle && !in.left && !in.brake &&
     after.car_x>before.car_x && after.speed>before.speed) {
   seq=2;return {seq,"right_throttle",before,after,baseline,fp,in};
  }
  if(seq==2 && in.left && in.brake && !in.right && !in.throttle &&
     after.car_x<before.car_x && after.speed<before.speed) {
   seq=3;return {seq,"left_brake",before,after,baseline,fp,in};
  }
  if(seq==3 && after.last_impact && !before.last_impact &&
     before.health==5 && after.health==4 && after.impacts==1 &&
     after.hit_cooldown==45) {
   seq=4;return {seq,"impact",before,after,baseline,fp,in};
  }
  return {};
 }
 DrivingGuestRecord leave(bool manual,bool chord,const DrivingState& car,uint64_t fp) {
  const bool ok=active && manual && chord && seq==4 && fp==baseline &&
                car.health==4 && car.impacts==1;
  active=false;
  if(!ok)return {};
  seq=5;return {seq,"exit",car,car,baseline,fp,{}};
 }
};
inline void resetDrivingGuestProof(bool has_sd) {
 if(!has_sd)return;
 if(auto* file=std::fopen("sdmc:/switch/vice_project_doom/driving_guest.txt","w"))
  std::fclose(file);
}
inline bool appendDrivingGuestProof(bool has_sd,const DrivingGuestRecord& r) {
 if(!has_sd || !r.seq)return false;
 auto* f=std::fopen("sdmc:/switch/vice_project_doom/driving_guest.txt","a");
 if(!f)return false;
 const int n=std::fprintf(f,
  "VPD_DRIVING_GUEST_V1 seq=%u event=%s before_frame=%u frame=%u "
  "before_x=%d car_x=%d before_speed=%d speed=%d "
  "before_health=%u health=%u impacts=%u cooldown=%u "
  "left=%u right=%u throttle=%u brake=%u "
  "platform_before=%016llx platform_after=%016llx "
  "source=libnx_pad original_nes_physics_proven=0\n",
  r.seq,r.name,r.before.frame,r.after.frame,r.before.car_x,r.after.car_x,
  r.before.speed,r.after.speed,static_cast<unsigned>(r.before.health),
  static_cast<unsigned>(r.after.health),r.after.impacts,
  static_cast<unsigned>(r.after.hit_cooldown),
  static_cast<unsigned>(r.input.left),static_cast<unsigned>(r.input.right),
  static_cast<unsigned>(r.input.throttle),static_cast<unsigned>(r.input.brake),
  static_cast<unsigned long long>(r.baseline),
  static_cast<unsigned long long>(r.current));
 const bool closed=std::fclose(f)==0;return n>0 && closed;
}
} // namespace vpd
