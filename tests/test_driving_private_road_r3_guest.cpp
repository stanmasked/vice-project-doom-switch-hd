#include "driving_private_road_r3_witness.hpp"
#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
static void check(bool ok,const char* why){
    if(!ok)throw std::runtime_error(why);
}
static void u16(std::uint8_t* p,unsigned v){
    p[0]=static_cast<std::uint8_t>(v);
    p[1]=static_cast<std::uint8_t>(v>>8);
}
static void u32(std::uint8_t* p,std::uint32_t v){
    for(unsigned i=0;i<4;++i)p[i]=static_cast<std::uint8_t>(v>>(8*i));
}
int main(){
    using namespace vpd;
    using namespace vpd::private_road;
    std::array<std::uint8_t,kBundleBytes> bytes{};
    for(unsigned i=0;i<8;++i)bytes[i]=kMagic[i];
    u16(bytes.data()+8,1);u16(bytes.data()+10,37);
    unsigned accepted=0;
    for(std::uint16_t f=600;f<=920;f+=8){
        if(rejectedFrame(f))continue;
        auto* p=bytes.data()+16+4*accepted++;
        u16(p,f);
        if(const auto* a=road_reference::atExactFrame(f)){
            p[2]=a->left;p[3]=a->right;
        }else {p[2]=66;p[3]=188;}
    }
    check(accepted==37,"invented bundle has wrong count");
    u32(bytes.data()+12,crc32(bytes.data()+16,148));
    PrivateRoadBundle data;
    check(data.loadBytes(bytes.data(),bytes.size()),"invented bundle failed");
    PrivateRoadReviewMode mode;
    PrivateRoadR3GuestProof witness;
    constexpr int w=kDrivingPreviewWidth,h=kDrivingPreviewHeight,stride=w+11;
    std::vector<std::uint32_t> pixels(
        static_cast<std::size_t>(stride)*h,0);
    DrivingPreviewView view{};
    const std::uint64_t frozen_platform=0x123456789abcu;
    check(!witness.observe(true,true,false,data,mode,view,
            pixels.data(),stride,frozen_platform).valid,
          "guest witness accepted host-only input");
    for(unsigned i=0;i<38;++i){
        check(mode.cycle(true,true,true,data),
              "native R3 selector did not accept verified pad edge");
        view.frame=i+1;
        const auto* sample=mode.selected(data);
        view.private_road_enabled=sample!=nullptr;
        view.private_original_frame=sample?sample->frame:0;
        view.private_left=sample?sample->left:0;
        view.private_right=sample?sample->right:0;
        check(drawDrivingPreview(pixels.data(),w,h,stride,view),
              "real frame draw failed");
        if(i==0) {
            const auto hd=road_reference::toHdImageSpace(*sample);
            const auto index=static_cast<std::size_t>(171)*stride+hd.left;
            const auto pixel=pixels[index];
            pixels[index]=0;
            check(!witness.observe(true,true,true,data,mode,view,
                  pixels.data(),stride,frozen_platform).valid,
                  "tampered pixel created false R3 evidence");
            pixels[index]=pixel;
        }
        const auto out=witness.observe(true,true,true,data,mode,view,
                                      pixels.data(),stride,frozen_platform);
        check(out.valid && out.seq==i+1 && out.drive_frame==i+1 &&
              out.source_frame==(sample?sample->frame:0),
              "native R3 source frame did not match selector");
        if(sample){
            const auto hd=road_reference::toHdImageSpace(*sample);
            check(out.left_hd==hd.left &&
                  out.right_hd==hd.right_inclusive &&
                  out.marker_pixel==driving_detail::rgba(233,190,117),
                  "real source rectangle or private-mode tag wrong");
        }else{
            check(out.seq==38 && out.off_pixel==
                  driving_detail::rgba(61,80,76),
                  "38th physical R3 edge did not reach OFF");
        }
        check(!witness.observe(true,true,true,data,mode,view,
             pixels.data(),stride,frozen_platform).valid,
             "stale native guest frame duplicated");
    }
    check(!witness.observe(true,true,true,data,mode,view,
          pixels.data(),stride,frozen_platform).valid,
          "fake 39th R3 event accepted");
    std::cout<<"VPD_ROMFREE_PRIVATE_ROAD_R3_GUEST_PASS"
             <<" sample_edges=37 off_edge=1"
             <<" synthetic_only=yes hud_car_preserved=yes\n";
}
