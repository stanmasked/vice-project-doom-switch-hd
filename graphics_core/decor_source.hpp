#pragma once
#include "asset_source.hpp"
#include <cstddef>
#include <cstdint>

namespace vpd {
// Independently-authored scenery decorations: 4 frames in an RGBA VPAT.
// Each cell renders to 48x64; accepted source cells: 12x16, 24x32, 48x64.
int decorScale(const SpriteAtlas& atlas);
int decorativeWorldX(int index);
unsigned decorFrame(int index,uint32_t simulation_tick);
bool drawDecorLayer(uint32_t* target,int width,int height,int stride,
                    const SpriteAtlas& atlas,int camera_px,uint32_t tick,
                    bool foreground);
enum class DecorReload : uint8_t {
    Loaded, Missing, Invalid, UnsupportedGeometry, Uninitialized
};
class DecorSource {
public:
    bool initialize(const uint8_t* embedded,size_t size);
    DecorReload reload(const char* path);
    void reset(){source_.resetToEmbedded();}
    const SpriteAtlas& atlas()const{return source_.atlas();}
    bool external()const{return source_.external();}
private:
    const uint8_t* embedded_=nullptr;
    size_t embedded_size_=0;
    AssetSource source_{};
};
}
