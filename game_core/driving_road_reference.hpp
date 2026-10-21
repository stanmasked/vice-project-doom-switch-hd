#pragma once
#include <array>
#include <cstdint>
// Owner-private FCEUX RGB visible-road cross sections. These are NOT road
// colliders, camera positions, motion speeds, or original graphics.
namespace vpd::road_reference {
struct CrossSection {
    std::uint16_t frame;
    std::uint8_t left,right;
    constexpr int width() const noexcept {return int(right)-left+1;}
    constexpr int center_twice() const noexcept {return int(left)+right;}
};
constexpr std::array<CrossSection,7> kObserved = {{
    {600,66,188}, {744,66,188}, {760,82,173}, {784,98,156},
    {800,100,155}, {840,84,171}, {920,116,203},
}};
constexpr const CrossSection* atExactFrame(std::uint32_t frame) noexcept {
    for(const auto& s:kObserved)if(s.frame==frame)return &s;
    return nullptr; // never interpolate or invent unobserved frames
}
struct HdImageInterval {int left,right_inclusive,width;};
constexpr HdImageInterval toHdImageSpace(const CrossSection& s) noexcept {
    return {int(s.left)*5, (int(s.right)+1)*5-1, s.width()*5};
}
constexpr bool valid() noexcept {
    std::uint16_t previous=0;
    for(const auto& s:kObserved) {
        if(s.frame<=previous || s.left>s.right || s.right>=255)return false;
        const auto hd=toHdImageSpace(s);
        if(hd.left<0 || hd.right_inclusive>=1280 ||
           hd.width!=hd.right_inclusive-hd.left+1)return false;
        previous=s.frame;
    }
    return true;
}
static_assert(valid(),"original source-free image-space reference malformed");
} // namespace vpd::road_reference
