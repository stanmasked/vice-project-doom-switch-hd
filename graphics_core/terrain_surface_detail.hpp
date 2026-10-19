#pragma once
// Opt-in synthetic terrain material relief for the ROM-free HD prototype.
// Original game tiles and user-provided terrain atlases are not altered.
// All coordinates are world-anchored; no randomness, timing or game state.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <limits>

namespace vpd {
namespace terrain_surface_detail {
inline int64_t floorDiv(int64_t x,int64_t d) {
    return x/d-(x%d<0 ? 1 : 0);
}
inline uint32_t blend(uint32_t original,uint32_t color,unsigned strength) {
    // The alpha channel is preserved exactly, including nonopaque inputs.
    uint32_t result=original&0xff000000u;
    for(unsigned channel=0;channel<3;++channel){
        const unsigned shift=channel*8u;
        const unsigned source=(original>>shift)&255u;
        const unsigned target=(color>>shift)&255u;
        result|=((source*(64u-strength)+target*strength+32u)/64u)<<shift;
    }
    return result;
}
inline void tintRect(uint32_t* pixels,int width,int height,int stride,
                     int64_t x,int64_t y,int rect_w,int rect_h,
                     uint32_t tint,unsigned strength){
    if(rect_w<=0 || rect_h<=0 || strength==0)return;
    const int x0=static_cast<int>(std::clamp<int64_t>(x,0,width));
    const int x1=static_cast<int>(std::clamp<int64_t>(x+rect_w,0,width));
    const int y0=static_cast<int>(std::clamp<int64_t>(y,0,height));
    const int y1=static_cast<int>(std::clamp<int64_t>(y+rect_h,0,height));
    for(int sy=y0;sy<y1;++sy)
        for(int sx=x0;sx<x1;++sx){
            auto& pixel=pixels[static_cast<std::size_t>(sy)*stride+sx];
            pixel=blend(pixel,tint,strength);
        }
}
inline uint32_t tileHash(int64_t tx,int ty){
    uint32_t h=static_cast<uint32_t>(tx)*0x9e3779b9u+
               static_cast<uint32_t>(ty)*0x85ebca6bu+0x20f6314fu;
    h^=h>>16;h*=0x7feb352du;h^=h>>15;
    h*=0x846ca68bu;h^=h>>16;
    return h;
}
} // namespace terrain_surface_detail

// Material relief only on *exposed* top and left edges of solid tiles.
// The callback must describe the same 16px collision map as the renderer.
// Never writes beyond visible width, including arbitrary row padding.
// Invalid arguments are rejected without modifying the framebuffer.
inline bool applyTerrainSurfaceDetail(
    uint32_t* pixels,int width,int height,int stride_pixels,
    int32_t camera_world_x,void* map_context,
    bool (*solid_at)(void*,int,int)){
    if(!pixels || !solid_at || width<=0 || height<=0 ||
       width>8192 || height>8192 || stride_pixels<width)return false;
    constexpr int tile=16,scale=2,world_y_offset=80;
    const int64_t first=terrain_surface_detail::floorDiv(camera_world_x,tile)-1;
    const int64_t count=(static_cast<int64_t>(width)+tile*scale-1)/
                         (tile*scale)+3;
    for(int ty=0;ty<15;++ty){
        for(int64_t tx=first;tx<first+count;++tx){
            // No overflow and no callback on undefined map integer edges.
            if(tx<=std::numeric_limits<int>::min() ||
               tx>=std::numeric_limits<int>::max())continue;
            const int cx=static_cast<int>(tx);
            if(!solid_at(map_context,cx,ty))continue;
            const int64_t sx=(tx*tile-camera_world_x)*scale;
            const int64_t sy=static_cast<int64_t>(ty*tile+world_y_offset)*scale;
            // A slim directional rim illuminates open platform tops.
            // Under an adjacent solid tile there must be no such rim.
            if(!solid_at(map_context,cx,ty-1)){
                terrain_surface_detail::tintRect(
                    pixels,width,height,stride_pixels,sx,sy,32,2,
                    0xffa0a8b8u,14);
                terrain_surface_detail::tintRect(
                    pixels,width,height,stride_pixels,sx,sy+2,32,3,
                    0xff333b52u,7);
                // World-coordinate-seeded subtle material breakup. It is
                // fixed for every camera position and repeated render.
                const uint32_t hash=terrain_surface_detail::tileHash(tx,ty);
                const int offset=4+static_cast<int>(hash%23u);
                terrain_surface_detail::tintRect(
                    pixels,width,height,stride_pixels,sx+offset,sy+6,3,2,
                    0xff515564u,9);
            }
            if(!solid_at(map_context,cx-1,ty)){
                terrain_surface_detail::tintRect(
                    pixels,width,height,stride_pixels,sx,sy+5,3,27,
                    0xff252d37u,12);
            }
        }
    }
    return true;
}
} // namespace vpd
