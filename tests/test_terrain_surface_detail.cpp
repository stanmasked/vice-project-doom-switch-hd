// Deterministic synthesized terrain edge material, ROM-free and asset-free.
#include "terrain_surface_detail.hpp"
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <cstdio>
#include <vector>
namespace {
void require(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
struct Map {
    bool cells[15][24]{};
};
bool solid(void* user,int x,int y){
    auto& map=*static_cast<Map*>(user);
    return x>=0 && x<24 && y>=0 && y<15 && map.cells[y][x];
}
bool empty(void*,int,int){return false;}
constexpr int width=512,height=720,stride=531;
constexpr uint32_t original=0x7f203040u;
std::vector<uint32_t> blank(){
    return std::vector<uint32_t>(static_cast<std::size_t>(height)*stride,original);
}
uint32_t pixel(const std::vector<uint32_t>& b,int x,int y){
    return b[static_cast<std::size_t>(y)*stride+x];
}
}
int main(){
 try{
    using vpd::applyTerrainSurfaceDetail;
    Map map{};
    map.cells[14][4]=true;
    map.cells[14][5]=true; // blocks the left edge of tile 5
    map.cells[13][4]=true; // blocks the top rim of tile 4 at y 14
    map.cells[11][9]=true; // independent raised ledge
    const auto clean=blank();
    auto pixels=clean;
    require(!applyTerrainSurfaceDetail(nullptr,width,height,stride,0,&map,solid),
            "null target was accepted");
    require(!applyTerrainSurfaceDetail(pixels.data(),width,height,width-1,
                                       0,&map,solid),
            "short stride was accepted");
    require(!applyTerrainSurfaceDetail(pixels.data(),width,height,stride,
                                       0,&map,nullptr),
            "null map callback was accepted");
    require(!applyTerrainSurfaceDetail(pixels.data(),0,height,stride,
                                       0,&map,solid),
            "zero canvas was accepted");
    require(!applyTerrainSurfaceDetail(pixels.data(),8193,height,9000,
                                       0,&map,solid),
            "unbounded canvas was accepted");
    require(pixels==clean,"invalid arguments corrupted framebuffer");
    require(applyTerrainSurfaceDetail(pixels.data(),width,height,stride,
                                      0,&map,empty) && pixels==clean,
            "empty map changed framebuffer");
    require(applyTerrainSurfaceDetail(pixels.data(),width,height,stride,
                                      0,&map,solid),
            "valid map rendering rejected");
    require(pixels!=clean,"material surface treatment generated no pixels");
    constexpr int sy=(14*16+80)*2;
    constexpr int sx4=4*16*2,sx5=5*16*2;
    require(pixel(pixels,sx4+12,sy)==original,
            "buried tile top incorrectly received an exposed rim");
    require(pixel(pixels,sx5+12,sy)!=original,
            "uncovered tile top did not receive exposed rim");
    require(pixel(pixels,sx4+1,sy+15)!=original,
            "exposed tile left edge is not shaded");
    require(pixel(pixels,sx5+1,sy+15)==original,
            "connected tiles have a false internal left shadow");
    require((pixel(pixels,sx5+12,sy)&0xff000000u)==0x7f000000u,
            "RGBA source alpha was overwritten");
    for(int y=0;y<height;++y)
        for(int x=width;x<stride;++x)
            require(pixel(pixels,x,y)==original,
                    "surface relief wrote into row-padding guard");
    auto repeat=clean;
    require(applyTerrainSurfaceDetail(repeat.data(),width,height,stride,
                                      0,&map,solid) && repeat==pixels,
            "fixed map/camera is not pixel deterministic");
    auto shifted=clean;
    require(applyTerrainSurfaceDetail(shifted.data(),width,height,stride,
                                      16,&map,solid),
            "camera-scrolled material rendering failed");
    // The same world-space tile must retain the exact material color
    // even when the viewport moves one 16px gameplay tile (32 HD px).
    for(int y=sy;y<sy+32;++y)
        for(int x=sx5;x<sx5+32;++x)
            require(pixel(pixels,x,y)==pixel(shifted,x-32,y),
                    "material detail swims when the camera scrolls");
    auto extreme=clean;
    require(applyTerrainSurfaceDetail(extreme.data(),width,height,stride,
                                      std::numeric_limits<int32_t>::min(),
                                      &map,solid) && extreme==clean,
            "minimum camera overflow caused spurious surfaces");
    require(applyTerrainSurfaceDetail(extreme.data(),width,height,stride,
                                      std::numeric_limits<int32_t>::max(),
                                      &map,solid) && extreme==clean,
            "maximum camera overflow caused spurious surfaces");
    std::puts("VPD_HD_TERRAIN_SURFACE_PASS exposed_top=yes buried_top=no "
              "left_edge=yes internal_seam=no world_locked_scroll=yes "
              "padding_untouched=yes alpha_preserved=yes "
              "deterministic=yes extreme_camera_safe=yes "
              "original_game_proven=no");
    return 0;
 }catch(const std::exception& e){
    std::fprintf(stderr,"VPD_HD_TERRAIN_SURFACE_FAIL %s\n",e.what());
    return 1;
 }
}
