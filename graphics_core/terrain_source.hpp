#pragma once
#include "asset_source.hpp"
#include <cstddef>
#include <cstdint>

namespace vpd {

// Four independently drawn tiles, displayed at a fixed 32x32 screen size.
// Only square 4/8/16/32px cells can be displayed with the VPAT nearest
// neighbor scale 8/4/2/1. Invalid geometry is never activated.
int terrainScale(const SpriteAtlas& atlas);
unsigned terrainFrame(bool solid_above,bool solid_left,bool solid_right,
                      int tile_x,int tile_y);

enum class TerrainReload : uint8_t {
    Loaded, Missing, Invalid, UnsupportedGeometry, Uninitialized
};
class TerrainSource {
public:
    bool initialize(const uint8_t* bytes,size_t size);
    TerrainReload reload(const char* path);
    void reset() { source_.resetToEmbedded(); }
    const SpriteAtlas& atlas() const { return source_.atlas(); }
    bool external() const { return source_.external(); }
private:
    const uint8_t* embedded_=nullptr;
    size_t embedded_size_=0;
    AssetSource source_{};
};
}
