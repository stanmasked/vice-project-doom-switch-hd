#include "decor_layout.hpp"
#include <cstdio>
#include <cerrno>

namespace vpd {
namespace {
uint16_t u16(const uint8_t* p){
    return uint16_t(p[0])|(uint16_t(p[1])<<8);
}
int16_t i16(const uint8_t* p){
    const uint16_t u=u16(p);
    return int16_t(u<=0x7fffu ? int(u) : int(u)-65536);
}
uint32_t u32(const uint8_t* p){
    return uint32_t(p[0])|(uint32_t(p[1])<<8)|
           (uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);
}
uint32_t crc32(const uint8_t* bytes,size_t size){
    uint32_t crc=~uint32_t(0);
    for(size_t i=0;i<size;++i){
        crc^=bytes[i];
        for(int k=0;k<8;++k)
            crc=(crc>>1)^((crc&1u)?0xedb88320u:0u);
    }
    return ~crc;
}
}
bool validDecorPlacement(const DecorPlacement& p,uint16_t atlas_frames){
    return atlas_frames>0 &&
           p.world_x>=-16384 && p.world_x<=16384 &&
           p.world_y>=-1024 && p.world_y<=1024 &&
           p.kind<=1 && p.layer<=1 &&
           p.frame_count>0 && p.first_frame<atlas_frames &&
           unsigned(p.first_frame)+p.frame_count<=atlas_frames &&
           p.period_ticks>=1 && p.period_ticks<=600;
}
bool validDecorLayout(DecorLayout layout,uint16_t frames){
    if(layout.count>kDecorMaxObjects ||
       (layout.count>0 && !layout.placements))return false;
    for(unsigned i=0;i<layout.count;++i)
        if(!validDecorPlacement(layout.placements[i],frames))return false;
    return true;
}
unsigned placedDecorFrame(const DecorPlacement& p,uint32_t tick){
    if(!p.frame_count||!p.period_ticks)return unsigned(p.first_frame);
    return unsigned(p.first_frame)+(tick/p.period_ticks+p.phase_frames)%p.frame_count;
}
bool DecorLayoutSource::initialize(DecorLayout embedded){
    embedded_={};
    external_=false;
    count_=0;
    if(!embedded.placements || embedded.count==0 ||
       !validDecorLayout(embedded))return false;
    embedded_=embedded;
    return true;
}
LayoutLoadResult DecorLayoutSource::loadBytes(const uint8_t* bytes,size_t size){
    if(!embedded_.placements && !embedded_.count)
        return LayoutLoadResult::Uninitialized;
    if(!bytes||size<kDecorLayoutHeaderSize||size>kDecorLayoutMaxBytes||
       bytes[0]!='V'||bytes[1]!='L'||bytes[2]!='A'||bytes[3]!='Y'||
       u16(bytes+4)!=1||u16(bytes+8)!=12||u16(bytes+10)!=0)
        return LayoutLoadResult::Invalid;
    const unsigned count=u16(bytes+6);
    if(count>kDecorMaxObjects||size!=16u+12u*count||
       crc32(bytes+16,size-16)!=u32(bytes+12))
        return LayoutLoadResult::Invalid;
    std::array<DecorPlacement,kDecorMaxObjects> staged{};
    for(unsigned i=0;i<count;++i){
        const uint8_t* p=bytes+16+12*i;
        DecorPlacement obj{
            i16(p),i16(p+2),p[4],p[5],p[6],p[7],
            u16(p+8),u16(p+10)
        };
        if(!validDecorPlacement(obj))return LayoutLoadResult::Invalid;
        staged[i]=obj;
    }
    placements_=staged;
    count_=static_cast<uint16_t>(count);
    external_=true;
    return LayoutLoadResult::Loaded;
}
LayoutLoadResult DecorLayoutSource::reload(const char* path){
    if(!embedded_.placements&&!embedded_.count)
        return LayoutLoadResult::Uninitialized;
    if(!path||!*path)return LayoutLoadResult::Missing;
    std::FILE* f=std::fopen(path,"rb");
    if(!f)return errno==ENOENT?LayoutLoadResult::Missing:
                             LayoutLoadResult::IoError;
    if(std::fseek(f,0,SEEK_END)!=0){std::fclose(f);return LayoutLoadResult::IoError;}
    const long len=std::ftell(f);
    if(len<0){std::fclose(f);return LayoutLoadResult::IoError;}
    if(len>static_cast<long>(kDecorLayoutMaxBytes)){
        std::fclose(f);return LayoutLoadResult::Invalid;
    }
    if(std::fseek(f,0,SEEK_SET)!=0){
        std::fclose(f);return LayoutLoadResult::IoError;
    }
    std::array<uint8_t,kDecorLayoutMaxBytes> data{};
    const size_t read=std::fread(data.data(),1,static_cast<size_t>(len),f);
    const bool failed=read!=static_cast<size_t>(len)||std::ferror(f)!=0;
    const int extra=failed?EOF:std::fgetc(f);
    std::fclose(f);
    if(failed||extra!=EOF)return LayoutLoadResult::IoError;
    return loadBytes(data.data(),read);
}
}
