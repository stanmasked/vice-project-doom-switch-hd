#include "asset_source.hpp"
#include "asset_atlas.hpp"
#include "demo_atlas.hpp"
#include <cstdio>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>
#define CHECK(condition) do { if(!(condition))throw std::runtime_error(#condition); } while(0)

namespace {
struct LocalFile {
    std::string name="vpd_generated_test_asset_source.vpat";
    ~LocalFile(){std::remove(name.c_str());}
    void write(const std::vector<uint8_t>& data)const{
        auto* f=std::fopen(name.c_str(),"wb");
        CHECK(f);
        CHECK(std::fwrite(data.data(),1,data.size(),f)==data.size());
        CHECK(std::fclose(f)==0);
    }
    void oversize()const{
        auto* f=std::fopen(name.c_str(),"wb");
        CHECK(f);
        CHECK(std::fseek(f,static_cast<long>(vpd::kMaxExternalAtlasBytes),SEEK_SET)==0);
        CHECK(std::fputc(0x42,f)!=EOF);
        CHECK(std::fclose(f)==0);
    }
};
uint32_t crc(const uint8_t* bytes,size_t n){
    uint32_t v=~uint32_t(0);
    for(size_t i=0;i<n;++i){
        v^=bytes[i];
        for(int b=0;b<8;++b)v=(v>>1)^((v&1u)?0xedb88320u:0u);
    }
    return ~v;
}
void patchCrc(std::vector<uint8_t>& bytes){
    uint32_t v=crc(bytes.data()+vpd::kVpatHeaderBytes,
                   bytes.size()-vpd::kVpatHeaderBytes);
    for(int k=0;k<4;++k)bytes[18+k]=static_cast<uint8_t>(v>>(8*k));
}
uint64_t fingerprint(const vpd::SpriteAtlas& a){
    uint32_t buffer[80*90];
    for(auto& x:buffer)x=0xff0c0d0eu;
    CHECK(vpd::blitAtlasFrame(buffer,80,90,80,a,0,4,7,2));
    uint64_t v=14695981039346656037ull;
    for(uint32_t p:buffer){
        for(int k=0;k<4;++k){v^=(p>>(8*k))&255u;v*=1099511628211ull;}
    }
    return v;
}
}

int main(){
    LocalFile path;
    vpd::AssetSource active;
    CHECK(active.reloadFromFile(path.name.c_str())==vpd::AtlasLoadResult::NotInitialized);
    CHECK(!active.initialize(nullptr,0,4));
    CHECK(active.initialize(vpd_demo::kAtlasBlob,vpd_demo::kAtlasBytes,4));
    const auto embedded=active.atlas().pixels;
    CHECK(embedded==vpd_demo::kAtlasBlob+vpd::kVpatHeaderBytes);
    CHECK(active.expectedFrameCount()==4);
    const auto original=fingerprint(active.atlas());
    CHECK(active.reloadFromFile("file_that_does_not_exist.vpat")==
          vpd::AtlasLoadResult::FileMissing);
    CHECK(!active.external()&&active.atlas().pixels==embedded);

    std::vector<uint8_t> alternative(vpd_demo::kAtlasBlob,
                                       vpd_demo::kAtlasBlob+vpd_demo::kAtlasBytes);
    // Mutate the first visible RGBA red channel, then recalculate correct CRC.
    bool changed=false;
    // First visible texel of *frame zero*, not the earliest pixel in
    // the whole 4-frame sheet (which could belong to the jump pose).
    for(size_t y=0;y<32 && !changed;++y){
        for(size_t x=0;x<24;++x){
            const size_t n=vpd::kVpatHeaderBytes+(y*96+x)*4;
            if(alternative[n+3]>0){
                alternative[n]^=0x33u;
                changed=true;
                break;
            }
        }
    }
    CHECK(changed);
    patchCrc(alternative);
    path.write(alternative);
    CHECK(active.reloadFromFile(path.name.c_str())==vpd::AtlasLoadResult::Loaded);
    CHECK(active.external() && active.atlas().pixels!=embedded);
    const auto good_external=active.atlas().pixels;
    const auto external_image=fingerprint(active.atlas());
    CHECK(external_image!=original);

    auto invalid=alternative;
    invalid.back()^=1;
    path.write(invalid);
    CHECK(active.reloadFromFile(path.name.c_str())==vpd::AtlasLoadResult::InvalidAtlas);
    CHECK(active.external() && active.atlas().pixels==good_external);
    CHECK(fingerprint(active.atlas())==external_image);

    invalid=alternative;
    invalid[14]=3;invalid[15]=0; // header-only frame count change; CRC still valid
    path.write(invalid);
    CHECK(active.reloadFromFile(path.name.c_str())==vpd::AtlasLoadResult::WrongFrameCount);
    CHECK(active.external() && active.atlas().pixels==good_external);

    invalid=alternative;
    invalid.pop_back(); // truncated
    path.write(invalid);
    CHECK(active.reloadFromFile(path.name.c_str())==vpd::AtlasLoadResult::InvalidAtlas);
    CHECK(active.atlas().pixels==good_external);

    path.oversize();
    CHECK(active.reloadFromFile(path.name.c_str())==vpd::AtlasLoadResult::TooLarge);
    CHECK(active.atlas().pixels==good_external);

    active.resetToEmbedded();
    CHECK(!active.external()&&active.atlas().pixels==embedded);
    CHECK(fingerprint(active.atlas())==original);
    CHECK(active.reloadFromFile("")==vpd::AtlasLoadResult::FileMissing);
    CHECK(!active.initialize(vpd_demo::kAtlasBlob,vpd_demo::kAtlasBytes,3));
    CHECK(active.atlas().pixels==nullptr);
    puts("PASS: bounded SD asset staging, CRC, frame contract and rollback");
}
