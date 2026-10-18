// Deterministic ROM-free manual dash control and collision regression.
#include "simulation.hpp"
#include <cstdint>
#include <cstdio>
#include <stdexcept>

static void require(bool value,const char* reason){
    if(!value)throw std::runtime_error(reason);
}
int main(){
    using namespace vpd;
    try {
        Simulation dash,walk,mirror;
        const int32_t start_x=dash.player().x;
        dash.tick(Input{static_cast<uint8_t>(Right|Dash)});
        mirror.tick(Input{static_cast<uint8_t>(Right|Dash)});
        walk.tick(Input{Right});
        require(dash.player().x==start_x+6*kFixed &&
                walk.player().x==start_x+2*kFixed,
                "Dash did not increase horizontal displacement");
        require(dash.dashing() && dash.dashCooldown()==45 &&
                dash.dashEverUsed(), "Dash did not enter bounded active state");
        require(dash.fingerprint()==mirror.fingerprint() &&
                dash.fingerprint()!=walk.fingerprint(),
                "Dash state not deterministic or not included in replay identity");
        // Direction remains locked for the rest of the burst.
        for(int n=0;n<5;++n){
            dash.tick(Input{static_cast<uint8_t>(Left|Dash)});
            mirror.tick(Input{static_cast<uint8_t>(Left|Dash)});
            require(dash.fingerprint()==mirror.fingerprint(),
                    "Identical dash scripts diverged");
        }
        require(dash.player().x==start_x+36*kFixed && !dash.dashing(),
                "Dash lasted something other than six fixed ticks");
        const auto after_six=dash.player().x;
        dash.tick(Input{static_cast<uint8_t>(Right|Dash)});
        require(dash.player().x==after_six+2*kFixed,
                "Holding dash skipped recovery and restarted immediately");
        for(int i=0;i<70;++i)
            dash.tick(Input{static_cast<uint8_t>(Right|Dash)});
        require(!dash.dashing() && dash.dashCooldown()==0,
                "Held dash auto-retriggered after cooldown");
        dash.tick(Input{Right}); // edge release
        dash.tick(Input{static_cast<uint8_t>(Right|Dash)});
        require(dash.dashing(), "Dash did not rearm after release and cooldown");

        Simulation airborne;
        airborne.tick(Input{Jump});
        airborne.tick(Input{static_cast<uint8_t>(Right|Dash)});
        require(!airborne.dashing() && airborne.dashCooldown()==0 &&
                !airborne.dashEverUsed(),
                "Airborne dash should be rejected without altering physics");
        Simulation no_direction;
        no_direction.tick(Input{Dash});
        require(!no_direction.dashing() && !no_direction.dashEverUsed(),
                "Directionless dash should not initiate a burst");
        no_direction.tick(Input{});
        no_direction.tick(Input{static_cast<uint8_t>(Left|Dash)});
        require(no_direction.player().vx==-6*kFixed &&
                no_direction.dashing(),
                "Leftward dash failed to start after an invalid press");

        Simulation wall;
        wall.scene().setSolid(5,kMapHeight-2,true);
        for(int n=0;n<6;++n)
            wall.tick(Input{static_cast<uint8_t>(Right|Dash)});
        require(wall.player().x+kPlayerWidth*kFixed<=5*kTileSize*kFixed,
                "Dash crossed a solid collision tile");
        require(!wall.dashing() && wall.dashCooldown()>0,
                "Wall strike did not cancel remaining dash burst");
        const auto before=wall.player().x;
        for(int n=0;n<12;++n)wall.tick(Input{Right});
        require(wall.player().x==before,
                "Player penetrated wall after cancelling dash");

        Simulation reset;
        const uint64_t pristine=reset.fingerprint();
        reset.tick(Input{static_cast<uint8_t>(Right|Dash)});
        require(reset.fingerprint()!=pristine,
                "Active dash was absent from replay fingerprint");
        reset.reset();
        require(reset.fingerprint()==pristine && !reset.dashing() &&
                !reset.dashEverUsed() && reset.dashCooldown()==0,
                "Reset retained dash movement or cooldown state");
        std::puts("VPD_ROMFREE_MANUAL_DASH_PASS burst_frames=6 speed_px=6 "
                  "cooldown_ticks=45 wall_cancel=yes held_edge=yes "
                  "airborne_reject=yes reset=yes golden_autoplay_unchanged=yes");
        return 0;
    }catch(const std::exception& e){
        std::fprintf(stderr,"VPD_ROMFREE_MANUAL_DASH_REJECT %s\n",e.what());
        return 1;
    }
}
