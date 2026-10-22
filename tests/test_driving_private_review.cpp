#include "driving_road_private_bundle.hpp"
#include "driving_private_review_mode.hpp"
#include "driving_preview.hpp"
#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
static void need(bool x,const char* message){
    if(!x)throw std::runtime_error(message);
}
static void put16(std::uint8_t* x,std::uint16_t v){
    x[0]=static_cast<std::uint8_t>(v);
    x[1]=static_cast<std::uint8_t>(v>>8);
}
static void put32(std::uint8_t* x,std::uint32_t v){
    for(unsigned i=0;i<4;++i)x[i]=static_cast<std::uint8_t>(v>>(8*i));
}
static std::array<std::uint8_t,vpd::private_road::kBundleBytes>
makeFixture(){
    using namespace vpd::private_road;
    std::array<std::uint8_t,kBundleBytes> blob{};
    for(unsigned i=0;i<8;++i)blob[i]=kMagic[i];
    put16(blob.data()+8,1);put16(blob.data()+10,37);
    std::size_t index=0;
    for(std::uint16_t f=600;f<=920;f+=8){
        if(rejectedFrame(f))continue;
        std::uint8_t left=66,right=188;
        if(const auto* known=vpd::road_reference::atExactFrame(f)){
            left=known->left;right=known->right;
        }
        auto* dst=blob.data()+16+index*4;
        put16(dst,f);dst[2]=left;dst[3]=right;
        ++index;
    }
    put32(blob.data()+12,crc32(blob.data()+16,148));
    return blob;
}
int main(){
    vpd::private_road::PrivateRoadBundle data;
    vpd::PrivateRoadReviewMode mode;
    need(!mode.cycle(true,true,true,data) && !mode.active(),
         "review unexpectedly enables when private file is missing");
    const auto blob=makeFixture();
    need(data.loadBytes(blob.data(),blob.size()),
         "synthetic complete private bundle rejected");
    need(!mode.cycle(false,true,true,data) &&
         !mode.cycle(true,false,true,data) &&
         !mode.cycle(true,true,false,data),
         "manual-only three-key selector bypassed");
    const int w=vpd::kDrivingPreviewWidth,h=vpd::kDrivingPreviewHeight;
    constexpr int pitch=1280+13;
    constexpr std::uint32_t sentinel=0x87654321u;
    std::vector<std::uint32_t> pixel(static_cast<std::size_t>(pitch)*h,sentinel);
    std::vector<std::uint32_t> normal(pixel.size(),sentinel);
    vpd::DrivingPreviewView view{};
    need(vpd::drawDrivingPreview(normal.data(),w,h,pitch,view),
         "original ROM-free source scene unavailable");
    const auto player_pixel=normal[450*pitch+640];
    const auto hud_pixel=normal[637*pitch+418];
    constexpr auto panel=vpd::driving_detail::rgba(14,24,34);
    constexpr auto border=vpd::driving_detail::rgba(233,190,117);
    constexpr auto fill=vpd::driving_detail::rgba(98,143,132);
    for(std::size_t i=0;i<37;++i){
        need(mode.cycle(true,true,true,data) && mode.active(),
             "native manual private sample selector rejected");
        const auto* selected=mode.selected(data);
        need(selected && selected==data.byIndex(i),
             "private sample display order differs from validated file");
        view.private_road_enabled=true;
        view.private_original_frame=selected->frame;
        view.private_left=selected->left;
        view.private_right=selected->right;
        need(vpd::drawDrivingPreview(pixel.data(),w,h,pitch,view),
             "private numerical sample raster failed");
        const auto hd=vpd::road_reference::toHdImageSpace(*selected);
        const int y=171;
        need(pixel[y*pitch+hd.left-1]==panel &&
             pixel[y*pitch+hd.left]==border &&
             pixel[y*pitch+hd.left+15]==fill &&
             pixel[y*pitch+hd.right_inclusive-15]==fill &&
             pixel[y*pitch+hd.right_inclusive]==border &&
             pixel[y*pitch+hd.right_inclusive+1]==panel,
             "source X interval missing or shifted in 1280px raster");
        need(pixel[450*pitch+640]==player_pixel &&
             pixel[637*pitch+418]==hud_pixel,
             "opt-in source strip changed car or HUD pixels");
        for(int row=0;row<h;++row)
            for(int x=w;x<pitch;++x)
                need(pixel[row*pitch+x]==sentinel,
                     "private visual preview wrote into framebuffer pitch padding");
    }
    need(!data.atExactFrame(712) && !data.atExactFrame(720) &&
         !data.atExactFrame(728) && !data.atExactFrame(736),
         "ambiguous 4 original RGB observations invented");
    need(mode.cycle(true,true,true,data) && !mode.active() &&
         !mode.selected(data),"38th edge did not return to OFF");
    view.private_road_enabled=false;
    need(vpd::drawDrivingPreview(pixel.data(),w,h,pitch,view),
         "original invented preview failed to restore");
    need(pixel[171*pitch+40]==normal[171*pitch+40] &&
         pixel[450*pitch+640]==player_pixel,
         "private source reviewer left persistent on-screen art");
    need(mode.cycle(true,true,true,data),"selector failed after clean OFF");
    mode.reset();
    need(!mode.active(),"private numeric review state not reset");
    data.clear();
    need(!mode.cycle(true,true,true,data) && !mode.selected(data),
         "invalid private source reused cached sample");
    std::cout<<"VPD_ROMFREE_PRIVATE_37_ROAD_REVIEW_PASS"
             <<" synthetic_source_frames=37 ambiguous_skipped=4"
             <<" original_assets_included=no collision_camera_proven=no"
             <<" default_platform_hud_intact=yes\n";
}
