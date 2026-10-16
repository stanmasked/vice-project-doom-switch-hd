#pragma once
#include "asset_source.hpp"
#include <cstddef>
#include <cstdint>

namespace vpd {

// A two-frame alpha VPAT: far skyline and near skyline. Their rendered
// frame size is fixed at 512x384 regardless of source sampling density.
int backdropScale(const SpriteAtlas& atlas);
int parallaxOffset(int camera_pixels,int divisor,int span_pixels);
bool drawBackdropLayers(uint32_t* pixels,int width,int height,int stride,
                        const SpriteAtlas& atlas,int camera_pixels);

enum class BackdropReload : uint8_t {
    Loaded, Missing, Invalid, UnsupportedGeometry, Uninitialized
};
class BackdropSource {
public:
    bool initialize(const uint8_t* bytes,size_t size);
    BackdropReload reload(const char* path);
    void reset(){source_.resetToEmbedded();}
    const SpriteAtlas& atlas() const{return source_.atlas();}
    bool external() const{return source_.external();}
private:
    const uint8_t* embedded_=nullptr;
    size_t embedded_size_=0;
    AssetSource source_{};
};
}
