#include "animation_resource.hpp"
#include <array>
#include <cstdio>
#include <utility>
#include <cerrno>

namespace vpd {
namespace {
uint16_t u16(const uint8_t* p) { return uint16_t(p[0])|(uint16_t(p[1])<<8); }
uint32_t u32(const uint8_t* p) {
    return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|
           (uint32_t(p[3])<<24);
}
uint32_t crc32(const uint8_t* p,size_t n) {
    uint32_t crc=~uint32_t(0);
    for(size_t i=0;i<n;++i){
        crc^=p[i];
        for(int bit=0;bit<8;++bit)
            crc=(crc>>1)^((crc&1u)?0xedb88320u:0);
    }
    return ~crc;
}
}
bool AnimationResource::initialize(const AnimationBank& embedded) {
    embedded_=nullptr;
    external_=false;
    runtime_={};
    if(!validAnimationBank(embedded))return false;
    embedded_=&embedded;
    return true;
}
void AnimationResource::rebuildPointers(){
    unsigned offset=0;
    for(unsigned state=0;state<4;++state){
        runtime_.clips[state]={
            frames_.data()+offset,counts_[state],loops_[state]!=0
        };
        offset+=counts_[state];
    }
}
AnimationLoadResult AnimationResource::loadBytes(
        const uint8_t* bytes,size_t size,uint16_t atlas_frames,
        uint32_t atlas_pixel_crc32) {
    if(!embedded_)return AnimationLoadResult::Uninitialized;
    if(!bytes || size<34 || size>kMaxAnimationFileBytes)
        return AnimationLoadResult::Invalid;
    if(bytes[0]!='V'||bytes[1]!='A'||bytes[2]!='N'||bytes[3]!='M'||
       u16(bytes+8)!=4 || u16(bytes+12)!=0)
        return AnimationLoadResult::Invalid;
    const unsigned version=u16(bytes+4);
    if(version!=1 && version!=2)return AnimationLoadResult::Invalid;
    const unsigned frame_count=u16(bytes+6);
    const unsigned total=u16(bytes+10);
    const size_t descriptors=version==2?22u:18u;
    if(frame_count==0||frame_count>4096||total<4||total>kMaxAnimationFrames||
       size!=descriptors+16u+size_t(total)*4 ||
       u32(bytes+14)!=crc32(bytes+18,size-18))
        return AnimationLoadResult::Invalid;
    if(frame_count!=atlas_frames)
        return AnimationLoadResult::AtlasMismatch;
    // v2 binds timing to the VPAT pixel payload; v1 remains unbound/legacy.
    if(version==2 && u32(bytes+18)!=atlas_pixel_crc32)
        return AnimationLoadResult::AtlasIdentityMismatch;
    std::array<AnimationFrame,kMaxAnimationFrames> staged{};
    std::array<uint8_t,4> counts{};
    std::array<uint8_t,4> loops{};
    unsigned used=0;
    for(unsigned state=0;state<4;++state){
        unsigned start=u16(bytes+descriptors+state*4);
        unsigned n=bytes[descriptors+2+state*4];
        unsigned flags=bytes[descriptors+3+state*4];
        if(!n||n>64||flags>1||start!=used||used+n>total)
            return AnimationLoadResult::Invalid;
        counts[state]=static_cast<uint8_t>(n);
        loops[state]=static_cast<uint8_t>(flags);
        used+=n;
    }
    if(used!=total)return AnimationLoadResult::Invalid;
    for(unsigned index=0;index<total;++index){
        const uint8_t* p=bytes+descriptors+16+index*4;
        const unsigned frame=u16(p),ticks=u16(p+2);
        if(frame>=frame_count||ticks==0||ticks>600)
            return AnimationLoadResult::Invalid;
        staged[index]={static_cast<uint16_t>(frame),
                       static_cast<uint16_t>(ticks)};
    }
    // The entire file is validated before changing the active bank.
    frames_=staged;
    counts_=counts;
    loops_=loops;
    runtime_.atlas_frame_count=static_cast<uint16_t>(frame_count);
    rebuildPointers();
    external_=true;
    return AnimationLoadResult::Loaded;
}
AnimationLoadResult AnimationResource::loadFile(
        const char* path,uint16_t atlas_frames,uint32_t atlas_pixel_crc32) {
    if(!embedded_)return AnimationLoadResult::Uninitialized;
    if(!path||!*path)return AnimationLoadResult::Missing;
    std::FILE* file=std::fopen(path,"rb");
    if(!file)return errno==ENOENT?AnimationLoadResult::Missing:
                              AnimationLoadResult::IoError;
    if(std::fseek(file,0,SEEK_END)!=0){
        std::fclose(file);return AnimationLoadResult::IoError;
    }
    const long length=std::ftell(file);
    if(length<0){
        std::fclose(file);return AnimationLoadResult::IoError;
    }
    if(length>static_cast<long>(kMaxAnimationFileBytes)){
        std::fclose(file);return AnimationLoadResult::Invalid;
    }
    if(std::fseek(file,0,SEEK_SET)!=0){
        std::fclose(file);return AnimationLoadResult::IoError;
    }
    std::array<uint8_t,kMaxAnimationFileBytes> data{};
    const size_t got=std::fread(data.data(),1,static_cast<size_t>(length),file);
    const bool broken=got!=static_cast<size_t>(length)||std::ferror(file)!=0;
    const int extra=broken?EOF:std::fgetc(file);
    std::fclose(file);
    if(broken||extra!=EOF)return AnimationLoadResult::IoError;
    return loadBytes(data.data(),got,atlas_frames,atlas_pixel_crc32);
}
void AnimationResource::reset(){
    external_=false;
}
void AnimationResource::swapExternal(AnimationResource& other){
    // Both participants must be initialized to the same embedded bank.
    if(!embedded_||embedded_!=other.embedded_)return;
    frames_.swap(other.frames_);
    counts_.swap(other.counts_);
    loops_.swap(other.loops_);
    std::swap(runtime_.atlas_frame_count,other.runtime_.atlas_frame_count);
    std::swap(external_,other.external_);
    rebuildPointers();
    other.rebuildPointers();
}
}
