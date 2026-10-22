#pragma once
#include "driving_road_reference.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>

// Optional private *numeric-only* source screenshot observations.
// Never contains ROM, FM2 input, CHR tiles, captured image pixels,
// source CPU traces, collision coordinates or effective PPU scroll.
// No interpolation or guessed camera velocity.
namespace vpd::private_road {
constexpr std::size_t kSamples=37;
constexpr std::size_t kHeaderBytes=16;
constexpr std::size_t kRecordBytes=4;
constexpr std::size_t kBundleBytes=kHeaderBytes+kSamples*kRecordBytes;
constexpr std::uint8_t kMagic[8]={'V','P','D','R','O','A','D','1'};

inline std::uint32_t crc32(const std::uint8_t* bytes,
                            std::size_t length) noexcept {
    std::uint32_t crc=0xffffffffu;
    for(std::size_t i=0;i<length;++i) {
        crc^=bytes[i];
        for(unsigned bit=0;bit<8;++bit)
            crc=(crc>>1)^((crc&1u)?0xedb88320u:0u);
    }
    return ~crc;
}
inline std::uint16_t u16(const std::uint8_t* p) noexcept {
    return static_cast<std::uint16_t>(p[0]) |
           static_cast<std::uint16_t>(p[1])<<8;
}
inline std::uint32_t u32(const std::uint8_t* p) noexcept {
    return static_cast<std::uint32_t>(p[0]) |
           static_cast<std::uint32_t>(p[1])<<8 |
           static_cast<std::uint32_t>(p[2])<<16 |
           static_cast<std::uint32_t>(p[3])<<24;
}
constexpr bool rejectedFrame(std::uint16_t frame) noexcept {
    return frame==712 || frame==720 || frame==728 || frame==736;
}

class PrivateRoadBundle {
public:
    bool loaded() const noexcept {return loaded_;}
    std::size_t count() const noexcept {return loaded_?kSamples:0;}
    void clear() noexcept {
        loaded_=false;
        records_={};
    }
    const road_reference::CrossSection* byIndex(std::size_t index) const noexcept {
        return loaded_ && index<kSamples ? &records_[index]:nullptr;
    }
    const road_reference::CrossSection* atExactFrame(
        std::uint32_t frame) const noexcept {
        if(!loaded_)return nullptr;
        for(const auto& s:records_)if(s.frame==frame)return &s;
        return nullptr;
    }
    bool loadBytes(const std::uint8_t* data,std::size_t size) noexcept {
        clear(); // malformed/reused source must never leave stale geometry
        if(!data || size!=kBundleBytes)return false;
        for(std::size_t i=0;i<8;++i)
            if(data[i]!=kMagic[i])return false;
        if(u16(data+8)!=1 || u16(data+10)!=kSamples ||
           u32(data+12)!=crc32(data+kHeaderBytes,size-kHeaderBytes))
            return false;
        std::array<road_reference::CrossSection,kSamples> temp{};
        std::size_t accepted=0;
        for(std::uint16_t frame=600;frame<=920;frame+=8) {
            if(rejectedFrame(frame))continue;
            if(accepted>=kSamples)return false;
            const auto offset=kHeaderBytes+accepted*kRecordBytes;
            road_reference::CrossSection s{
                u16(data+offset),data[offset+2],data[offset+3]};
            if(s.frame!=frame || s.left>s.right || s.right>=255 ||
               s.width()<30 || s.width()>200)return false;
            if(const auto* known=road_reference::atExactFrame(frame))
                if(known->left!=s.left || known->right!=s.right)
                    return false;
            temp[accepted++]=s;
        }
        if(accepted!=kSamples)return false;
        records_=temp;
        loaded_=true;
        return true;
    }
    bool loadFile(const char* path) noexcept {
        clear();
        if(!path)return false;
        auto* file=std::fopen(path,"rb");
        if(!file)return false;
        std::array<std::uint8_t,kBundleBytes> bytes{};
        const auto read=std::fread(bytes.data(),1,bytes.size(),file);
        const int trailing=std::fgetc(file);
        const bool closed=std::fclose(file)==0;
        return closed && read==bytes.size() && trailing==EOF &&
               loadBytes(bytes.data(),bytes.size());
    }
private:
    bool loaded_=false;
    std::array<road_reference::CrossSection,kSamples> records_{};
};
} // namespace vpd::private_road
