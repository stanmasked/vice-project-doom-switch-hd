#include "backdrop_source.hpp"
#include "scene_renderer.hpp"
#include "demo_backdrop.hpp"
#include <cstdio>
#include <cstdint>
#include <stdexcept>
#include <string>
#include <vector>
#define CHECK(x) do { if(!(x))throw std::runtime_error(#x); } while(0)

namespace {
struct Temp {
    std::string path="vpd_synthetic_backdrop.vpat";
    ~Temp(){std::remove(path.c_str());}
    void write(const std::vector<uint8_t>& raw)const{
        FILE* f=std::fopen(path.c_str(),"wb");CHECK(f);
        CHECK(std::fwrite(raw.data(),1,raw.size(),f)==raw.size());
        CHECK(std::fclose(f)==0);
    }
};
uint32_t crc(const uint8_t* p,size_t n){
    uint32_t c=~uint32_t(0);
    for(size_t i=0;i<n;++i){
        c^=p[i];
        for(int bit=0;bit<8;++bit)c=(c>>1)^((c&1u)?0xedb88320u:0);
    }
    return ~c;
}
void fixCrc(std::vector<uint8_t>& raw){
    uint32_t sum=crc(raw.data()+22,raw.size()-22);
    for(int k=0;k<4;++k)raw[18+k]=uint8_t(sum>>(8*k));
}
uint64_t hash(const std::vector<uint32_t>& a){
    uint64_t h=14695981039346656037ull;
    for(uint32_t value:a)for(int k=0;k<4;++k){
        h^=(value>>(k*8))&255u;h*=1099511628211ull;
    }
    return h;
}
uint64_t picture(vpd::SceneView view){
    std::vector<uint32_t> b(vpd::kSceneWidth*vpd::kSceneHeight);
    CHECK(vpd::drawScene(b.data(),vpd::kSceneWidth,vpd::kSceneHeight,
                         vpd::kSceneWidth,view));
    return hash(b);
}
}
int main(){
    Temp temp;
    vpd::BackdropSource source;
    CHECK(source.reload(temp.path.c_str())==vpd::BackdropReload::Uninitialized);
    CHECK(!source.initialize(nullptr,0));
    CHECK(source.initialize(vpd_backdrop::kAtlasBlob,vpd_backdrop::kAtlasBytes));
    CHECK(!source.external());
    CHECK(vpd::backdropScale(source.atlas())==4);
    CHECK(source.atlas().frame_count==2);
    CHECK(vpd::parallaxOffset(0,5,512)==0);
    CHECK(vpd::parallaxOffset(5,5,512)==1);
    CHECK(vpd::parallaxOffset(100,5,512)==20);
    CHECK(vpd::parallaxOffset(100,2,512)==50);
    CHECK(vpd::parallaxOffset(-1,5,512)==511);
    CHECK(vpd::parallaxOffset(-1,2,512)==511);
    CHECK(vpd::parallaxOffset(10,0,512)==-1);

    vpd::SceneView view{};
    view.player_x_px=10;
    view.player_y_px=200;
    const uint64_t procedural=picture(view);
    view.backdrop_atlas=&source.atlas();
    const auto baseline=picture(view);
    CHECK(procedural!=baseline);
    CHECK(picture(view)==baseline);
    view.camera_x_px=80;
    CHECK(picture(view)!=baseline);
    view.camera_x_px=0;

    const auto* builtin=source.atlas().pixels;
    CHECK(source.reload("missing_background_test.vpat")==vpd::BackdropReload::Missing);
    CHECK(source.atlas().pixels==builtin);

    std::vector<uint8_t> raw(vpd_backdrop::kAtlasBlob,
              vpd_backdrop::kAtlasBlob+vpd_backdrop::kAtlasBytes);
    // A visibly opaque pixel from the nearest layer, within the 720px scene.
    const size_t pos=22u+(90u*256u+128u+10u)*4u;
    CHECK(raw[pos+3]==255);
    raw[pos]^=0x55;
    fixCrc(raw);
    temp.write(raw);
    CHECK(source.reload(temp.path.c_str())==vpd::BackdropReload::Loaded);
    CHECK(source.external());
    const auto* external=source.atlas().pixels;
    CHECK(external!=builtin);
    const auto updated=picture(view);
    CHECK(updated!=baseline);

    auto corrupt=raw;
    corrupt.back()^=1;
    temp.write(corrupt);
    CHECK(source.reload(temp.path.c_str())==vpd::BackdropReload::Invalid);
    CHECK(source.atlas().pixels==external);
    CHECK(picture(view)==updated);
    auto wrong=raw;
    wrong[14]=1;wrong[15]=0;
    temp.write(wrong);
    CHECK(source.reload(temp.path.c_str())==vpd::BackdropReload::Invalid);
    CHECK(source.atlas().pixels==external);

    // VPAT structurally valid, but unexpected ratio for the 512x384 viewport.
    auto geometry=raw;
    geometry[10]=64;geometry[11]=0;
    temp.write(geometry);
    CHECK(source.reload(temp.path.c_str())==vpd::BackdropReload::UnsupportedGeometry);
    CHECK(source.atlas().pixels==external);

    source.reset();
    CHECK(!source.external()&&source.atlas().pixels==builtin);
    CHECK(picture(view)==baseline);
    puts("PASS: two parallax layers, scroll, asset validation and last-good rollback");
}
