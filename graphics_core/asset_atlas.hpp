#pragma once
#include <cstddef>
#include <cstdint>
namespace vpd {
// VPAT v1, uncompressed independently authored RGBA8888 atlas.
// Atlas is a non-owning view; underlying bytes must outlive it.
struct SpriteAtlas {
    const uint8_t* pixels=nullptr;
    uint16_t width=0, height=0, frame_width=0, frame_height=0;
    uint16_t frame_count=0;
    // CRC of validated uncompressed VPAT pixel payload (resource identity).
    uint32_t pixel_crc32=0;
};
constexpr size_t kVpatHeaderBytes=22;
bool openAtlas(SpriteAtlas& out,const uint8_t* bytes,size_t size);
// Alpha-blended nearest-neighbor frame. Returns false for invalid arguments.
bool blitAtlasFrame(uint32_t* target,int width,int height,int stride,
                    const SpriteAtlas& atlas,unsigned frame,int x,int y,int scale,
                    bool flip_x=false);
}
