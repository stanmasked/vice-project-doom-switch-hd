#pragma once
#include "driving_road_private_bundle.hpp"
#include <cstdint>
#include <cstdio>
// Native result for *optional* source-free numeric reference SD intake.
// No source edge coordinates or original graphics are recorded.
namespace vpd {
struct RoadSdStartup {
  bool mounted=false;
  bool loaded=false;
  unsigned count=0;
  unsigned first_frame=0;
  unsigned last_frame=0;
};
inline RoadSdStartup roadSdStartup(
    bool has_sd,const private_road::PrivateRoadBundle& b) noexcept {
  RoadSdStartup out{};
  out.mounted=has_sd;
  out.loaded=has_sd && b.loaded();
  if(!out.loaded)return out;
  out.count=static_cast<unsigned>(b.count());
  if(const auto* first=b.byIndex(0))out.first_frame=first->frame;
  if(const auto* last=b.byIndex(b.count()-1))out.last_frame=last->frame;
  return out;
}
inline bool writeRoadSdStartup(
    bool has_sd,const private_road::PrivateRoadBundle& b) {
  if(!has_sd)return false;
  const auto state=roadSdStartup(has_sd,b);
  auto* f=std::fopen(
    "sdmc:/switch/vice_project_doom/private_road_sd_guest.txt","w");
  if(!f)return false;
  const int n=std::fprintf(f,
    "VPD_PRIVATE_ROAD_SD_V1 mounted=%u loaded=%u samples=%u "
    "first_frame=%u last_frame=%u source=nro_startup "
    "original_art=no camera_collision_proven=no\n",
    static_cast<unsigned>(state.mounted),
    static_cast<unsigned>(state.loaded),state.count,state.first_frame,
    state.last_frame);
  const bool closed=std::fclose(f)==0;
  return n>0 && closed;
}
} // namespace vpd
