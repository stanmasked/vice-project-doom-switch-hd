#pragma once
#include "driving_road_reference.hpp"
#include <cstdint>
// Manual-only observational review, not original gameplay input/physics.
// 0 = normal invented ROM-free preview; 1..7 = EXACT known FCEUX frames.
namespace vpd {
class RoadProfileReviewMode {
public:
    bool cycle(bool manual,bool driving,bool fresh_three_key_chord) noexcept {
        if(!manual || !driving || !fresh_three_key_chord)return false;
        slot_=static_cast<std::uint8_t>(
            (static_cast<unsigned>(slot_)+1u)%
            (road_reference::kObserved.size()+1u));
        return true;
    }
    void reset() noexcept {slot_=0;}
    bool active() const noexcept {return slot_!=0;}
    std::uint16_t originalFrame() const noexcept {
        return slot_ ? road_reference::kObserved[slot_-1].frame : 0;
    }
private:
    std::uint8_t slot_=0;
};
} // namespace vpd
