#include "driving_road_ppu_alignment.hpp"
#include <cstdint>
#include <initializer_list>
#include <iostream>
#include <stdexcept>
static void req(bool ok,const char* message) {
  if(!ok)throw std::runtime_error(message);
}
int main() {
  using namespace vpd::road_ppu_reference;
  constexpr int frames[]={600,744,800,920};
  constexpr int raw[]={79,136,144,24};
  constexpr int post[]={79,134,139,19};
  constexpr int widths[]={123,123,56,88};
  constexpr int centers[]={254,254,255,319};
  req(consistent(),"frame-aligned reference invalid");
  req(kObservedFrames==321 && kObservedTotalWrites==1284,
      "observed original event counts changed");
  req(kExecutedWriterPcs[0]==0xe8ec && kExecutedWriterPcs[1]==0xe8f1 &&
      kExecutedWriterPcs[2]==0xe369 && kExecutedWriterPcs[3]==0xe36c,
      "original CPU writer provenance changed");
  req(kFirstWriterCycleGap==7 && kLateWriterCycleGap==4,
      "source CPU cycle timing changed");
  for(std::size_t i=0;i<kAligned.size();++i) {
    auto joint=atExactFrame(frames[i]);
    req(static_cast<bool>(joint) && joint.ppu->frame==frames[i] &&
        joint.image->frame==frames[i],"unmatched source movie frame");
    req(joint.ppu->second_2005_written==raw[i] &&
        joint.ppu->ram_0d_postframe==post[i],"actual PPU/RAM sample altered");
    req(joint.image->width()==widths[i] &&
        joint.image->center_twice()==centers[i],
        "observed RGB cross-section changed");
    req(joint.ppu->differsFromPostframe()==(i!=0),
        "postframe RAM improperly substituted for source writer");
  }
  req(atExactFrame(600).image->width()==atExactFrame(744).image->width() &&
      atExactFrame(600).ppu->second_2005_written!=
      atExactFrame(744).ppu->second_2005_written,
      "register changes need not imply visible width change");
  for(std::uint32_t frame:{0u,599u,601u,745u,760u,784u,799u,
                            801u,840u,921u,3606u})
    req(!static_cast<bool>(atExactFrame(frame)),
        "invented original register/image pair");
  std::cout<<"VPD_ROMFREE_ROAD_PPU_ALIGNMENT_PASS matched_frames=4"
           <<" writer_frames=321 writer_events=1284"
           <<" ppu_scanline_proven=no camera_speed_proven=no"
           <<" road_collision_proven=no original_media=none\n";
}
