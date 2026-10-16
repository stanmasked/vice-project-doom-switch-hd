#include "asset_bundle.hpp"
#include "animation_resource.hpp"
#include "demo_atlas.hpp"
#include "demo_animation.hpp"
#include <cstdio>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>
#define CHECK(x) do{if(!(x))throw std::runtime_error(#x);}while(0)

namespace {
std::vector<uint8_t> load(const char* path) {
    FILE* f=std::fopen(path,"rb");
    CHECK(f);
    CHECK(std::fseek(f,0,SEEK_END)==0);
    long size=std::ftell(f);
    CHECK(size>=0 && size<=4096);
    CHECK(std::fseek(f,0,SEEK_SET)==0);
    std::vector<uint8_t> b(size_t(size),0);
    CHECK(std::fread(b.data(),1,b.size(),f)==b.size());
    CHECK(std::fclose(f)==0);
    return b;
}
void write(const char* path,const std::vector<uint8_t>& bytes) {
    FILE* f=std::fopen(path,"wb");CHECK(f);
    CHECK(std::fwrite(bytes.data(),1,bytes.size(),f)==bytes.size());
    CHECK(std::fclose(f)==0);
}
uint32_t crc32(const uint8_t* p,size_t n){
    uint32_t x=~uint32_t(0);
    for(size_t i=0;i<n;++i){
        x^=p[i];
        for(int bit=0;bit<8;++bit)x=(x>>1)^((x&1)?0xedb88320u:0);
    }
    return ~x;
}
void patchAnimationCrc(std::vector<uint8_t>& b){
    uint32_t x=crc32(b.data()+18,b.size()-18);
    for(int k=0;k<4;++k)b[14+k]=uint8_t(x>>(k*8));
}
struct TempFiles {
    std::string atlas="vpd_test_pair.vpat";
    std::string anim="vpd_test_pair.vanm";
    ~TempFiles(){std::remove(atlas.c_str());std::remove(anim.c_str());}
};
}
int main(int argc,char** argv) {
    CHECK(argc==3);
    const std::vector<uint8_t> binary=load(argv[1]);
    const std::vector<uint8_t> bound=load(argv[2]);
    const std::vector<uint8_t> embedded(vpd_demo::kAtlasBlob,
             vpd_demo::kAtlasBlob+vpd_demo::kAtlasBytes);
    TempFiles files;
    write(files.atlas.c_str(),embedded);
    write(files.anim.c_str(),binary);

    vpd::AnimationResource individual;
    CHECK(individual.initialize(vpd_demo::kAnimationBank));
    CHECK(individual.loadBytes(binary.data(),binary.size(),4)==
          vpd::AnimationLoadResult::Loaded);
    CHECK(individual.external());
    CHECK(vpd::validAnimationBank(individual.bank()));
    CHECK(individual.bank().clips[1].frames[0].ticks==6);
    auto changed=binary;
    changed[40]=2; // run A duration 6 -> 2
    patchAnimationCrc(changed);
    CHECK(individual.loadBytes(changed.data(),changed.size(),4)==
          vpd::AnimationLoadResult::Loaded);
    CHECK(individual.bank().clips[1].frames[0].ticks==2);
    changed.back()^=1;
    CHECK(individual.loadBytes(changed.data(),changed.size(),4)==
          vpd::AnimationLoadResult::Invalid);
    CHECK(individual.bank().clips[1].frames[0].ticks==2);
    CHECK(individual.loadBytes(binary.data(),binary.size(),3)==
          vpd::AnimationLoadResult::AtlasMismatch);
    individual.reset();
    CHECK(!individual.external());
    CHECK(individual.bank().clips[1].frames[0].ticks==6);

    vpd::AssetBundle game;
    CHECK(game.initialize(vpd_demo::kAtlasBlob,vpd_demo::kAtlasBytes,
                           vpd_demo::kAnimationBank));
    CHECK(!game.externalAtlas()&&!game.externalAnimation());
    CHECK(game.reload(files.atlas.c_str(),files.anim.c_str())==
          vpd::BundleReload::LoadedPair);
    CHECK(game.externalAtlas()&&game.externalAnimation());
    const auto* before=game.atlas().pixels;
    CHECK(game.animation().clips[1].frames[0].ticks==6);
    write(files.anim.c_str(),changed); // broken CRC; any good atlas MUST roll back
    CHECK(game.reload(files.atlas.c_str(),files.anim.c_str())==
          vpd::BundleReload::BadAnimation);
    CHECK(game.atlas().pixels==before && game.externalAnimation());
    CHECK(game.animation().clips[1].frames[0].ticks==6);
    write(files.anim.c_str(),binary);
    auto mismatch=binary;
    mismatch[6]=3; // declared atlas-frame-count != actual
    patchAnimationCrc(mismatch);
    write(files.anim.c_str(),mismatch);
    CHECK(game.reload(files.atlas.c_str(),files.anim.c_str())==
          vpd::BundleReload::BadAnimation);
    CHECK(game.atlas().pixels==before);
    write(files.anim.c_str(),binary);
    // Texture corruption must NOT replace animation on a two-file reload.
    auto bad_tex=embedded;bad_tex.back()^=1;
    write(files.atlas.c_str(),bad_tex);
    CHECK(game.reload(files.atlas.c_str(),files.anim.c_str())==
          vpd::BundleReload::BadAtlas);
    CHECK(game.animation().clips[1].frames[0].ticks==6);
    CHECK(game.atlas().pixels==before);
    write(files.atlas.c_str(),embedded);

    std::remove(files.anim.c_str());
    CHECK(game.reload(files.atlas.c_str(),files.anim.c_str())==
          vpd::BundleReload::LoadedAtlasOnly);
    CHECK(game.externalAtlas()&&!game.externalAnimation()); // stage-25 compatibility
    CHECK(game.animation().clips[1].frames[0].ticks==6);
    const auto* legacy=game.atlas().pixels;
    CHECK(game.reload("missing_vpd_bundle_atlas.vpat",files.anim.c_str())==
          vpd::BundleReload::MissingAtlas);
    CHECK(game.atlas().pixels==legacy);
    // VANM v2: same frame count is insufficient: CRC must identify this
    // actual VPAT pixel payload. Legacy VANM v1 intentionally remains usable.
    CHECK(bound.size()==binary.size()+4);
    CHECK(bound[4]==2 && bound[5]==0);
    CHECK(individual.loadBytes(bound.data(),bound.size(),4,
               game.atlas().pixel_crc32)==vpd::AnimationLoadResult::Loaded);
    CHECK(individual.loadBytes(bound.data(),bound.size(),4,
               game.atlas().pixel_crc32^1u)==
               vpd::AnimationLoadResult::AtlasIdentityMismatch);
    write(files.anim.c_str(),bound);
    CHECK(game.reload(files.atlas.c_str(),files.anim.c_str())==
          vpd::BundleReload::LoadedPair);
    const auto* good_bound_pixels=game.atlas().pixels;
    CHECK(game.animation().clips[1].frames[0].ticks==6);
    auto different_vpat=embedded;
    const size_t pos=vpd::kVpatHeaderBytes+(7u*96u+12u)*4u;
    different_vpat[pos]^=0x3fu;
    uint32_t texture_crc=crc32(different_vpat.data()+vpd::kVpatHeaderBytes,
                                different_vpat.size()-vpd::kVpatHeaderBytes);
    for(int k=0;k<4;++k)different_vpat[18+k]=uint8_t(texture_crc>>(8*k));
    write(files.atlas.c_str(),different_vpat);
    CHECK(game.reload(files.atlas.c_str(),files.anim.c_str())==
          vpd::BundleReload::BadAnimation);
    CHECK(game.atlas().pixels==good_bound_pixels);
    CHECK(game.animation().clips[1].frames[0].ticks==6);
    write(files.atlas.c_str(),embedded);
    CHECK(game.reload(files.atlas.c_str(),files.anim.c_str())==
          vpd::BundleReload::LoadedPair);
    game.reset();
    CHECK(!game.externalAtlas()&&!game.externalAnimation());
    CHECK(game.atlas().pixels==vpd_demo::kAtlasBlob+vpd::kVpatHeaderBytes);
    puts("PASS: VANM v1/v2, atlas CRC identity, durations, rollback, legacy fallback");
    return 0;
}
