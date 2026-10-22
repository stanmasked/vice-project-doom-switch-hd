#pragma once
#include "driving_private_review_mode.hpp"
#include "driving_raster_witness.hpp"
#include <cstdio>
#include <cstdint>
// Explicit source-owned negative evidence: an actual physical R3 input
// reaches a live guest with an invalid/missing private numeric SD file.
// The renderer/vehicle cannot fall through to 37-frame observations.
namespace vpd {
struct PrivateRoadRejectEvent {
  bool valid=false;
  unsigned frame=0,health=0;
  std::uint32_t neutral_road=0,neutral_shoulder=0,car=0,hud=0;
  std::uint64_t platform=0;
};
class PrivateRoadRejectProof {
public:
  PrivateRoadRejectEvent observe(
     bool manual,bool driving,bool actual_r3_edge,
     const private_road::PrivateRoadBundle& bundle,
     const PrivateRoadReviewMode& private_mode,
     const DrivingPreviewView& view,
     const std::uint32_t* image,int stride,std::uint64_t fingerprint) {
    if(seen_||!manual||!driving||!actual_r3_edge||
       bundle.loaded()||private_mode.active()||
       private_mode.selected(bundle)!=nullptr||
       view.private_road_enabled||view.observed_road_frame!=0||
       !image||stride<kDrivingPreviewWidth)return {};
    const auto sample=sampleDrivingRaster(image,stride,view);
    if(!sample.matched)return {};
    constexpr auto shoulder=driving_detail::rgba(61,80,76);
    constexpr auto road=driving_detail::rgba(42,50,66);
    const auto outside=image[171*stride+40];
    const auto inside=image[171*stride+500];
    if(outside!=shoulder || inside!=road)return {};
    seen_=true;
    PrivateRoadRejectEvent event{};
    event.valid=true;
    event.frame=view.frame;
    event.health=view.health;
    event.neutral_road=inside;
    event.neutral_shoulder=outside;
    event.car=sample.car;
    event.hud=sample.hud;
    event.platform=fingerprint;
    return event;
  }
private:
  bool seen_=false;
};
inline void resetPrivateRoadRejectGuest(bool has_sd) {
  if(!has_sd)return;
  if(auto* f=std::fopen(
     "sdmc:/switch/vice_project_doom/private_road_reject_guest.txt","w"))
     std::fclose(f);
}
inline bool appendPrivateRoadRejectGuest(
   bool has_sd,const PrivateRoadRejectEvent& e) {
  if(!has_sd || !e.valid)return false;
  auto* f=std::fopen(
      "sdmc:/switch/vice_project_doom/private_road_reject_guest.txt","a");
  if(!f)return false;
  const int n=std::fprintf(f,
      "VPD_PRIVATE_ROAD_REJECT_V1 loaded=0 native_r3=1 "
      "private_active=0 frame=%u health=%u "
      "road_pixel=%08x shoulder_pixel=%08x "
      "car_pixel=%08x hud_pixel=%08x platform_fp=%016llx "
      "source=libnx_live_raster original_art=no collision_proven=no\n",
      e.frame,e.health,static_cast<unsigned>(e.neutral_road),
      static_cast<unsigned>(e.neutral_shoulder),
      static_cast<unsigned>(e.car),static_cast<unsigned>(e.hud),
      static_cast<unsigned long long>(e.platform));
  const bool closed=std::fclose(f)==0;
  return n>0 && closed;
}
} // namespace vpd
