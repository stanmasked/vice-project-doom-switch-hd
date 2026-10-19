// Native source + bounded RGB witness; does not itself prove NeXium video.
#include "hd_hostile_halo_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>
namespace {
void check(bool valid,const char* error){
    if(!valid)throw std::runtime_error(error);
}
}
int main(){
 try{
    using namespace vpd;
    constexpr int width=1280,height=720,stride=1311;
    std::vector<uint32_t> pixels(static_cast<std::size_t>(stride)*height,
                                 0xff213c58u);
    const auto plain=sampleHostileHalo(
        pixels.data(),width,height,stride,420,575);
    check(plain.count==kHostileHaloSamples,
          "Hostile halo ROI was not sampled completely");
    check(!sampleHostileHalo(nullptr,width,height,stride,420,575).count,
          "Null framebuffer accepted");
    check(!sampleHostileHalo(pixels.data(),width,height,1,420,575).count,
          "Bad stride accepted");
    check(!sampleHostileHalo(pixels.data(),width,height,stride,3,575).count,
          "Offscreen ROI was silently zero padded");
    check(!countHostileHaloChanges(plain,plain),
          "Unchanged pixels forged a hostile halo");
    for(unsigned i=0;i<12;++i)
        pixels[static_cast<std::size_t>(575)*stride+405+i]=0xff79adf1u;
    const auto lit=sampleHostileHalo(
        pixels.data(),width,height,stride,420,575);
    check(countHostileHaloChanges(plain,lit)==12 && plain.hash!=lit.hash,
          "Sampling missed bounded 12-pixel difference");
    Simulation game;
    game.enableEnemyEncounter();
    std::FILE* file=std::tmpfile();
    check(file!=nullptr,"No native witness stream");
    check(!writeHostileHaloWitness(file,game,0,plain,lit,12),
          "Pre-wave source was incorrectly accepted");
    for(int i=0;i<140 && game.guardEnemy().health;++i)
        game.tick(Input{Fire});
    check(game.guardEnemy().health==0,
          "Authentic first guard fire hits never completed");
    for(int i=0;i<260 && !game.secondWaveActive();++i)
        game.tick(Input{Right});
    check(game.secondWaveActive(),"Genuine right movement did not open wave");
    for(int i=0;i<200 && game.player().x<29*kTileSize*kFixed;++i)
        game.tick(Input{Right});
    bool hostile_source=false;
    for(int i=0;i<160;++i){
        for(const auto& bullet:game.enemyProjectiles())
            hostile_source|=bullet.active;
        if(hostile_source)break;
        game.tick(Input{});
    }
    check(hostile_source && game.sentry().shots_fired>0 &&
          game.sentry().health==2 && game.playerHealth()>0,
          "Genuine active turret bullet did not reach render state");
    unsigned slot=kMaxEnemyProjectiles;
    for(unsigned i=0;i<kMaxEnemyProjectiles;++i)
        if(game.enemyProjectiles()[i].active){slot=i;break;}
    check(slot<kMaxEnemyProjectiles,"No live projectile slot");
    check(!writeHostileHaloWitness(file,game,slot,plain,plain,0),
          "Identical unlit/lit frames accepted");
    check(!writeHostileHaloWitness(file,game,slot,plain,lit,2),
          "Wrong pixel difference accepted");
    check(!writeHostileHaloWitness(file,game,kMaxEnemyProjectiles,
                                   plain,lit,12),
          "Out-of-range hostile shot slot accepted");
    check(writeHostileHaloWitness(file,game,slot,plain,lit,12),
          "Genuine active wave-two bullet falsely rejected");
    std::rewind(file);
    char row[600]{};
    check(std::fgets(row,sizeof(row),file)!=nullptr &&
          std::strstr(row,"VPD_ROMFREE_HOSTILE_HALO_V1") &&
          std::strstr(row,"event=fourth_turret_bullet") &&
          std::strstr(row,"samples=1024 changed=12") &&
          std::strstr(row,"same_guest_frame=yes native_framebuffer=yes"),
          "Source hostile halo record noncanonical");
    check(std::fgets(row,sizeof(row),file)==nullptr,
          "Rejected source records were persisted");
    std::fclose(file);
    std::puts("VPD_HOSTILE_HALO_HOST_PASS source_wave2_bullet=yes "
              "distinct_pixels=12 out_of_range_rejected=yes "
              "guest_emulator_proven=no original_game_proven=no");
    return 0;
 }catch(const std::exception& error){
    std::fprintf(stderr,"VPD_HOSTILE_HALO_HOST_FAIL %s\n",error.what());
    return 1;
 }
}
