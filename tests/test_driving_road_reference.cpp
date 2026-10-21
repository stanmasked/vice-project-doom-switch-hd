#include "driving_road_reference.hpp"
#include <cstdint>
#include <initializer_list>
#include <iostream>
#include <stdexcept>
static void ck(bool yes,const char* why){if(!yes)throw std::runtime_error(why);}
int main() {
    using namespace vpd::road_reference;
    constexpr int widths[]={123,123,92,59,56,88,88};
    constexpr int centers2[]={254,254,255,254,255,255,319};
    constexpr int starts[]={330,330,410,490,500,420,580};
    constexpr int ends[]={944,944,869,784,779,859,1019};
    ck(valid() && kObserved.size()==7,"source table corrupt");
    for(std::size_t i=0;i<kObserved.size();++i){
        const auto& s=kObserved[i];
        ck(atExactFrame(s.frame)==&s,"exact original frame lookup failed");
        ck(s.width()==widths[i],"source visible width changed");
        ck(s.center_twice()==centers2[i],"source center shifted");
        auto hd=toHdImageSpace(s);
        ck(hd.left==starts[i] && hd.right_inclusive==ends[i],
           "image-space scaling incorrect");
        ck(hd.width==widths[i]*5 && hd.width==hd.right_inclusive-hd.left+1,
           "inclusive HD image interval is inconsistent");
    }
    for(std::uint32_t frame : {0u,599u,601u,700u,745u,783u,
                               785u,799u,801u,841u,921u,3606u})
        ck(atExactFrame(frame)==nullptr,
           "interpolation/extrapolation invented an original observation");
    ck(kObserved[6].center_twice()-kObserved[0].center_twice()==65,
       "late image-center shift reference lost");
    std::cout<<"VPD_ROMFREE_ROAD_CROSS_SECTION_PASS samples=7"
             <<" x_nes=256 x_hd=1280 exact_frame_only=yes"
             <<" original_road_collision_proven=no camera_speed_proven=no"
             <<" copyrighted_pixels_included=no\n";
}
