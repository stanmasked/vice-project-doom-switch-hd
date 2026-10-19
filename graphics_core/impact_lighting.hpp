#pragma once
// Optional deterministic CPU post-lighting for live ROM-free combat.
// Colors are independent authored RGB values, not sampled NES artwork.
// RGBA8888 byte convention matches graphics_core/scene_renderer.cpp:
// red in least significant byte, alpha in most significant byte.
#include <algorithm>
#include <cstdint>
namespace vpd {
enum class ImpactLightColor : uint32_t {
    Hero  = 0xff74a6ffu, // warm red/orange in packed R,G,B little-endian
    Guard = 0xff7dcaffu, // gold
    Sentry= 0xffe5e16fu  // cyan
};
inline bool applyImpactLight(uint32_t* pixels,int width,int height,
                             int stride_pixels,int center_x,int center_y,
                             int radius,unsigned energy,
                             ImpactLightColor tint){
    if(!pixels || width<=0 || height<=0 || stride_pixels<width ||
       radius<=0 || radius>256 || energy>32u)return false;
    if(energy==0u)return true;
    // Use signed 64-bit intermediates so an offscreen actor never
    // overflows a clipping rectangle or corrupts framebuffer padding.
    const int64_t low_x=static_cast<int64_t>(center_x)-radius;
    const int64_t high_x=static_cast<int64_t>(center_x)+radius+1;
    const int64_t low_y=static_cast<int64_t>(center_y)-radius;
    const int64_t high_y=static_cast<int64_t>(center_y)+radius+1;
    const int x0=static_cast<int>(std::clamp<int64_t>(low_x,0,width));
    const int x1=static_cast<int>(std::clamp<int64_t>(high_x,0,width));
    const int y0=static_cast<int>(std::clamp<int64_t>(low_y,0,height));
    const int y1=static_cast<int>(std::clamp<int64_t>(high_y,0,height));
    const int64_t rr=static_cast<int64_t>(radius)*radius;
    const uint32_t color=static_cast<uint32_t>(tint);
    for(int y=y0;y<y1;++y){
        const int64_t dy=static_cast<int64_t>(y)-center_y;
        for(int x=x0;x<x1;++x){
            const int64_t dx=static_cast<int64_t>(x)-center_x;
            const int64_t dist=dx*dx+dy*dy;
            if(dist>=rr)continue;
            const unsigned weight=static_cast<unsigned>(
                static_cast<int64_t>(energy)*(rr-dist)/rr);
            if(weight==0)continue;
            uint32_t& p=pixels[static_cast<std::size_t>(y)*
                               static_cast<std::size_t>(stride_pixels)+x];
            const uint32_t previous=p;
            uint32_t mixed=0xff000000u;
            for(unsigned channel=0;channel<3u;++channel){
                const unsigned shift=channel*8u;
                const unsigned base=(previous>>shift)&255u;
                const unsigned light=(color>>shift)&255u;
                const unsigned next=(base*(64u-weight)+
                                     light*weight+32u)/64u;
                mixed|=next<<shift;
            }
            p=mixed;
        }
    }
    return true;
}
} // namespace vpd
