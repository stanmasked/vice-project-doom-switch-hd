#pragma once
#include "driving_road_reference.hpp"
#include <array>
#include <cstdint>
// Source-only paired original FCEUX observations, not camera speed, a
// collision polygon, inferred effective PPU scroll or scanline boundaries.
namespace vpd::road_ppu_reference {
struct AlignedFrame {
  std::uint16_t frame;
  std::uint8_t second_2005_written, ram_0d_postframe;
  constexpr bool differsFromPostframe() const noexcept {
    return second_2005_written!=ram_0d_postframe;
  }
};
constexpr std::array<AlignedFrame,4> kAligned = {{
  {600,79,79},{744,136,134},{800,144,139},{920,24,19}
}};
constexpr std::array<std::uint16_t,4> kExecutedWriterPcs = {{
  0xe8ec,0xe8f1,0xe369,0xe36c
}};
constexpr unsigned kObservedPerFrameWrites=4;
constexpr unsigned kObservedFrames=321;
constexpr unsigned kObservedTotalWrites=1284;
constexpr int kFirstWriterCycleGap=7;
constexpr int kLateWriterCycleGap=4;
struct MatchedObservation {
  const AlignedFrame* ppu=nullptr;
  const road_reference::CrossSection* image=nullptr;
  constexpr explicit operator bool() const noexcept {
    return ppu!=nullptr && image!=nullptr;
  }
};
constexpr MatchedObservation atExactFrame(std::uint32_t frame) noexcept {
  for(const auto& p:kAligned)
    if(p.frame==frame)return {&p,road_reference::atExactFrame(frame)};
  return {};
}
constexpr bool consistent() noexcept {
  if(kObservedTotalWrites!=kObservedPerFrameWrites*kObservedFrames ||
     !road_reference::valid())return false;
  std::uint16_t last=0;
  for(const auto& p:kAligned) {
    const auto aligned=atExactFrame(p.frame);
    if(p.frame<=last || !aligned || aligned.ppu!=&p ||
       !aligned.image || aligned.image->width()<1)return false;
    last=p.frame;
  }
  return true;
}
static_assert(consistent(),"source-only original alignment changed");
} // namespace vpd::road_ppu_reference
