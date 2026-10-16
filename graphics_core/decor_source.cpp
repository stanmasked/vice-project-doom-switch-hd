#include "decor_source.hpp"
#include <cstdint>
#include <limits>
#include "decor_layout.hpp"

namespace vpd {
int decorScale(const SpriteAtlas& a){
    if(!a.pixels||a.frame_count!=4||!a.frame_width||!a.frame_height||
       48%a.frame_width||64%a.frame_height)return -1;
    const int scale=48/a.frame_width;
    return scale>=1&&scale<=8&&a.frame_height*scale==64?scale:-1;
}
int decorativeWorldX(int index){
    return 80+index*176;
}
unsigned decorFrame(int index,uint32_t tick){
    return (index%2==0) ? unsigned((tick/24u+unsigned(index/2))%2u) :
                          2u+unsigned((tick/9u+unsigned(index/2))%2u);
}
bool drawDecorLayer(uint32_t* target,int width,int height,int stride,
                    const SpriteAtlas& atlas,int camera_px,uint32_t tick,
                    bool foreground){
    const int scale=decorScale(atlas);
    if(!target||width<=0||height<=0||stride<width||scale<0)return false;
    // Purely visual positions, independent of any collision or game logic.
    // All geometry is synthetic and deterministic. Draw at most 12 props.
    for(int i=0;i<12;++i){
        if(bool(i%2)!=foreground)continue;
        int64_t sx=(int64_t(decorativeWorldX(i))-camera_px)*2;
        if(sx < -48 || sx >= width || sx < std::numeric_limits<int>::min() ||
           sx > std::numeric_limits<int>::max())continue;
        const int sy=foreground ? 366 : 306;
        if(!blitAtlasFrame(target,width,height,stride,atlas,
                           decorFrame(i,tick),int(sx),sy,scale))
            return false;
    }
    return true;
}
bool drawPlacedDecorLayer(uint32_t* target,int width,int height,int stride,
                          const SpriteAtlas& atlas,DecorLayout layout,
                          int camera_px,uint32_t tick,bool foreground){
    const int scale=decorScale(atlas);
    if(!target||width<=0||height<=0||stride<width||scale<0||
       !validDecorLayout(layout,atlas.frame_count))return false;
    for(unsigned i=0;i<layout.count;++i){
        const DecorPlacement& p=layout.placements[i];
        if(bool(p.layer)!=foreground)continue;
        const int64_t sx=(int64_t(p.world_x)-camera_px)*2;
        const int64_t sy=(int64_t(p.world_y)+80)*2;
        if(sx<=-48||sx>=width||sy<=-64||sy>=height)continue;
        if(sx<std::numeric_limits<int>::min()||
           sx>std::numeric_limits<int>::max()||
           sy<std::numeric_limits<int>::min()||
           sy>std::numeric_limits<int>::max())continue;
        if(!blitAtlasFrame(target,width,height,stride,atlas,
                           placedDecorFrame(p,tick),int(sx),int(sy),scale))
            return false;
    }
    return true;
}
bool DecorSource::initialize(const uint8_t* bytes,size_t size){
    embedded_=nullptr;embedded_size_=0;
    SpriteAtlas a{};
    if(!openAtlas(a,bytes,size)||decorScale(a)<0||
       !source_.initialize(bytes,size,4))return false;
    embedded_=bytes;embedded_size_=size;
    return true;
}
DecorReload DecorSource::reload(const char* path){
    if(!embedded_)return DecorReload::Uninitialized;
    AssetSource candidate;
    if(!candidate.initialize(embedded_,embedded_size_,4))
        return DecorReload::Uninitialized;
    const auto status=candidate.reloadFromFile(path);
    if(status==AtlasLoadResult::FileMissing)return DecorReload::Missing;
    if(status!=AtlasLoadResult::Loaded)return DecorReload::Invalid;
    if(decorScale(candidate.atlas())<0)return DecorReload::UnsupportedGeometry;
    if(!source_.swapLoaded(candidate))return DecorReload::Invalid;
    return DecorReload::Loaded;
}
}
