#pragma once
#include <algorithm>
#include <cstddef>
#include <cstdint>

// Original-STYLE ROM-free driving-stage rendering *prototype*.
// The Y=196 boundary is a manual classification of private 256x240
// original-game screenshots. It is NOT a calibrated PPU raster scanline.
// This intentionally contains no captured tiles, CHR, FM2 or ROM bytes.
namespace vpd {
constexpr int kDrivingSourceWidth = 256;
constexpr int kDrivingSourceHeight = 240;
constexpr int kDrivingHudStartSourceY = 196;
constexpr int kDrivingPreviewWidth = 1280;
constexpr int kDrivingPreviewHeight = 720;
constexpr int kDrivingHudTop = 588;  // (196 / 240) * 720.
static_assert(kDrivingHudTop * kDrivingSourceHeight ==
              kDrivingHudStartSourceY * kDrivingPreviewHeight,
              "Original image-space HUD boundary mapping changed");

struct DrivingPreviewView {
    uint32_t frame=0;
    int road_phase=0;  // invented visual-only stripe offset; not real camera speed
    uint32_t ticks=0;  // prototype timer; not extracted NES timer
    uint8_t health=5;  // HUD visualization only; no original car physics
    bool show_car=true;
    int car_x=640;
    int obstacle_x=640;
    int obstacle_y=20;
    bool show_obstacle=false; // invented traffic fixture
    bool impact_flash=false;
    uint8_t speed=3;
};

namespace driving_detail {
constexpr uint32_t rgba(unsigned r,unsigned g,unsigned b) {
    return 0xff000000u | (b<<16) | (g<<8) | r;
}
constexpr uint32_t kRoadEdge=rgba(77,89,101);
constexpr uint32_t kRoad=rgba(42,50,66);
constexpr uint32_t kHudBase=rgba(17,25,39);
constexpr uint32_t kHudBorder=rgba(182,168,113);
constexpr uint32_t kAccent=rgba(223,177,104);
struct Canvas {
    uint32_t* buffer;
    int stride;
    int low;
    int high;
    void rect(int x,int y,int w,int h,uint32_t color) {
        if(w<=0 || h<=0)return;
        const int x0=std::max(0,x), x1=std::min(kDrivingPreviewWidth,x+w);
        const int y0=std::max(low,y), y1=std::min(high,y+h);
        if(x0>=x1||y0>=y1)return;
        for(int row=y0;row<y1;++row)
            std::fill(buffer+static_cast<std::size_t>(row)*stride+x0,
                      buffer+static_cast<std::size_t>(row)*stride+x1,color);
    }
};
inline void digit(Canvas& c,int x,int y,unsigned number,uint32_t color) {
    // Original-free 7-segment diagnostic typeface, 16x27.
    static constexpr uint8_t parts[10]={
        0x3f,0x06,0x5b,0x4f,0x66,0x6d,0x7d,0x07,0x7f,0x6f};
    if(number>9)return;
    const uint8_t mask=parts[number];
    if(mask&0x01)c.rect(x+3,y,10,3,color);
    if(mask&0x02)c.rect(x+13,y+3,3,9,color);
    if(mask&0x04)c.rect(x+13,y+15,3,9,color);
    if(mask&0x08)c.rect(x+3,y+24,10,3,color);
    if(mask&0x10)c.rect(x,y+15,3,9,color);
    if(mask&0x20)c.rect(x,y+3,3,9,color);
    if(mask&0x40)c.rect(x+3,y+12,10,3,color);
}
inline void number(Canvas& c,int x,int y,uint32_t value,unsigned digits,
                   uint32_t color) {
    // Always displays exactly digits digits; fixed bound, no allocations.
    if(digits==0 || digits>9)return;
    uint32_t scale=1;
    for(unsigned i=1;i<digits;++i)scale*=10u;
    for(unsigned i=0;i<digits;++i) {
        digit(c,x+static_cast<int>(i)*21,y,(value/scale)%10u,color);
        scale=scale==1?1:scale/10;
    }
}
inline void drawRoad(Canvas& road,const DrivingPreviewView& view) {
    // All writes are hard-clipped to y=[0,588). No HUD damage is possible.
    const uint32_t shoulders=rgba(61,80,76), verge=rgba(82,93,87);
    road.rect(0,0,kDrivingPreviewWidth,kDrivingHudTop,shoulders);
    const int bend=static_cast<int>((view.frame/30u)%7u)-3;
    const int left=268+bend*7;
    const int right=1012+bend*7;
    road.rect(left-24,0,right-left+48,kDrivingHudTop,verge);
    road.rect(left,0,right-left,kDrivingHudTop,kRoad);
    road.rect(left+9,0,8,kDrivingHudTop,kRoadEdge);
    road.rect(right-17,0,8,kDrivingHudTop,kRoadEdge);
    // One visual-only scrolling marker stream. It is NOT NES scroll speed.
    const int offset=((view.road_phase%72)+72)%72;
    for(int y=-72+offset;y<kDrivingHudTop;y+=72) {
        road.rect(634+bend*7,y,12,32,rgba(191,190,164));
    }
    // Invented traffic rectangle; fully clipped above the HUD.
    if(view.show_obstacle) {
        road.rect(view.obstacle_x-35,view.obstacle_y-40,
                  70,80,rgba(33,33,50));
        road.rect(view.obstacle_x-27,view.obstacle_y-32,
                  54,63,rgba(58,131,155));
        road.rect(view.obstacle_x-18,view.obstacle_y-19,
                  36,22,rgba(166,200,187));
    }
    // Placeholder player car, controlled by an independent ROM-free model.
    if(view.show_car) {
        const int x=view.car_x, y=433;
        road.rect(x-44,y,88,105,rgba(20,28,44));
        road.rect(x-35,y+7,70,88,
                  view.impact_flash?rgba(232,200,126):rgba(163,47,63));
        road.rect(x-26,y+24,52,32,rgba(96,152,166));
        road.rect(x-30,y+74,60,8,rgba(226,179,101));
        road.rect(x-51,y+21,12,25,rgba(23,26,33));
        road.rect(x+39,y+21,12,25,rgba(23,26,33));
    }
}
inline void drawHud(Canvas& hud,const DrivingPreviewView& view) {
    // All writes are hard-clipped to y=[588,720). No road damage possible.
    hud.rect(0,kDrivingHudTop,kDrivingPreviewWidth,
             kDrivingPreviewHeight-kDrivingHudTop,kHudBase);
    hud.rect(0,kDrivingHudTop,kDrivingPreviewWidth,5,kHudBorder);
    hud.rect(36,kDrivingHudTop+21,170,8,rgba(112,126,153));
    hud.rect(36,kDrivingHudTop+36,100,4,kAccent);
    number(hud,36,kDrivingHudTop+66,view.ticks%1000000u,6,
           rgba(235,222,192));
    hud.rect(416,kDrivingHudTop+22,136,6,rgba(76,112,127));
    // Counter bars use live view input; disabled/zero is still HUD-only.
    const unsigned bars=std::min<unsigned>(view.health,5u);
    for(unsigned i=0;i<bars;++i)
        hud.rect(416+static_cast<int>(i)*28,kDrivingHudTop+47,
                 21,26,rgba(211,85,91));
    hud.rect(820,kDrivingHudTop+24,180,5,kHudBorder);
    hud.rect(820,kDrivingHudTop+43,180,4,rgba(69,94,114));
    // Prototype speed readout: no original driving-speed claim.
    number(hud,1095,kDrivingHudTop+63,view.speed,1,kAccent);
    number(hud,833,kDrivingHudTop+64,view.frame%10000u,4,kAccent);
    hud.rect(1092,kDrivingHudTop+23,146,11,rgba(42,94,112));
}
}  // namespace driving_detail

inline bool drawDrivingPreview(uint32_t* target,int width,int height,
                               int stride_pixels,
                               const DrivingPreviewView& view) {
    if(!target || width!=kDrivingPreviewWidth ||
       height!=kDrivingPreviewHeight || stride_pixels<width)
        return false;
    driving_detail::Canvas road{target,stride_pixels,0,kDrivingHudTop};
    driving_detail::Canvas hud{target,stride_pixels,kDrivingHudTop,height};
    driving_detail::drawRoad(road,view);
    driving_detail::drawHud(hud,view);
    return true;
}
}  // namespace vpd
