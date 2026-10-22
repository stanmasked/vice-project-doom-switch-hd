#pragma once
#include "driving_road_private_bundle.hpp"
#include <cstddef>
#include <cstdint>
// Extra opt-in manual-only SD reference channel. The old built-in
// seven-key Y reviewer remains independent and unchanged.
namespace vpd {
class PrivateRoadReviewMode {
public:
    bool cycle(bool manual,bool driving,bool new_chord,
               const private_road::PrivateRoadBundle& bundle) noexcept {
        if(!manual || !driving || !new_chord || !bundle.loaded())
            return false;
        slot_=static_cast<std::uint8_t>(
            (static_cast<std::size_t>(slot_)+1)%(
                bundle.count()+1u));
        return true;
    }
    void reset() noexcept {slot_=0;}
    bool active() const noexcept {return slot_!=0;}
    const road_reference::CrossSection* selected(
        const private_road::PrivateRoadBundle& bundle) const noexcept {
        return slot_ && bundle.loaded() ?
            bundle.byIndex(static_cast<std::size_t>(slot_-1)):nullptr;
    }
private:
    std::uint8_t slot_=0;
};
} // namespace vpd
