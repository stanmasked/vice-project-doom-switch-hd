#pragma once
// Native evidence from the *visible*, actual-pad-input manual Simulation.
// Independent guest-scripted second_wave_witness.txt is never a substitute.
#include "simulation.hpp"
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <sys/stat.h>
namespace vpd {
constexpr const char* kLiveSecondWavePath =
    "sdmc:/switch/vice_project_doom/second_wave_live_witness.txt";
enum class LiveWaveEvent : unsigned {
    Activated=1, Fire=2, FirstImpact=3, Defeat=4, Exit=5
};
inline bool liveWaveWrite(std::FILE* file,LiveWaveEvent event,
                          const Simulation& game,uint8_t input) {
    if(!file || !game.enemyEncounterEnabled() ||
       !game.secondWaveActive() || game.guardEnemy().health!=0 ||
       game.frame()==0 || game.frame()>1400)return false;
    const SentryEnemy& turret=game.sentry();
    const unsigned seq=static_cast<unsigned>(event);
    const int32_t x=game.player().x;
    const bool right=(input&Right)!=0;
    const bool fire=(input&Fire)!=0;
    const bool alive=game.playerHealth()>0;
    if(x<0 || x>kMapWidth*kTileSize*kFixed ||
       turret.health>2 || turret.projectile_hits>2)return false;
    switch(event){
        case LiveWaveEvent::Activated:
            if(!right || !alive || x<26*kTileSize*kFixed ||
               turret.health!=2 || turret.projectile_hits!=0 ||
               game.stageCleared())return false;
            break;
        case LiveWaveEvent::Fire:
            if(!right || !fire || !alive || turret.health!=2 ||
               turret.projectile_hits!=0 ||
               game.shotsFired()==0 || game.stageCleared())return false;
            break;
        case LiveWaveEvent::FirstImpact:
            if(!alive || turret.health!=1 ||
               turret.projectile_hits!=1 || game.stageCleared())return false;
            break;
        case LiveWaveEvent::Defeat:
            if(!alive || turret.health!=0 ||
               turret.projectile_hits!=2 || game.stageCleared())return false;
            break;
        case LiveWaveEvent::Exit:
            if(!alive || !game.stageCleared() ||
               turret.health!=0 || turret.projectile_hits!=2 ||
               x<55*kTileSize*kFixed)return false;
            break;
    }
    static constexpr const char* names[5]={
        "wave","fire","hit1","defeat","exit"
    };
    char line[320]{};
    const int n=std::snprintf(line,sizeof(line),
        "VPD_ROMFREE_WAVE2_LIVE_V1 seq=%u event=%s frame=%u "
        "player_x=%ld hero_hp=%u turret_hp=%u turret_hits=%u "
        "turret_shots=%u hero_shots=%u wave=1 clear=%u "
        "input_right=%u input_fire=%u source=live_guest "
        "original_game_proven=no\n",
        seq,names[seq-1],game.frame(),static_cast<long>(x),
        static_cast<unsigned>(game.playerHealth()),
        static_cast<unsigned>(turret.health),
        static_cast<unsigned>(turret.projectile_hits),
        static_cast<unsigned>(turret.shots_fired),
        game.shotsFired(),game.stageCleared()?1u:0u,
        right?1u:0u,fire?1u:0u);
    return n>0 && static_cast<std::size_t>(n)<sizeof(line) &&
           std::fwrite(line,1,static_cast<std::size_t>(n),file)==
             static_cast<std::size_t>(n) && std::fflush(file)==0;
}
inline bool liveWaveReset(bool has_sd){
    if(!has_sd)return false;
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    std::FILE* f=std::fopen(kLiveSecondWavePath,"w");
    return f && std::fclose(f)==0;
}
inline bool liveWaveAppend(bool has_sd,LiveWaveEvent event,
                           const Simulation& game,uint8_t input){
    if(!has_sd)return false;
    std::FILE* f=std::fopen(kLiveSecondWavePath,"a");
    if(!f)return false;
    const bool ok=liveWaveWrite(f,event,game,input);
    return std::fclose(f)==0 && ok;
}
} // namespace vpd
