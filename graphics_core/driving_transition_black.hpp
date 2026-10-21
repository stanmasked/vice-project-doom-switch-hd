#pragma once
#include <cstdint>
#include <cstddef>
// Actual framebuffer fill for a scene-independent blackout. No ROM pixels.
// The alpha byte is fully opaque in native RGBA8888.
namespace vpd {
inline bool drawDrivingBlackout(std::uint32_t* pixels,int width,int height,int stride) {
    if(!pixels || width!=1280 || height!=720 || stride<width)return false;
    for(int y=0;y<height;++y) {
        for(int x=0;x<width;++x)
            pixels[static_cast<std::size_t>(y)*stride+x]=0xff000000u;
    }
    return true;
}
} // namespace vpd
