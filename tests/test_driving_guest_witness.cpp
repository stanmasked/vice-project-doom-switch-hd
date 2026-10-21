#include "driving_guest_witness.hpp"
#include "simulation.hpp"
#include <stdexcept>
#include <iostream>
static void check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
int main(){
 vpd::Simulation platform;const auto baseline=platform.fingerprint();
 vpd::DrivingGuestProof proof;vpd::DrivingState car;
 check(!proof.enter(false,true,car,baseline).seq,"autoplay entry accepted");
 check(!proof.enter(true,false,car,baseline).seq,"host-only entry accepted");
 auto run=[&](vpd::DriveInput in) {
  const auto prior=car;car.tick(in);
  return proof.tick(in,prior,car,platform.fingerprint()).seq;
 };
 check(proof.enter(true,true,car,baseline).seq==1,"entry missing");
 check(run({false,true,true,false})==2,"right+throttle missing");
 bool left=false;
 for(int i=0;i<16;++i)left=run({true,false,false,true})==3 || left;
 check(left,"left+brake missing");
 bool impact=false;
 for(int i=0;i<9;++i)impact=run({false,false,true,false})==4 || impact;
 for(int i=0;i<200 && !impact;++i)impact=run({})==4;
 check(impact && car.health==4 && car.impacts==1,"collision missing");
 check(!proof.leave(true,false,car,baseline).seq,"false exit accepted");
 // A failed exit invalidates the witness until a fresh session.
 check(!proof.leave(true,true,car,baseline).seq,"stale exit accepted");
 proof={};car.reset();
 check(proof.enter(true,true,car,baseline).seq==1,"fresh entry missing");
 check(run({false,true,true,false})==2,"second right missing");
 left=false;
 for(int i=0;i<16;++i)left=run({true,false,false,true})==3 || left;
 check(left,"second left missing");
 impact=false;
 for(int i=0;i<9;++i)impact=run({false,false,true,false})==4 || impact;
 for(int i=0;i<200 && !impact;++i)impact=run({})==4;
 check(impact && proof.leave(true,true,car,baseline).seq==5,
       "complete source-owned exit missing");
 check(platform.fingerprint()==baseline,"platform simulation changed");
 std::cout<<"VPD_ROMFREE_DRIVING_GUEST_FIVE_EVENTS_PASS"
          <<" source_pad_required=1 platform_frozen=1 original_rom=0\n";
}
