#include "terrain_source.hpp"

namespace vpd {
int terrainScale(const SpriteAtlas& a){
    if(!a.pixels||a.frame_count!=4||a.frame_width!=a.frame_height||
       a.frame_width<4||a.frame_width>32||32%a.frame_width!=0)
        return -1;
    const int scale=32/a.frame_width;
    return scale>=1&&scale<=8?scale:-1;
}
unsigned terrainFrame(bool above,bool left,bool right,int tx,int ty){
    // Two surface patterns; exposed edges and internal masonry.
    if(!above)return static_cast<unsigned>((tx+ty)&1);
    if(!left)return 2;
    if(!right)return 3;
    return 1;
}
bool TerrainSource::initialize(const uint8_t* bytes,size_t size){
    embedded_=nullptr;
    embedded_size_=0;
    SpriteAtlas validated{};
    if(!openAtlas(validated,bytes,size)||terrainScale(validated)<0 ||
       !source_.initialize(bytes,size,4))return false;
    embedded_=bytes;
    embedded_size_=size;
    return true;
}
TerrainReload TerrainSource::reload(const char* path){
    if(!embedded_)return TerrainReload::Uninitialized;
    AssetSource candidate;
    if(!candidate.initialize(embedded_,embedded_size_,4))
        return TerrainReload::Uninitialized;
    const AtlasLoadResult status=candidate.reloadFromFile(path);
    if(status==AtlasLoadResult::FileMissing)return TerrainReload::Missing;
    if(status!=AtlasLoadResult::Loaded)return TerrainReload::Invalid;
    if(terrainScale(candidate.atlas())<0)return TerrainReload::UnsupportedGeometry;
    if(!source_.swapLoaded(candidate))return TerrainReload::Invalid;
    return TerrainReload::Loaded;
}
}
