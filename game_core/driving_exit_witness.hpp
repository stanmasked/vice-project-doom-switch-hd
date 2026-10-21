#pragma once
#include <cstdint>
#include <cstdio>
// Source-owned ROM-free evidence of the native driving blackout. The state
// machine cannot produce an event from host keystrokes or simulated records.
namespace vpd {
struct DrivingExitRecord {
  bool valid=false;
  unsigned seq=0;
  const char* scene="";
  unsigned last_road_frame=0,black_frames=0;
  std::uint64_t baseline=0,platform=0;
  bool sampled_black=false;
};
class DrivingExitProof {
public:
  DrivingExitRecord begin(bool actual_pad_minus,unsigned road_frame,
                          std::uint64_t fp) {
    if(active_ || done_ || !actual_pad_minus)return {};
    active_=true;baseline_=fp;road_frame_=road_frame;
    return {true,0,"last_road",road_frame_,0,baseline_,fp,false};
  }
  DrivingExitRecord black(unsigned count,std::uint64_t fp,bool black_pixel) {
    if(!active_ || done_ || !black_pixel ||
       count!=black_frames_+1 || count>41 || baseline_!=fp)return {};
    black_frames_=count;
    return {true,count,"black",road_frame_,black_frames_,
            baseline_,fp,true};
  }
  DrivingExitRecord platform(std::uint64_t fp) {
    if(!active_ || done_ || black_frames_!=41 || baseline_!=fp)return {};
    done_=true;active_=false;
    return {true,42,"platform",road_frame_,41,baseline_,fp,false};
  }
private:
  bool active_=false,done_=false;
  unsigned road_frame_=0,black_frames_=0;
  std::uint64_t baseline_=0;
};
inline void resetDrivingExitWitness(bool sd) {
  if(!sd)return;
  if(auto* f=std::fopen("sdmc:/switch/vice_project_doom/driving_exit_guest.txt","w"))
    std::fclose(f);
}
inline bool appendDrivingExitWitness(bool sd,const DrivingExitRecord& r) {
  if(!sd || !r.valid)return false;
  auto* f=std::fopen("sdmc:/switch/vice_project_doom/driving_exit_guest.txt","a");
  if(!f)return false;
  const int n=std::fprintf(f,
    "VPD_DRIVING_EXIT_V1 seq=%u scene=%s road_frame=%u "
    "black_frames=%u black_pixel=%u "
    "platform_before=%016llx platform_after=%016llx "
    "source=libnx_frame original_stage_clear_proven=0\n",
    r.seq,r.scene,r.last_road_frame,r.black_frames,
    static_cast<unsigned>(r.sampled_black),
    static_cast<unsigned long long>(r.baseline),
    static_cast<unsigned long long>(r.platform));
  const bool closed=std::fclose(f)==0;return n>0 && closed;
}
} // namespace vpd
