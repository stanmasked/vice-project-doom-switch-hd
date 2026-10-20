#pragma once
// Native and host share a strictly bounded, ROM-free scene fingerprint.
// Excludes the top/right HD FX status overlay: a pixel difference here must
// come from authored scene effects, not merely from the ON/OFF label.
#include <cstdint>
namespace vpd {
struct HdFxGuestFingerprint {
    uint64_t hash=14695981039346656037ull;
    unsigned pixels=0;
};
inline HdFxGuestFingerprint fingerprintHdFxVisual(
    const uint32_t* pixels,int width,int height,int stride_pixels){
    HdFxGuestFingerprint result{};
    if(!pixels || width<900 || height<620 || stride_pixels<width)
        return result;
    // Haze lanes, grounded dust, actor impact light and sentry projectiles
    // may all affect this region. Never read framebuffer row padding.
    for(int y=160;y<620;++y)
        for(int x=0;x<900;++x){
            const uint32_t pixel=pixels[
                static_cast<unsigned>(y)*static_cast<unsigned>(stride_pixels)+
                static_cast<unsigned>(x)];
            result.hash^=pixel;
            result.hash*=1099511628211ull;
            ++result.pixels;
        }
    return result;
}
} // namespace vpd
