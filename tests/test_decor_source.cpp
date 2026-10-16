#include "decor_source.hpp"
#include "scene_renderer.hpp"
#include "demo_decor.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>
#include <string>
#include <vector>
#define REQUIRE(x) do { if(!(x))throw std::runtime_error(#x); } while(0)

namespace {
struct FixtureFile {
    const std::string path="vpd_test_decor_source.vpat";
    ~FixtureFile(){std::remove(path.c_str());}
    void write(const std::vector<uint8_t>& bytes)const {
        FILE* f=std::fopen(path.c_str(),"wb");REQUIRE(f);
        REQUIRE(std::fwrite(bytes.data(),1,bytes.size(),f)==bytes.size());
        REQUIRE(std::fclose(f)==0);
    }
};
uint32_t crc(const uint8_t* p,size_t n) {
    uint32_t c=~uint32_t(0);
    for(size_t i=0;i<n;++i){
        c^=p[i];
        for(int k=0;k<8;++k)c=(c>>1)^((c&1u)?0xedb88320u:0);
    }
    return ~c;
}
void fixCrc(std::vector<uint8_t>& bytes){
    uint32_t sum=crc(bytes.data()+22,bytes.size()-22);
    for(int k=0;k<4;++k)bytes[18+k]=uint8_t(sum>>(8*k));
}
uint64_t fingerprint(const std::vector<uint32_t>& pixels){
    uint64_t result=14695981039346656037ull;
    for(uint32_t p:pixels)
        for(int c=0;c<4;++c) { result^=(p>>(c*8))&255u;result*=1099511628211ull; }
    return result;
}
uint64_t render(vpd::SceneView view){
    std::vector<uint32_t> screen(vpd::kSceneWidth*vpd::kSceneHeight);
    REQUIRE(vpd::drawScene(screen.data(),vpd::kSceneWidth,vpd::kSceneHeight,
                           vpd::kSceneWidth,view));
    return fingerprint(screen);
}
}
int main(){
    FixtureFile file;
    vpd::DecorSource source;
    REQUIRE(source.reload(file.path.c_str())==vpd::DecorReload::Uninitialized);
    REQUIRE(!source.initialize(nullptr,0));
    REQUIRE(source.initialize(vpd_decor::kAtlasBlob,vpd_decor::kAtlasBytes));
    REQUIRE(vpd::decorScale(source.atlas())==2);
    REQUIRE(source.atlas().frame_count==4);
    REQUIRE(vpd::decorativeWorldX(0)==80);
    REQUIRE(vpd::decorativeWorldX(1)==256);
    REQUIRE(vpd::decorFrame(0,0)==0);
    REQUIRE(vpd::decorFrame(0,24)==1);
    REQUIRE(vpd::decorFrame(1,0)==2);
    REQUIRE(vpd::decorFrame(1,9)==3);

    // Order-independent deterministic compositing: each layer differs.
    std::vector<uint32_t> back(vpd::kSceneWidth*vpd::kSceneHeight,0xff102040u);
    auto front=back;
    REQUIRE(vpd::drawDecorLayer(back.data(),vpd::kSceneWidth,vpd::kSceneHeight,
                                vpd::kSceneWidth,source.atlas(),0,0,false));
    REQUIRE(vpd::drawDecorLayer(front.data(),vpd::kSceneWidth,vpd::kSceneHeight,
                                vpd::kSceneWidth,source.atlas(),0,0,true));
    REQUIRE(fingerprint(back)!=fingerprint(front));
    REQUIRE(fingerprint(back)!=fingerprint(std::vector<uint32_t>(
                vpd::kSceneWidth*vpd::kSceneHeight,0xff102040u)));
    REQUIRE(!vpd::drawDecorLayer(nullptr,vpd::kSceneWidth,vpd::kSceneHeight,
                                vpd::kSceneWidth,source.atlas(),0,0,false));

    vpd::SceneView view{};
    view.player_x_px=65; view.player_y_px=194;
    const uint64_t no_decoration=render(view);
    view.decor_atlas=&source.atlas();
    const uint64_t initial=render(view);
    REQUIRE(no_decoration!=initial);
    REQUIRE(render(view)==initial);
    view.frame=24;
    REQUIRE(render(view)!=initial);
    view.frame=0;view.camera_x_px=78;
    REQUIRE(render(view)!=initial);
    view.camera_x_px=0;

    const uint8_t* built_in=source.atlas().pixels;
    REQUIRE(source.reload("missing_test_decor.vpat")==vpd::DecorReload::Missing);
    REQUIRE(source.atlas().pixels==built_in);
    std::vector<uint8_t> alternative(vpd_decor::kAtlasBlob,
                                     vpd_decor::kAtlasBlob+vpd_decor::kAtlasBytes);
    const size_t offset=22u+(15u*96u+11u)*4u;
    REQUIRE(alternative[offset+3]==255);
    alternative[offset]^=0x71u;
    fixCrc(alternative);
    file.write(alternative);
    REQUIRE(source.reload(file.path.c_str())==vpd::DecorReload::Loaded);
    REQUIRE(source.external());
    const uint8_t* accepted=source.atlas().pixels;
    REQUIRE(accepted!=built_in);
    const uint64_t changed=render(view);
    REQUIRE(changed!=initial);
    std::vector<uint8_t> broken=alternative;
    broken.back()^=1u;
    file.write(broken);
    REQUIRE(source.reload(file.path.c_str())==vpd::DecorReload::Invalid);
    REQUIRE(source.atlas().pixels==accepted);
    REQUIRE(render(view)==changed);
    broken=alternative;
    broken[14]=3; // valid VPAT record layout but wrong 4-frame contract
    file.write(broken);
    REQUIRE(source.reload(file.path.c_str())==vpd::DecorReload::Invalid);
    REQUIRE(source.atlas().pixels==accepted);
    broken=alternative;
    broken[10]=12; // 12x32 cells: supported VPAT but wrong decor aspect
    file.write(broken);
    REQUIRE(source.reload(file.path.c_str())==vpd::DecorReload::UnsupportedGeometry);
    REQUIRE(source.atlas().pixels==accepted);
    source.reset();
    REQUIRE(!source.external());
    REQUIRE(source.atlas().pixels==built_in);
    REQUIRE(render(view)==initial);
    puts("PASS: alpha props, front/back composition, world scroll, animation, SD rollback");
}
