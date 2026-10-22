#include "driving_private_road_reject_witness.hpp"
#include "driving_preview.hpp"
#include <iostream>
#include <stdexcept>
#include <vector>
static void ensure(bool x,const char* why){
    if(!x)throw std::runtime_error(why);
}
int main(){
    vpd::private_road::PrivateRoadBundle unavailable;
    vpd::PrivateRoadReviewMode mode;
    vpd::PrivateRoadRejectProof witness;
    vpd::DrivingPreviewView view{};
    constexpr int w=vpd::kDrivingPreviewWidth,h=vpd::kDrivingPreviewHeight;
    constexpr int pitch=w+9;
    std::vector<std::uint32_t> pixels(static_cast<std::size_t>(pitch)*h);
    view.frame=7;
    ensure(vpd::drawDrivingPreview(pixels.data(),w,h,pitch,view),
           "standard fallback framebuffer missing");
    const auto bad=witness.observe(true,true,true,unavailable,mode,view,
                                   pixels.data(),pitch,999);
    ensure(bad.valid && bad.frame==7 &&
           bad.neutral_shoulder==vpd::driving_detail::rgba(61,80,76) &&
           bad.neutral_road==vpd::driving_detail::rgba(42,50,66),
           "invalid file could not produce source-owned rejection");
    ensure(!witness.observe(true,true,true,unavailable,mode,view,
            pixels.data(),pitch,999).valid,
           "same emulator R3 edge forged repeated evidence");
    vpd::PrivateRoadRejectProof noHostProof;
    ensure(!noHostProof.observe(true,true,false,unavailable,mode,view,
            pixels.data(),pitch,999).valid,
           "host-only false R3 proof accepted");
    vpd::RoadProfileReviewMode builtin;
    ensure(builtin.cycle(true,true,true),"Y fallback not selectable");
    view.observed_road_frame=builtin.originalFrame();
    ensure(view.observed_road_frame==600 &&
           vpd::drawDrivingPreview(pixels.data(),w,h,pitch,view),
           "built-in Y reference broken by missing SD file");
    ensure(pixels[171*pitch+330]==
               vpd::driving_detail::rgba(233,190,117),
           "fallback Y original numeric X interval absent");
    vpd::PrivateRoadRejectProof afterY;
    ensure(!afterY.observe(true,true,true,unavailable,mode,view,
            pixels.data(),pitch,999).valid,
           "invalid SD fallback wrongfully treated built-in Y as plain road");
    std::cout<<"VPD_ROMFREE_ROAD_SD_REJECT_WITNESS_PASS"
             <<" actual_edge_needed=yes builtin_y_fallback=yes"
             <<" owner_private_data_absent=yes\n";
}
