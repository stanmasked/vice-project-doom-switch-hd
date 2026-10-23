#include "driving_route_witness.hpp"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <string>

static void check(bool ok,const char* message) {
    if(!ok) throw std::runtime_error(message);
}

int main() {
    vpd::DrivingRouteProof proof;
    vpd::DrivingState state{};
    const std::uint64_t fingerprint=0x0123456789abcdefULL;
    const vpd::DriveInput right{false,true,false,false};

    state.frame=1;
    check(!proof.sample(right,state,fingerprint).valid,
          "route witness sampled before its 16-frame cadence");
    state.frame=16;
    auto first=proof.sample(right,state,fingerprint);
    check(first.valid && first.seq==1 && first.event==std::string("sample"),
          "first periodic route sample missing");
    check(first.frame==16 && first.source==std::string("libnx_pad") &&
          first.input.right && !first.input.left,
          "first route sample lost pad input provenance");

    state.frame=17;
    state.obstacle_serial=1;
    state.obstacles_passed=1;
    state.obstacle_x=570;
    state.obstacle_y=-110;
    auto lane=proof.sample({},state,fingerprint);
    check(lane.valid && lane.seq==2 && lane.frame==17,
          "obstacle recycle was not sampled between cadence frames");
    check(lane.obstacle_serial==1 && lane.obstacles_passed==1 &&
          lane.obstacle_x==570 && lane.obstacle_y==-110,
          "route sample lost recycled obstacle state");

    state.frame=32;
    auto periodic=proof.sample({},state,fingerprint);
    check(periodic.valid && periodic.seq==3 && periodic.frame==32,
          "next 16-frame route sample missing");

    state.frame=3197;
    state.obstacles_passed=29;
    state.obstacle_serial=29;
    state.obstacle_x=570;
    state.obstacle_y=268;
    auto exit=proof.exitRequest(state,fingerprint,false,true);
    check(exit.valid && exit.seq==4 && exit.event==std::string("exit_request"),
          "automatic route completion witness missing");
    check(exit.source==std::string("libnx_frame") && !exit.manual_exit &&
          exit.route_complete && exit.frame==3197,
          "route exit reason was not recorded faithfully");
    check(!proof.sample({},state,fingerprint).valid,
          "route sample accepted after terminal request");
    check(!proof.exitRequest(state,fingerprint,false,true).valid,
          "duplicate terminal request accepted");

    proof.reset();
    state={};
    state.frame=16;
    auto restarted=proof.sample({},state,fingerprint);
    check(restarted.valid && restarted.seq==1,
          "route proof reset retained prior sequence state");

    std::cout<<"VPD_DRIVING_ROUTE_WITNESS_PASS cadence=16 obstacle_edges=1 "
             <<"automatic_exit=1 duplicate_exit=0 reset=1\n";
}
