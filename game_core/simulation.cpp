#include "simulation.hpp"
#include <algorithm>
#include <cstdint>

namespace vpd {
namespace {
constexpr int32_t kRunSpeed=2*kFixed;
constexpr int32_t kGuardSpeed=kFixed;
constexpr int32_t kGuardDetection=144*kFixed;
constexpr int32_t kGuardStrike=20*kFixed;
constexpr int32_t kGuardPatrolMin=14*kTileSize*kFixed;
constexpr int32_t kGuardPatrolMax=20*kTileSize*kFixed;
constexpr uint8_t kGuardAttackDelay=32;
constexpr int32_t kSentryActivation=26*kTileSize*kFixed;
constexpr int32_t kSentryDetection=160*kFixed;
constexpr int32_t kSentryShotSpeed=3*kFixed;
constexpr uint8_t kSentryFireDelay=42;
constexpr uint16_t kSentryShotLife=90;
constexpr int32_t kStageExit=55*kTileSize*kFixed;
// Original, ROM-free prototype only: short grounded directional dash.
constexpr int32_t kDashSpeed=6*kFixed;
constexpr uint8_t kDashFrames=6;
constexpr uint8_t kDashRecovery=45;
constexpr int32_t kGravity=54;
constexpr int32_t kMaxFall=5*kFixed;
constexpr int32_t kJumpVelocity=-5*kFixed;
constexpr int32_t kProjectileSpeed=6*kFixed;
constexpr uint16_t kProjectileLifetime=90;
constexpr uint8_t kFireInterval=10;
// Fixed point floor division, including negatives.
int floorDiv(int value,int divisor) {
    int quotient=value/divisor;
    int remainder=value%divisor;
    return quotient-(remainder<0 ? 1:0);
}
}
Scene::Scene() {
    for(int x=0;x<kMapWidth;++x) setSolid(x,kMapHeight-1,true);
    for(int x=12;x<=21;++x) setSolid(x,11,true);
    for(int x=28;x<=35;++x) setSolid(x,9,true);
    for(int x=43;x<=52;++x) setSolid(x,12,true);
    for(int y=11;y<=13;++y) setSolid(59,y,true);
}
bool Scene::solid(int tx,int ty) const {
    if(tx<0 || tx>=kMapWidth || ty>=kMapHeight) return true;
    if(ty<0) return false;
    return tiles_[static_cast<std::size_t>(ty)*kMapWidth+static_cast<std::size_t>(tx)]!=0;
}
void Scene::setSolid(int tx,int ty,bool value) {
    if(tx>=0 && tx<kMapWidth && ty>=0 && ty<kMapHeight)
        tiles_[static_cast<std::size_t>(ty)*kMapWidth+static_cast<std::size_t>(tx)]=value?1:0;
}
char Scene::cell(int tx,int ty) const { return solid(tx,ty)?'#':' '; }
Simulation::Simulation(){ reset(); }
void Simulation::reset(){
    scene_=Scene{};
    player_=Actor{};
    player_.x=3*kTileSize*kFixed;
    player_.y=((kMapHeight-1)*kTileSize-kPlayerHeight)*kFixed;
    player_.grounded=true;
    frame_=0;
    camera_x_=0;
    jump_was_down_=false;
    facing_left_=false;
    fire_cooldown_=0;
    shots_fired_=0;
    dash_ticks_=0;
    dash_cooldown_=0;
    dash_direction_=0;
    dash_was_down_=false;
    dash_ever_used_=false;
    projectiles_.fill(Projectile{});
    target_=TrainingTarget{};
    encounter_enabled_=false;
    guard_=GuardEnemy{};
    player_health_=5;
    player_hit_flash_ticks_=0;
    second_wave_active_=false;
    stage_cleared_=false;
    sentry_=SentryEnemy{};
    enemy_projectiles_.fill(EnemyProjectile{});
}
void Simulation::enableEnemyEncounter(){
    if(encounter_enabled_)return;
    encounter_enabled_=true;
    guard_=GuardEnemy{};
    player_health_=5;
    player_hit_flash_ticks_=0;
    second_wave_active_=false;
    stage_cleared_=false;
    sentry_=SentryEnemy{};
    enemy_projectiles_.fill(EnemyProjectile{});
}
bool Simulation::collideAt(int32_t x,int32_t y) const{
    constexpr int tile=kTileSize*kFixed;
    const int x0=floorDiv(x,tile);
    const int x1=floorDiv(x+kPlayerWidth*kFixed-1,tile);
    const int y0=floorDiv(y,tile);
    const int y1=floorDiv(y+kPlayerHeight*kFixed-1,tile);
    for(int ty=y0;ty<=y1;++ty)
        for(int tx=x0;tx<=x1;++tx)
            if(scene_.solid(tx,ty)) return true;
    return false;
}
void Simulation::moveHorizontal(int32_t delta){
    const int dir=delta<0?-1:1;
    while(delta!=0){
        const int32_t step=dir*std::min<int32_t>(delta<0?-delta:delta,kFixed);
        if(collideAt(player_.x+step,player_.y)){
            const int tile=kTileSize*kFixed;
            if(dir>0){
                const int hit=floorDiv(player_.x+step+kPlayerWidth*kFixed-1,tile);
                player_.x=hit*tile-kPlayerWidth*kFixed;
            } else{
                const int hit=floorDiv(player_.x+step,tile);
                player_.x=(hit+1)*tile;
            }
            player_.vx=0;
            break;
        }
        player_.x+=step;
        delta-=step;
    }
}
void Simulation::moveVertical(int32_t delta){
    const int dir=delta<0?-1:1;
    player_.grounded=false;
    while(delta!=0){
        const int32_t step=dir*std::min<int32_t>(delta<0?-delta:delta,kFixed);
        if(collideAt(player_.x,player_.y+step)){
            const int tile=kTileSize*kFixed;
            if(dir>0){
                const int hit=floorDiv(player_.y+step+kPlayerHeight*kFixed-1,tile);
                player_.y=hit*tile-kPlayerHeight*kFixed;
                player_.grounded=true;
            } else{
                const int hit=floorDiv(player_.y+step,tile);
                player_.y=(hit+1)*tile;
            }
            player_.vy=0;
            break;
        }
        player_.y+=step;
        delta-=step;
    }
}
void Simulation::advanceProjectiles(){
    constexpr int32_t tile=kTileSize*kFixed;
    // Small swept steps prevent skipping a one-tile obstacle.
    for(auto& shot:projectiles_){
        if(!shot.active)continue;
        if(++shot.age>=kProjectileLifetime){
            shot.active=false;
            continue;
        }
        const int dir=shot.vx<0?-1:1;
        int32_t remaining=shot.vx<0?-shot.vx:shot.vx;
        while(remaining>0){
            const int32_t step=std::min<int32_t>(remaining,kFixed);
            const int32_t next=shot.x+dir*step;
            if(scene_.solid(floorDiv(next,tile),floorDiv(shot.y,tile))){
                shot.active=false;
                break;
            }
            // Opt-in guard uses the same one-pixel swept bullet positions as
            // the existing stationary target, so no shot can tunnel through it.
            if(encounter_enabled_ && guard_.health>0 &&
               next>=guard_.x && next<guard_.x+kPlayerWidth*kFixed &&
               shot.y>=guard_.y && shot.y<guard_.y+kPlayerHeight*kFixed){
                --guard_.health;
                ++guard_.projectile_hits;
                guard_.hit_flash_ticks=12; // real swept-impact feedback
                if(!guard_.health)guard_.alerted=false;
                shot.active=false;
                break;
            }
            if(second_wave_active_ && sentry_.health>0 &&
               next>=sentry_.x && next<sentry_.x+kPlayerWidth*kFixed &&
               shot.y>=sentry_.y && shot.y<sentry_.y+kPlayerHeight*kFixed){
                --sentry_.health;
                ++sentry_.projectile_hits;
                sentry_.hit_flash_ticks=12;
                shot.active=false;
                break;
            }
            // Hit test uses the very same one-pixel swept positions as
            // solid-tile collision, so a shot cannot skip a thin target.
            if(target_.health>0 &&
               next>=target_.x && next<target_.x+kTileSize*kFixed &&
               shot.y>=target_.y && shot.y<target_.y+kTileSize*kFixed) {
                --target_.health;
                ++target_.hits;
                shot.active=false;
                break;
            }
            shot.x=next;
            remaining-=step;
        }
    }
}
void Simulation::fireProjectile(){
    for(auto& shot:projectiles_){
        if(shot.active)continue;
        const int dir=facing_left_?-1:1;
        const int32_t x=player_.x+
            (facing_left_?-kFixed:kPlayerWidth*kFixed);
        const int32_t y=player_.y+(kPlayerHeight/2)*kFixed;
        constexpr int32_t tile=kTileSize*kFixed;
        if(scene_.solid(floorDiv(x,tile),floorDiv(y,tile)))return;
        shot=Projectile{x,y,dir*kProjectileSpeed,0,true};
        ++shots_fired_;
        fire_cooldown_=kFireInterval;
        return;
    }
}
void Simulation::advanceGuard(){
    if(!encounter_enabled_ || guard_.health==0)return;
    if(guard_.attack_cooldown>0)--guard_.attack_cooldown;
    const int32_t difference=player_.x-guard_.x;
    const int32_t abs_dx=difference<0?-difference:difference;
    const int32_t height=player_.y-guard_.y;
    const int32_t abs_y=height<0?-height:height;
    guard_.alerted=player_health_>0 && abs_dx<=kGuardDetection &&
                   abs_y<=kPlayerHeight*kFixed;
    int dir=guard_.direction;
    if(guard_.alerted){
        if(difference<0)dir=-1;
        else if(difference>0)dir=1;
    } else if(guard_.x>=kGuardPatrolMax)dir=-1;
    else if(guard_.x<=kGuardPatrolMin)dir=1;
    guard_.direction=static_cast<int8_t>(dir);
    const bool approach=!guard_.alerted || abs_dx>kGuardStrike;
    if(approach){
        int32_t next=std::clamp(guard_.x+dir*kGuardSpeed,
                                kGuardPatrolMin,kGuardPatrolMax);
        if(!collideAt(next,guard_.y))guard_.x=next;
        else if(!guard_.alerted)guard_.direction=static_cast<int8_t>(-dir);
    }
    const int32_t new_diff=player_.x-guard_.x;
    const int32_t new_abs=new_diff<0?-new_diff:new_diff;
    if(guard_.alerted && new_abs<=kGuardStrike &&
       guard_.attack_cooldown==0 && player_health_>0){
        --player_health_;
        player_hit_flash_ticks_=16; // follows actual contact damage
        ++guard_.attacks;
        guard_.attack_cooldown=kGuardAttackDelay;
    }
}
void Simulation::advanceEnemyProjectiles(){
    constexpr int32_t tile=kTileSize*kFixed;
    for(auto& bullet:enemy_projectiles_){
        if(!bullet.active)continue;
        if(++bullet.age>=kSentryShotLife){
            bullet.active=false;
            continue;
        }
        const int dir=bullet.vx<0?-1:1;
        int32_t left=bullet.vx<0?-bullet.vx:bullet.vx;
        while(left>0){
            const int32_t step=std::min<int32_t>(left,kFixed);
            const int32_t next=bullet.x+dir*step;
            if(scene_.solid(floorDiv(next,tile),floorDiv(bullet.y,tile))){
                bullet.active=false;
                break;
            }
            if(player_health_>0 &&
               next>=player_.x && next<player_.x+kPlayerWidth*kFixed &&
               bullet.y>=player_.y && bullet.y<player_.y+kPlayerHeight*kFixed){
                --player_health_;
                player_hit_flash_ticks_=16;
                ++sentry_.shots_hit;
                bullet.active=false;
                break;
            }
            bullet.x=next;
            left-=step;
        }
    }
}
void Simulation::advanceSentry(){
    if(!encounter_enabled_)return;
    if(!second_wave_active_ && guard_.health==0 &&
       player_.x>=kSentryActivation && player_health_>0){
        second_wave_active_=true;
    }
    if(!second_wave_active_)return;
    if(sentry_.hit_flash_ticks>0)--sentry_.hit_flash_ticks;
    // Existing fired projectiles are still simulated if the sentry dies.
    advanceEnemyProjectiles();
    if(sentry_.health==0){
        if(player_.x>=kStageExit && player_health_>0)stage_cleared_=true;
        return;
    }
    if(sentry_.fire_cooldown>0)--sentry_.fire_cooldown;
    const int32_t diff=player_.x-sentry_.x;
    const int32_t distance=diff<0?-diff:diff;
    const int32_t height=player_.y-sentry_.y;
    const int32_t vertical=height<0?-height:height;
    if(player_health_==0 || distance>kSentryDetection ||
       vertical>kPlayerHeight*kFixed || sentry_.fire_cooldown!=0)return;
    for(auto& bullet:enemy_projectiles_){
        if(bullet.active)continue;
        const int dir=diff<0?-1:1;
        const int32_t bx=sentry_.x+(dir<0?-kFixed:kPlayerWidth*kFixed);
        const int32_t by=sentry_.y+(kPlayerHeight/2)*kFixed;
        if(scene_.solid(floorDiv(bx,kTileSize*kFixed),
                        floorDiv(by,kTileSize*kFixed)))return;
        bullet={bx,by,dir*kSentryShotSpeed,0,true};
        ++sentry_.shots_fired;
        sentry_.fire_cooldown=kSentryFireDelay;
        break;
    }
}
void Simulation::tick(Input input){
    // A terminal encounter must not keep moving its hero, consuming enemy
    // shots or changing HP while the user reads the outcome. Retry is an
    // explicit separate Minus input, not repeated ticks or auto-reset.
    if(encounter_enabled_ && (player_health_==0 || stage_cleared_)){
        ++frame_;
        return;
    }
    if(encounter_enabled_){
        if(guard_.hit_flash_ticks>0)--guard_.hit_flash_ticks;
        if(player_hit_flash_ticks_>0)--player_hit_flash_ticks_;
    }
    const bool left=(input.buttons&Left)!=0;
    const bool right=(input.buttons&Right)!=0;
    if(dash_cooldown_>0)--dash_cooldown_;
    const bool dash_down=(input.buttons&Dash)!=0;
    if(dash_down && !dash_was_down_ && dash_ticks_==0 &&
       dash_cooldown_==0 && player_.grounded && left!=right){
        dash_direction_=left?-1:1;
        dash_ticks_=kDashFrames;
        dash_cooldown_=kDashRecovery;
        dash_ever_used_=true;
    }
    dash_was_down_=dash_down;
    const bool dash_step=dash_ticks_>0;
    player_.vx=dash_step?dash_direction_*kDashSpeed:
              (left==right?0:(left?-kRunSpeed:kRunSpeed));
    if(dash_step)facing_left_=dash_direction_<0;
    else if(left!=right)facing_left_=left;
    if(dash_step)--dash_ticks_;
    const bool jump_down=(input.buttons&Jump)!=0;
    if(jump_down && !jump_was_down_ && player_.grounded){
        player_.vy=kJumpVelocity;
        player_.grounded=false;
    }
    jump_was_down_=jump_down;
    player_.vy=std::min(player_.vy+kGravity,kMaxFall);
    moveHorizontal(player_.vx);
    // A solid wall cancels the remaining burst, without bypassing collision.
    if(dash_step && player_.vx==0)dash_ticks_=0;
    moveVertical(player_.vy);
    advanceProjectiles();
    if(fire_cooldown_>0)--fire_cooldown_;
    if((input.buttons&Fire)!=0 && fire_cooldown_==0)
        fireProjectile();
    advanceGuard();
    advanceSentry();
    camera_x_=std::clamp(player_.x/kFixed-10*kTileSize,0,(kMapWidth-40)*kTileSize);
    ++frame_;
}
uint64_t Simulation::fingerprint() const{
    // Explicit byte-order FNV-1a, not a hash of compiler struct layout.
    uint64_t hash=14695981039346656037ull;
    auto append=[&hash](uint32_t value){
        for(int byte=0;byte<4;++byte){
            hash^=static_cast<uint8_t>(value>>(8*byte));
            hash*=1099511628211ull;
        }
    };
    append(static_cast<uint32_t>(player_.x));
    append(static_cast<uint32_t>(player_.y));
    append(static_cast<uint32_t>(player_.vx));
    append(static_cast<uint32_t>(player_.vy));
    append(static_cast<uint32_t>(player_.grounded?1:0));
    append(static_cast<uint32_t>(camera_x_));
    append(frame_);
    append(static_cast<uint32_t>(jump_was_down_?1:0));
    // Preserve the existing reference hash when the map is untouched, but
    // include the *exact* live tile bytes whenever gameplay edits geometry.
    // Two physically identical actors with distinct solid tiles can have
    // different projectile collisions on the next tick.
    static const Scene pristine_map{};
    static_assert((kMapWidth*kMapHeight)%4==0,
                  "packed map replay serialization requires four-byte tiles");
    if(scene_.cells()!=pristine_map.cells()){
        append(0x4D415031u); // map-state version discriminator
        const auto& tiles=scene_.cells();
        for(std::size_t i=0;i<tiles.size();i+=4){
            const uint32_t word=
                static_cast<uint32_t>(tiles[i]) |
                (static_cast<uint32_t>(tiles[i+1])<<8) |
                (static_cast<uint32_t>(tiles[i+2])<<16) |
                (static_cast<uint32_t>(tiles[i+3])<<24);
            append(word);
        }
    }
    // Facing changes future projectile direction even before the first shot.
    // Preserve the legacy golden replay (which ends facing right) while
    // preventing false replay identity for an otherwise identical left pose.
    if(facing_left_ && !shots_fired_)append(0x4C454654u); // "LEFT"
    // Preserve the existing no-shot golden-replay hash. Projectile state
    // participates in replay identity as soon as shooting is exercised.
    if(shots_fired_){
        append(0x53484f54u); // explicit SHOT discriminator
        append(shots_fired_);
        append(static_cast<uint32_t>(fire_cooldown_));
        append(static_cast<uint32_t>(facing_left_?1:0));
        append(static_cast<uint32_t>(target_.x));
        append(static_cast<uint32_t>(target_.y));
        append(static_cast<uint32_t>(target_.health));
        append(static_cast<uint32_t>(target_.hits));
        for(const auto& shot:projectiles_){
            append(static_cast<uint32_t>(shot.active?1:0));
            append(static_cast<uint32_t>(shot.x));
            append(static_cast<uint32_t>(shot.y));
            append(static_cast<uint32_t>(shot.vx));
            append(static_cast<uint32_t>(shot.age));
        }
    }
    // Leave established ROM-free autoplay golden fingerprints untouched,
    // while distinguishing any input or physics state introduced by dash.
    if(dash_ever_used_ || dash_was_down_ || dash_ticks_ || dash_cooldown_){
        append(0x44415348u); // DASH state version discriminator
        append(static_cast<uint32_t>(dash_ticks_));
        append(static_cast<uint32_t>(dash_cooldown_));
        append(static_cast<uint32_t>(static_cast<int32_t>(dash_direction_)));
        append(static_cast<uint32_t>(dash_was_down_?1:0));
        append(static_cast<uint32_t>(dash_ever_used_?1:0));
    }
    if(encounter_enabled_){
        append(0x47554152u); // GUARD: opt-in enemy-state version
        append(static_cast<uint32_t>(guard_.x));
        append(static_cast<uint32_t>(guard_.y));
        append(static_cast<uint32_t>(guard_.health));
        append(static_cast<uint32_t>(guard_.alerted?1:0));
        append(static_cast<uint32_t>(static_cast<int32_t>(guard_.direction)));
        append(static_cast<uint32_t>(guard_.attack_cooldown));
        append(static_cast<uint32_t>(guard_.attacks));
        append(static_cast<uint32_t>(guard_.projectile_hits));
        append(static_cast<uint32_t>(guard_.hit_flash_ticks));
        append(static_cast<uint32_t>(player_health_));
        append(static_cast<uint32_t>(player_hit_flash_ticks_));
        // Preserve all existing single-guard guest witnesses/replay hashes:
        // the new wave enters the state identity only after activation.
        if(second_wave_active_){
            append(0x53454e54u); // "SENT" - wave two
            append(static_cast<uint32_t>(sentry_.x));
            append(static_cast<uint32_t>(sentry_.y));
            append(static_cast<uint32_t>(sentry_.health));
            append(static_cast<uint32_t>(sentry_.fire_cooldown));
            append(static_cast<uint32_t>(sentry_.hit_flash_ticks));
            append(static_cast<uint32_t>(sentry_.shots_fired));
            append(static_cast<uint32_t>(sentry_.shots_hit));
            append(static_cast<uint32_t>(sentry_.projectile_hits));
            append(static_cast<uint32_t>(stage_cleared_?1:0));
            for(const auto& bullet:enemy_projectiles_){
                append(static_cast<uint32_t>(bullet.active?1:0));
                append(static_cast<uint32_t>(bullet.x));
                append(static_cast<uint32_t>(bullet.y));
                append(static_cast<uint32_t>(bullet.vx));
                append(static_cast<uint32_t>(bullet.age));
            }
        }
    }
    return hash;
}
}
