#include "backdrop_source.hpp"
#include <cstdint>

namespace vpd {
int backdropScale(const SpriteAtlas& a){
    if(!a.pixels||a.frame_count!=2||!a.frame_width||!a.frame_height||
       512%a.frame_width||384%a.frame_height)return -1;
    const int scale=512/a.frame_width;
    return scale>=1&&scale<=8&&a.frame_height*scale==384?scale:-1;
}
int parallaxOffset(int camera_pixels,int divisor,int span_pixels) {
    if(divisor<=0||span_pixels<=0)return -1;
    // Integer division is floor, including negative camera positions.
    int q=camera_pixels/divisor;
    if(camera_pixels%divisor<0)--q;
    int remainder=q%span_pixels;
    if(remainder<0)remainder+=span_pixels;
    return remainder;
}
bool drawBackdropLayers(uint32_t* target,int width,int height,int stride,
                        const SpriteAtlas& atlas,int camera_pixels){
    const int scale=backdropScale(atlas);
    if(!target||width<=0||height<=0||stride<width||scale<0)return false;
    // Behind the player's terrain, near layer moves 2.5x faster than far.
    // Position is local to the scene buffer and not a real NES raster trace.
    for(unsigned layer=0;layer<2;++layer) {
        int divisor=layer==0?5:2;
        int offset=parallaxOffset(camera_pixels,divisor,512);
        int y=layer==0?165:265;
        // Start one full tile left so negative offsets and seams are covered.
        for(int x=-offset-512;x<width;x+=512){
            if(!blitAtlasFrame(target,width,height,stride,atlas,layer,
                               x,y,scale))return false;
        }
    }
    return true;
}
bool BackdropSource::initialize(const uint8_t* bytes,size_t size){
    embedded_=nullptr;
    embedded_size_=0;
    SpriteAtlas atlas{};
    if(!openAtlas(atlas,bytes,size)||backdropScale(atlas)<0||
       !source_.initialize(bytes,size,2))return false;
    embedded_=bytes;
    embedded_size_=size;
    return true;
}
BackdropReload BackdropSource::reload(const char* path){
    if(!embedded_)return BackdropReload::Uninitialized;
    AssetSource candidate;
    if(!candidate.initialize(embedded_,embedded_size_,2))
        return BackdropReload::Uninitialized;
    const AtlasLoadResult status=candidate.reloadFromFile(path);
    if(status==AtlasLoadResult::FileMissing)return BackdropReload::Missing;
    if(status!=AtlasLoadResult::Loaded)return BackdropReload::Invalid;
    if(backdropScale(candidate.atlas())<0)
        return BackdropReload::UnsupportedGeometry;
    if(!source_.swapLoaded(candidate))return BackdropReload::Invalid;
    return BackdropReload::Loaded;
}
}
