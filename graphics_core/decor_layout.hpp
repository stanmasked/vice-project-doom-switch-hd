#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace vpd {
// VLAY v1: 16-byte header plus at most 64 fixed 12-byte records.
// World x/y are logical pixels, not screen pixels or NES map offsets.
struct DecorPlacement {
    int16_t world_x=0, world_y=0;
    uint8_t kind=0;       // 0 beacon, 1 fan; information for content tooling
    uint8_t layer=0;      // 0 behind platforms, 1 in front of the hero
    uint8_t first_frame=0, frame_count=1;
    uint16_t period_ticks=1, phase_frames=0;
};
struct DecorLayout {
    const DecorPlacement* placements=nullptr;
    uint16_t count=0;
};
constexpr size_t kDecorMaxObjects=64;
constexpr size_t kDecorLayoutHeaderSize=16;
constexpr size_t kDecorLayoutMaxBytes=kDecorLayoutHeaderSize+12*kDecorMaxObjects;

bool validDecorPlacement(const DecorPlacement& p,uint16_t atlas_frames=4);
bool validDecorLayout(DecorLayout layout,uint16_t atlas_frames=4);
unsigned placedDecorFrame(const DecorPlacement& p,uint32_t tick);

enum class LayoutLoadResult:uint8_t {
    Loaded, Missing, IoError, Invalid, Uninitialized
};

// Fixed-storage, no heap allocation and no stale pointers when reloading.
// Class is noncopyable: layout().placements points inside this owner.
class DecorLayoutSource {
public:
    DecorLayoutSource()=default;
    DecorLayoutSource(const DecorLayoutSource&)=delete;
    DecorLayoutSource& operator=(const DecorLayoutSource&)=delete;
    bool initialize(DecorLayout embedded);
    LayoutLoadResult loadBytes(const uint8_t* bytes,size_t length);
    LayoutLoadResult reload(const char* path);
    void reset(){external_=false;}
    DecorLayout layout()const {
        return external_ ? DecorLayout{placements_.data(),count_} : embedded_;
    }
    bool external()const{return external_;}
private:
    DecorLayout embedded_{};
    std::array<DecorPlacement,kDecorMaxObjects> placements_{};
    uint16_t count_=0;
    bool external_=false;
};
}
