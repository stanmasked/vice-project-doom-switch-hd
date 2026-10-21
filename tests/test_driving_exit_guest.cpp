#include "driving_exit_witness.hpp"
#include "driving_stage_exit.hpp"
#include "simulation.hpp"
#include <stdexcept>
#include <iostream>
static void check(bool yes,const char* msg){if(!yes)throw std::runtime_error(msg);}
int main() {
  vpd::Simulation platform;const auto fp=platform.fingerprint();
  vpd::DrivingStageExit timeline;
  vpd::DrivingExitProof proof;
  check(!proof.begin(false,25,fp).valid,"host-only input allowed");
  check(timeline.requestAfterDrivingFrame(true,true),"source transition not armed");
  check(proof.begin(true,25,fp).valid,"native road source missing");
  check(!proof.begin(true,25,fp).valid,"duplicate road accepted");
  check(!proof.black(2,fp,true).valid,"skipped first black accepted");
  for(unsigned n=1;n<=41;++n) {
    check(timeline.present()==vpd::stage_transition::Scene::Black,
          "timeline scene was not black");
    check(!proof.black(n,fp,false).valid,"nonblack pixel accepted");
    auto event=proof.black(n,fp,true);
    check(event.valid && event.seq==n && event.black_frames==n,
          "black native event sequence incorrect");
    check(!proof.black(n,fp,true).valid,"duplicate black record accepted");
  }
  check(timeline.present()==vpd::stage_transition::Scene::Platform,
        "platform did not follow 41 black frames");
  check(proof.platform(fp).valid,"platform record missing");
  check(!proof.platform(fp).valid,"second platform record accepted");
  check(platform.fingerprint()==fp,"legacy simulation mutated");
  std::cout<<"VPD_ROMFREE_DRIVING_EXIT_GUEST_PASS source_black_frames=41"
           <<" native_records=43 frozen_platform=1 original_assets=no\n";
}
