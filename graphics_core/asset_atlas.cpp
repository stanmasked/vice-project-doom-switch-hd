#include "asset_atlas.hpp"
#include <cstdint>
#include <cstddef>
namespace vpd {
namespace {
uint16_t u16le(const uint8_t* p){return static_cast<uint16_t>(p[0]|(p[1]<<8));}
uint32_t u32le(const uint8_t* p){return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);}
uint32_t crc32(const uint8_t* p,size_t n){
    uint32_t crc=~uint32_t(0);
    for(size_t i=0;i<n;++i){
        crc^=p[i];
        for(int b=0;b<8;++b)crc=(crc>>1) ^ ((crc&1u)?0xedb88320u:0u);
    }
    return ~crc;
}
}
bool openAtlas(SpriteAtlas& out,const uint8_t* bytes,size_t size){
    out={};
    if(!bytes || size<kVpatHeaderBytes)return false;
    if(bytes[0]!='V'||bytes[1]!='P'||bytes[2]!='A'||bytes[3]!='T')return false;
    if(u16le(bytes+4)!=1 || u16le(bytes+16)!=0)return false;
    const unsigned w=u16le(bytes+6),h=u16le(bytes+8);
    const unsigned fw=u16le(bytes+10),fh=u16le(bytes+12);
    const unsigned count=u16le(bytes+14);
    if(w==0||h==0||w>1024||h>1024||fw==0||fh==0||
       fw>w||fh>h||w%fw||h%fh||count==0||
       count>(w/fw)*(h/fh))return false;
    size_t pixels=size_t(w)*h*4;
    if(size!=kVpatHeaderBytes+pixels)return false;
    if(u32le(bytes+18)!=crc32(bytes+kVpatHeaderBytes,pixels))return false;
    out={bytes+kVpatHeaderBytes,static_cast<uint16_t>(w),static_cast<uint16_t>(h),
         static_cast<uint16_t>(fw),static_cast<uint16_t>(fh),static_cast<uint16_t>(count)};
    return true;
}
bool blitAtlasFrame(uint32_t* target,int width,int height,int stride,
                    const SpriteAtlas& a,unsigned frame,int x,int y,int scale,bool flip_x){
    if(!target||width<=0||height<=0||stride<width||!a.pixels||
       !a.width||!a.height||!a.frame_width||!a.frame_height||
       a.frame_width>a.width||a.frame_height>a.height||
       a.width%a.frame_width||a.height%a.frame_height||
       frame>=a.frame_count||scale<1||scale>8)return false;
    unsigned columns=a.width/a.frame_width;
    if(frame/columns>=a.height/a.frame_height)return false;
    int64_t rx0=x,ry0=y;
    int64_t rx1=rx0+int64_t(a.frame_width)*scale;
    int64_t ry1=ry0+int64_t(a.frame_height)*scale;
    int sx0=static_cast<int>(rx0>0?rx0:0),sy0=static_cast<int>(ry0>0?ry0:0);
    int sx1=static_cast<int>(rx1<width?rx1:width),sy1=static_cast<int>(ry1<height?ry1:height);
    if(sx0>=sx1||sy0>=sy1)return true;
    const unsigned tile_x=(frame%columns)*a.frame_width;
    const unsigned tile_y=(frame/columns)*a.frame_height;
    for(int py=sy0;py<sy1;++py){
        int from_y=tile_y+static_cast<int>((int64_t(py)-ry0)/scale);
        for(int px=sx0;px<sx1;++px){
            int local_x=static_cast<int>((int64_t(px)-rx0)/scale);
            int from_x=tile_x+(flip_x?int(a.frame_width)-1-local_x:local_x);
            size_t i=(size_t(from_y)*a.width+from_x)*4;
            unsigned alpha=a.pixels[i+3];
            if(alpha==0)continue;
            uint32_t src=uint32_t(a.pixels[i])|
                          (uint32_t(a.pixels[i+1])<<8)|
                          (uint32_t(a.pixels[i+2])<<16)|0xff000000u;
            uint32_t& dest=target[size_t(py)*stride+px];
            if(alpha==255){dest=src;continue;}
            unsigned inv=255-alpha;
            uint32_t mixed=0xff000000u;
            for(unsigned channel=0;channel<3;++channel){
                unsigned offset=channel*8;
                unsigned blended=(((src>>offset)&255u)*alpha +
                                  ((dest>>offset)&255u)*inv+127u)/255u;
                mixed|=blended<<offset;
            }
            dest=mixed;
        }
    }
    return true;
}
}
