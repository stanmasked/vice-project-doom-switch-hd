#include "simulation.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
static void check(bool ok,const char* message){
    if(!ok)throw std::runtime_error(message);
}
int main(){
    try{
        using namespace vpd;
        Simulation a,b;
        check(a.fingerprint()==b.fingerprint(),"initial deterministic state");
        const int32_t start_x=a.player().x;
        const int32_t floor_y=a.player().y;
        for(int f=0;f<300;++f){
            uint8_t buttons=f<180?Right:0;
            if((f>=12&&f<24)||(f>=130&&f<144))buttons|=Jump;
            const Input input{buttons};
            a.tick(input);
            b.tick(input);
            check(a.fingerprint()==b.fingerprint(),"two replays differ");
            check(a.player().y+kPlayerHeight*kFixed<=kMapHeight*kTileSize*kFixed,
                "actor falls through floor");
        }
        check(a.player().x>start_x,"actor never moved");
        check(a.cameraX()>0,"camera did not scroll");
        check(a.frame()==300,"incorrect frame count");
        check(a.fingerprint()==7488840217753765732ull,
            "300-frame golden replay hash changed");
        std::cout<<"Replay 300 frames: "<<a.fingerprint()<<'\n';
        a.reset();
        check(a.frame()==0 && a.player().x==start_x && a.player().y==floor_y,
            "reset must restore initial state");
        Simulation rising;
        rising.tick(Input{Jump});
        check(rising.player().y<floor_y,"jump must move actor upward");
        for(int f=0;f<90;++f)rising.tick(Input{});
        check(rising.player().grounded && rising.player().y==floor_y,
            "jump must land exactly on floor");
        Simulation wall;
        wall.scene().setSolid(5,kMapHeight-2,true);
        for(int f=0;f<100;++f)wall.tick(Input{Right});
        check(wall.player().x+kPlayerWidth*kFixed<=5*kTileSize*kFixed,
            "actor passed through wall");
        Simulation held;
        for(int f=0;f<120;++f)held.tick(Input{static_cast<uint8_t>(Jump)});
        check(held.player().grounded && held.player().y==floor_y,
            "holding jump must not auto-repeat");
        // ROM-free fixed-step projectile combat prototype.
        Simulation firing,mirror;
        for(int f=0;f<135;++f) {
            uint8_t controls=(f<55)?static_cast<uint8_t>(Fire):0;
            if(f>=60&&f<65)controls|=Left;
            if(f>=65&&f<100)controls|=Fire;
            const Input input{controls};
            firing.tick(input);
            mirror.tick(input);
            check(firing.fingerprint()==mirror.fingerprint(),
                  "projectile physics broke deterministic replay");
            for(const auto& shot:firing.projectiles()){
                if(!shot.active)continue;
                const int px=shot.x/(kFixed*kTileSize);
                const int py=shot.y/(kFixed*kTileSize);
                check(!firing.scene().solid(px,py),
                      "active projectile crossed a solid tile");
            }
        }
        check(firing.shotsFired()>=5,"holding fire never repeated shots");
        check(firing.fingerprint()!=Simulation{}.fingerprint(),
              "combat-state fingerprint omitted shots");
        Simulation cooldown;
        for(int f=0;f<24;++f)cooldown.tick(Input{Fire});
        check(cooldown.shotsFired()==3,
              "fire cooldown should yield frames 1,11,21");
        Simulation blocking;
        blocking.scene().setSolid(5,kMapHeight-2,true);
        blocking.tick(Input{Fire});
        check(blocking.shotsFired()==1 &&
              blocking.projectiles()[0].active,
              "shot was not launched toward the wall");
        for(int f=0;f<12;++f)blocking.tick(Input{});
        check(!blocking.projectiles()[0].active,
              "shot tunneled through adjacent solid wall");
        // Same location, velocity and frame count, but different
        // future shot direction: hash must distinguish left/right facing.
        Simulation face_right,face_left;
        face_right.tick(Input{Left});
        face_right.tick(Input{Right});
        face_right.tick(Input{});
        face_left.tick(Input{Right});
        face_left.tick(Input{Left});
        face_left.tick(Input{});
        check(face_left.player().x==face_right.player().x &&
              face_left.player().y==face_right.player().y &&
              face_left.player().vx==face_right.player().vx &&
              face_left.player().vy==face_right.player().vy &&
              face_left.frame()==face_right.frame(),
              "facing hash test did not reach equivalent physical pose");
        check(face_left.fingerprint()!=face_right.fingerprint(),
              "opposite shot directions yielded identical replay state");
        face_left.tick(Input{Fire});
        face_right.tick(Input{Fire});
        check(face_left.projectiles()[0].vx<0 &&
              face_right.projectiles()[0].vx>0,
              "facing divergence was not observable in fired shots");
        Simulation leftshot;
        leftshot.tick(Input{Left});
        leftshot.tick(Input{Fire});
        check(leftshot.projectiles()[0].active &&
              leftshot.projectiles()[0].vx<0,
              "shot did not follow last directional input");
        Simulation expired;
        expired.tick(Input{Fire});
        for(int f=0;f<95;++f)expired.tick(Input{});
        for(const auto& shot:expired.projectiles())
            check(!shot.active,"expired projectile remains active");
        firing.reset();
        check(firing.shotsFired()==0 &&
              firing.fingerprint()==Simulation{}.fingerprint(),
              "combat state survived a full gameplay reset");
        // Same synthetic shooting timeline yields the same three target hits.
        Simulation target_a,target_b;
        check(target_a.trainingTarget().health==3 &&
              target_a.trainingTarget().hits==0,
              "practice target did not initialize");
        for(int f=0;f<110;++f) {
            target_a.tick(Input{Fire});
            target_b.tick(Input{Fire});
            check(target_a.fingerprint()==target_b.fingerprint(),
                  "target health or hits lost deterministic replay");
        }
        check(target_a.trainingTarget().health==0 &&
              target_a.trainingTarget().hits==3,
              "three authentic swept shot impacts must destroy target");
        for(int f=0;f<110;++f)target_a.tick(Input{Fire});
        check(target_a.trainingTarget().hits==3,
              "already destroyed target counted duplicate impacts");
        Simulation shielded;
        // An earlier solid column must block every bullet and protect target.
        shielded.scene().setSolid(10,kMapHeight-2,true);
        for(int f=0;f<110;++f)shielded.tick(Input{Fire});
        check(shielded.trainingTarget().health==3 &&
              shielded.trainingTarget().hits==0,
              "shots bypassed blocking world geometry to hit target");
        target_a.reset();
        check(target_a.trainingTarget().health==3 &&
              target_a.trainingTarget().hits==0,
              "reset did not restore target integrity");
        // The scene layout is mutable, so replay identity must include
        // the exact solid tile map, not just player/projectile states.
        Simulation map_a,map_b;
        check(map_a.fingerprint()==map_b.fingerprint(),
              "fresh maps must be replay-equivalent");
        const uint64_t original_map_hash=map_b.fingerprint();
        map_b.scene().setSolid(57,3,true); // far away from player
        check(map_a.player().x==map_b.player().x &&
              map_a.player().y==map_b.player().y,
              "map test accidentally moved the player");
        check(map_a.fingerprint()!=map_b.fingerprint(),
              "changed tile geometry missing from replay fingerprint");
        map_b.scene().setSolid(57,3,false);
        check(map_b.fingerprint()==original_map_hash,
              "restoring original map should restore original fingerprint");
        map_a.scene().setSolid(57,3,true);
        check(map_a.fingerprint()!=map_b.fingerprint(),
              "modified map should differ from restored default map");
        map_b.scene().setSolid(57,3,true);
        check(map_a.fingerprint()==map_b.fingerprint(),
              "identical modified maps differ across replay instances");
        map_a.tick(Input{Fire});
        map_b.tick(Input{Fire});
        check(map_a.fingerprint()==map_b.fingerprint(),
              "modified tile layouts break firing replay determinism");
        map_b.scene().setSolid(57,4,true);
        check(map_a.fingerprint()!=map_b.fingerprint(),
              "map modifications after shooting must also change replay identity");
        Simulation idle;
        for(int f=0;f<600;++f)idle.tick(Input{});
        check(idle.player().grounded && idle.player().y==floor_y,
            "idle floor drift");
        std::cout<<"PASS: deterministic replay, camera, floor, wall, jump, ROM-free fire cooldown/collision/lifetime, reset\n";
        return 0;
    } catch(const std::exception& e){
        std::cerr<<"FAIL: "<<e.what()<<'\n';
        return 1;
    }
}
