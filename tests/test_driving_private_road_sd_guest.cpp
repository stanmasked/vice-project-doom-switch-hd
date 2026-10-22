#include "driving_private_road_sd_witness.hpp"
#include <array>
#include <cstdint>
#include <stdexcept>
#include <iostream>
using namespace vpd::private_road;
static void ok(bool valid,const char* reason) {
 if(!valid)throw std::runtime_error(reason);
}
static void put16(std::uint8_t* p,unsigned v){
 p[0]=static_cast<std::uint8_t>(v);
 p[1]=static_cast<std::uint8_t>(v>>8);
}
static void put32(std::uint8_t* p,std::uint32_t v){
 for(unsigned i=0;i<4;++i)p[i]=static_cast<std::uint8_t>(v>>(8*i));
}
int main(){
 PrivateRoadBundle empty;
 const auto offline=vpd::roadSdStartup(false,empty);
 ok(!offline.loaded && !offline.mounted && offline.count==0,
    "missing SD cannot enable measurements");
 const auto noFile=vpd::roadSdStartup(true,empty);
 ok(!noFile.loaded && noFile.mounted && noFile.count==0,
    "missing private bundle incorrectly reported loaded");
 std::array<std::uint8_t,kBundleBytes> bytes{};
 for(unsigned i=0;i<8;++i)bytes[i]=kMagic[i];
 put16(bytes.data()+8,1);put16(bytes.data()+10,37);
 unsigned count=0;
 for(unsigned frame=600;frame<=920;frame+=8){
   if(rejectedFrame(static_cast<std::uint16_t>(frame)))continue;
   auto* dst=bytes.data()+16+4*count++;
   put16(dst,frame);
   const auto* original=vpd::road_reference::atExactFrame(frame);
   dst[2]=original?original->left:66;
   dst[3]=original?original->right:188;
 }
 ok(count==37,"synthetic record count changed");
 put32(bytes.data()+12,crc32(bytes.data()+16,148));
 ok(empty.loadBytes(bytes.data(),bytes.size()),"synthetic source rejected");
 const auto good=vpd::roadSdStartup(true,empty);
 ok(good.loaded && good.count==37 && good.first_frame==600 &&
    good.last_frame==920,"guest startup report not from validated data");
 bytes[16]^=1;
 ok(!empty.loadBytes(bytes.data(),bytes.size()) &&
    !vpd::roadSdStartup(true,empty).loaded,
    "corrupted private numerical SD file retained guest success");
 std::cout<<"VPD_ROMFREE_ROAD_SD_STARTUP_PASS source=synthetic"
          <<" count=37 missing_file_inert=yes original_art=no\n";
}
