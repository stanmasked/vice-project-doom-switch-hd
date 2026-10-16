#pragma once
#include "animation.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
namespace vpd {
// VANM v1 legacy / v2 atlas-bound: header 18/22 bytes + descriptors + frame records.
// This resource owns all frame records. It cannot be moved or copied because
// AnimationClip exposes pointers into its fixed-size frame array.
constexpr size_t kMaxAnimationFrames=256;
constexpr size_t kMaxAnimationFileBytes=38+4*kMaxAnimationFrames;
enum class AnimationLoadResult : uint8_t {
    Loaded, Missing, IoError, Invalid, AtlasMismatch, AtlasIdentityMismatch, Uninitialized
};
class AnimationResource {
public:
    AnimationResource()=default;
    AnimationResource(const AnimationResource&)=delete;
    AnimationResource& operator=(const AnimationResource&)=delete;
    bool initialize(const AnimationBank& embedded);
    AnimationLoadResult loadBytes(const uint8_t* data,size_t size,uint16_t atlas_frames,
                                  uint32_t atlas_pixel_crc32=0);
    AnimationLoadResult loadFile(const char* path,uint16_t atlas_frames,
                                 uint32_t atlas_pixel_crc32=0);
    void reset();
    void swapExternal(AnimationResource& other);
    const AnimationBank& bank() const { return external_?runtime_:*embedded_; }
    bool external() const { return external_; }
    bool initialized() const { return embedded_!=nullptr; }
private:
    void rebuildPointers();
    const AnimationBank* embedded_=nullptr;
    AnimationBank runtime_{};
    std::array<AnimationFrame,kMaxAnimationFrames> frames_{};
    std::array<uint8_t,4> counts_{};
    std::array<uint8_t,4> loops_{};
    bool external_=false;
};
}
