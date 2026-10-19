// Strict source-owned hit-light witness and bounded pixel sample regression.
#include "simulation.hpp"
#include "hd_hit_light_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>
namespace {
void check(bool condition,const char* error){
    if(!condition)throw std::runtime_error(error);
}
}
int main(){
 try{
    using namespace vpd;
    Simulation game;
    game.enableEnemyEncounter();
    constexpr int width=1280,height=720,stride=1300;
    std::vector<uint32_t> image(static_cast<std::size_t>(stride)*height,
                                0xff203040u);
    const auto before=sampleGuardImpact(image.data(),width,height,stride,
                                        500,580);
    check(before.count==25,"Source unlit sample grid not complete");
    auto changed=before;
    check(diffGuardImpactSamples(before,changed)==0,
          "Identical samples falsely suggested an impact effect");
    for(int y=-24;y<=24;y+=12)
        for(int x=-24;x<=24;x+=12)
            image[static_cast<std::size_t>(580+y)*stride+500+x]=0xff48ffffu;
    changed=sampleGuardImpact(image.data(),width,height,stride,500,580);
    check(changed.count==25 &&
          diffGuardImpactSamples(before,changed)==25 &&
          before.hash!=changed.hash,
          "Source glow samples are not distinct");
    for(int i=0;i<8;++i)game.tick(Input{Right});
    std::FILE* f=std::tmpfile();
    check(f!=nullptr,"Native HD source witness tempfile unavailable");
    check(!writeHitLightEvidence(f,game,before,changed,25),
          "Healthy pre-fire actor accepted a false light event");
    game.tick(Input{Fire});
    check(!writeHitLightEvidence(f,game,before,changed,25),
          "Bullet spawn accepted as a real guard collision");
    for(int i=0;i<120 && game.guardEnemy().projectile_hits==0;++i)
        game.tick(Input{});
    check(game.guardEnemy().health==2 &&
          game.guardEnemy().projectile_hits==1 &&
          game.guardEnemy().hit_flash_ticks>0 &&
          game.shotsFired()==1 && game.playerHealth()==5,
          "Real source projectile did not create valid guard impact state");
    check(!writeHitLightEvidence(f,game,before,before,0),
          "Unchanged pixels forged a native impact");
    check(!writeHitLightEvidence(f,game,before,changed,2),
          "Tiny sample noise forged 25-sample glow");
    check(writeHitLightEvidence(f,game,before,changed,25),
          "Authentic hit plus distinct framebuffer light was rejected");
    std::rewind(f);
    char line[512]{};
    check(std::fgets(line,sizeof(line),f)!=nullptr &&
          std::strstr(line,"VPD_ROMFREE_HD_HIT_LIGHT_V1") &&
          std::strstr(line,"event=source_guard_impact") &&
          std::strstr(line,"samples=25 changed=25") &&
          std::strstr(line,"same_simulation_frame=yes native_framebuffer=yes") &&
          std::strstr(line,"source=live_guest original_game_proven=no"),
          "HD guest witness not canonical");
    check(std::fgets(line,sizeof(line),f)==nullptr,
          "Invalid HD source events leaked into guest witness");
    std::fclose(f);
    std::puts("VPD_HD_HIT_LIGHT_HOST_PASS genuine_guard_impact=yes "
              "source_guard_hp=2 sample_count=25 changed_samples=25 "
              "false_fire_or_same_pixels_rejected=yes "
              "live_nexium_proven=no original_game_proven=no");
    return 0;
 }catch(const std::exception& error){
    std::fprintf(stderr,"VPD_HD_HIT_LIGHT_HOST_FAIL %s\n",error.what());
    return 1;
 }
}
