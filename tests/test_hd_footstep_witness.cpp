// Source-gated, CPU framebuffer-only native dust witness test.
#include "hd_footstep_witness.hpp"
#include <cstdio>
#include <cstring>
#include <stdexcept>
#include <vector>
namespace {
void check(bool ok,const char* why){if(!ok)throw std::runtime_error(why);}
}
int main(){
 try{
    using namespace vpd;
    constexpr int width=1280,height=720,stride=1301;
    std::vector<uint32_t> buffer(static_cast<std::size_t>(stride)*height,
                                 0xff263d52u);
    auto no_dust=sampleFootstep(buffer.data(),width,height,stride,180,606);
    check(no_dust.count==kDustProofPixels,
          "Ground ROI did not collect all source pixels");
    check(sampleFootstep(nullptr,width,height,stride,180,606).count==0,
          "Null target should reject dust sample");
    check(sampleFootstep(buffer.data(),width,height,2,180,606).count==0,
          "Invalid row stride should reject footstep sample");
    check(sampleFootstep(buffer.data(),width,height,stride,0,606).count==0,
          "Offscreen heel must reject partial sample, not zero-fill");
    check(changedFootstepPixels(no_dust,no_dust)==0,
          "Same pixels unexpectedly claimed a dust difference");
    for(int i=0;i<12;++i)
        buffer[static_cast<std::size_t>(600)*stride+151+i]=0xffaaaa8au;
    const auto dust=sampleFootstep(buffer.data(),width,height,stride,180,606);
    check(changedFootstepPixels(no_dust,dust)==12&&
          no_dust.hash!=dust.hash,
          "Difference sampler did not detect authored dust pixels");
    Simulation game;
    game.enableEnemyEncounter();
    auto* file=std::tmpfile();
    check(file!=nullptr,"Temporary native proof file unavailable");
    check(!writeFootstepProof(file,game,no_dust,dust,12),
          "Stationary spawn incorrectly certified motion dust");
    for(int i=0;i<8;++i)game.tick(Input{Right});
    check(fourthFresh(game)&&game.player().grounded&&
          game.player().vx==2*kFixed&&
          game.player().x>=3*kTileSize*kFixed+16*kFixed,
          "Source fourth ground right step not recreated");
    check(!writeFootstepProof(file,game,no_dust,no_dust,0),
          "Identical framebuffer samples forged motion effect");
    check(!writeFootstepProof(file,game,no_dust,dust,2),
          "Forged changed sample count accepted");
    check(writeFootstepProof(file,game,no_dust,dust,12),
          "Authentic fourth grounded movement rejected");
    std::rewind(file);
    char line[512]{};
    check(std::fgets(line,sizeof(line),file)&&
          std::strstr(line,"VPD_ROMFREE_HD_FOOTSTEP_V1")&&
          std::strstr(line,"event=fourth_ground_move")&&
          std::strstr(line,"samples=1056 changed=12")&&
          std::strstr(line,"same_guest_frame=yes native_framebuffer=yes"),
          "Native ground-step record schema corrupted");
    check(std::fgets(line,sizeof(line),file)==nullptr,
          "Rejected synthetic events were written");
    std::fclose(file);
    std::puts("VPD_NATIVE_FOOTSTEP_HOST_PASS source_moving=yes "
              "source_grounded=yes changed_pixels=12 "
              "invalid_state_and_false_difference_rejected=yes "
              "emulator_guest_proven=no original_game_proven=no");
    return 0;
 }catch(const std::exception& error){
    std::fprintf(stderr,"VPD_NATIVE_FOOTSTEP_HOST_FAIL %s\n",error.what());
    return 1;
 }
}
