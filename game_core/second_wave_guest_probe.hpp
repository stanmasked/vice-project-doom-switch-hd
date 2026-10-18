#pragma once
// Independent native guest script for ROM-free *second-wave* stage logic.
// Runs in a fresh Simulation; never claims host pad-controlled wave-two play.
#include "simulation.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <sys/stat.h>

namespace vpd {
constexpr const char* kSentryProofPath =
    "sdmc:/switch/vice_project_doom/second_wave_witness.txt";
struct SentryProofRow {
    uint32_t frame=0;
    int32_t player_x=0;
    uint8_t guard_hp=0;
    uint8_t sentry_hp=0;
    uint8_t player_hp=0;
    uint16_t sentry_shots=0;
    uint16_t sentry_hits=0;
    uint16_t sentry_damage=0;
    bool wave=false;
    bool clear=false;
};
using SentryProofRows=std::array<SentryProofRow,5>;
inline SentryProofRow sentrySnapshot(const Simulation& world){
    return {world.frame(),world.player().x,world.guardEnemy().health,
            world.sentry().health,world.playerHealth(),
            world.sentry().shots_fired,world.sentry().shots_hit,
            world.sentry().projectile_hits,world.secondWaveActive(),
            world.stageCleared()};
}
inline bool reachSecondWave(Simulation& world,SentryProofRow& guard,
                            SentryProofRow& wave) {
    world.enableEnemyEncounter();
    for(int i=0;i<150 && world.guardEnemy().health;++i)
        world.tick(Input{Fire});
    if(world.guardEnemy().health!=0 || world.secondWaveActive())return false;
    guard=sentrySnapshot(world);
    for(int i=0;i<260 && !world.secondWaveActive();++i)
        world.tick(Input{Right});
    if(!world.secondWaveActive() || world.sentry().health!=2 ||
       world.player().x<26*kTileSize*kFixed)return false;
    wave=sentrySnapshot(world);
    return true;
}
inline bool collectSentryProof(SentryProofRows& rows) {
    Simulation stage;
    if(!reachSecondWave(stage,rows[0],rows[1]))return false;
    if(rows[0].guard_hp!=0 || rows[0].wave ||
       rows[1].guard_hp!=0 || !rows[1].wave)return false;
    // Independent stationary-target test of real hostile projectile physics.
    Simulation target;
    SentryProofRow unusedGuard{},unusedWave{};
    if(!reachSecondWave(target,unusedGuard,unusedWave))return false;
    for(int i=0;i<60 && target.player().x<29*kTileSize*kFixed;++i)
        target.tick(Input{Right});
    bool received=false;
    for(int i=0;i<170;++i){
        const auto before=target.sentry().shots_hit;
        target.tick(Input{});
        if(target.sentry().shots_hit>before){received=true;break;}
    }
    if(!received || target.playerHealth()>=5 || target.sentry().health!=2)
        return false;
    rows[2]=sentrySnapshot(target);

    bool defeated=false;
    for(int i=0;i<230;++i){
        stage.tick(Input{static_cast<uint8_t>(Right|Fire)});
        if(stage.sentry().health==0){defeated=true;break;}
    }
    if(!defeated || stage.sentry().projectile_hits!=2)return false;
    rows[3]=sentrySnapshot(stage);

    bool cleared=false;
    for(int i=0;i<300;++i){
        if(stage.stageCleared()){cleared=true;break;}
        stage.tick(Input{Right});
    }
    if(!cleared || stage.playerHealth()==0 ||
       stage.player().x<55*kTileSize*kFixed)return false;
    rows[4]=sentrySnapshot(stage);
    return rows[2].sentry_hits>0 && rows[2].sentry_shots>0 &&
           rows[4].clear && !rows[3].clear;
}
inline bool writeSentryProof(std::FILE* file,const SentryProofRows& rows){
    if(!file)return false;
    static constexpr const char* names[5]={
        "guard","wave","hostile_hit","turret_down","exit"
    };
    for(std::size_t i=0;i<rows.size();++i){
        const auto& r=rows[i];
        const char* scenario=i==2?"stationary":"stage";
        char line[302]{};
        const int len=std::snprintf(
            line,sizeof(line),
            "VPD_ROMFREE_WAVE2_V1 seq=%u event=%s scenario=%s "
            "frame=%u player_x=%ld guard_hp=%u sentry_hp=%u player_hp=%u "
            "sentry_shots=%u sentry_hits=%u sentry_damage=%u "
            "wave=%u clear=%u source=guest_script original_game_proven=no\n",
            static_cast<unsigned>(i+1),names[i],scenario,r.frame,
            static_cast<long>(r.player_x),static_cast<unsigned>(r.guard_hp),
            static_cast<unsigned>(r.sentry_hp),
            static_cast<unsigned>(r.player_hp),
            static_cast<unsigned>(r.sentry_shots),
            static_cast<unsigned>(r.sentry_hits),
            static_cast<unsigned>(r.sentry_damage),
            r.wave?1u:0u,r.clear?1u:0u);
        if(len<=0 || static_cast<std::size_t>(len)>=sizeof(line) ||
           std::fwrite(line,1,static_cast<std::size_t>(len),file)!=
           static_cast<std::size_t>(len))return false;
    }
    return std::fflush(file)==0;
}
inline bool persistSentryProof(bool has_sd){
    if(!has_sd)return false;
    SentryProofRows rows{};
    if(!collectSentryProof(rows))return false;
    std::FILE* f=std::fopen(kSentryProofPath,"w");
    if(!f)return false;
    const bool written=writeSentryProof(f,rows);
    return std::fclose(f)==0 && written;
}
inline bool resetSentryProof(bool has_sd){
    if(!has_sd)return false;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    std::FILE* f=std::fopen(kSentryProofPath,"w");
    return f && std::fclose(f)==0;
}
} // namespace vpd
