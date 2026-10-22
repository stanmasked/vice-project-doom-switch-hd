#include "driving_road_private_bundle.hpp"
#include <array>
#include <cstdint>
#include <iostream>
#include <stdexcept>
using namespace vpd::private_road;
static void check(bool ok,const char* reason) {
    if(!ok)throw std::runtime_error(reason);
}
static void put16(std::uint8_t* x,std::uint16_t v) {
    x[0]=static_cast<std::uint8_t>(v);
    x[1]=static_cast<std::uint8_t>(v>>8);
}
static void put32(std::uint8_t* x,std::uint32_t v) {
    for(unsigned i=0;i<4;++i)x[i]=static_cast<std::uint8_t>(v>>(8*i));
}
using TestBundle=std::array<std::uint8_t,kBundleBytes>;
static void seal(TestBundle& raw) {
    put32(raw.data()+12,crc32(raw.data()+16,raw.size()-16));
}
static TestBundle makeSynthetic() {
    TestBundle data{};
    for(unsigned i=0;i<8;++i)data[i]=kMagic[i];
    put16(data.data()+8,1);
    put16(data.data()+10,kSamples);
    std::size_t index=0;
    for(std::uint16_t frame=600;frame<=920;frame+=8) {
        if(rejectedFrame(frame))continue;
        std::uint8_t left=66,right=188; // intentionally invented fixture
        if(const auto* s=vpd::road_reference::atExactFrame(frame)) {
            left=s->left;right=s->right;
        }
        auto* p=data.data()+kHeaderBytes+index*kRecordBytes;
        put16(p,frame);
        p[2]=left;p[3]=right;
        ++index;
    }
    check(index==37,"synthetic valid sample count wrong");
    seal(data);
    return data;
}
int main() {
    PrivateRoadBundle actual{};
    const auto good=makeSynthetic();
    check(!actual.loaded() && actual.count()==0 &&
          !actual.atExactFrame(600),"optional source loaded by default");
    check(!actual.loadFile(nullptr) &&
          !actual.loadFile("/unlikely/unused/private_road.vprd"),
          "missing private file must not enable source");
    check(actual.loadBytes(good.data(),good.size()),
          "complete validated synthetic source bundle rejected");
    check(actual.loaded() && actual.count()==37,"valid source count wrong");
    std::size_t seen=0;
    for(std::uint16_t frame=600;frame<=920;frame+=8) {
        const auto* s=actual.atExactFrame(frame);
        if(rejectedFrame(frame))check(s==nullptr,"ambiguous source inferred");
        else{
            check(s && s->frame==frame && s->width()>=30,
                  "exact real-index lookup incorrect");
            check(actual.byIndex(seen)==s,"source ordering corrupted");
            ++seen;
        }
    }
    check(seen==37 && actual.byIndex(37)==nullptr &&
          actual.atExactFrame(601)==nullptr &&
          actual.atExactFrame(0)==nullptr,
          "unknown movie frames extrapolated");
    auto corrupt=good;
    corrupt[16]^=1;
    check(!actual.loadBytes(corrupt.data(),corrupt.size()) &&
          !actual.loaded() && actual.atExactFrame(600)==nullptr,
          "CRC failure retained former private geometry");
    corrupt=good;
    corrupt[8]=2;seal(corrupt);
    check(!actual.loadBytes(corrupt.data(),corrupt.size()),"version check missing");
    corrupt=good;
    corrupt[10]=36;seal(corrupt);
    check(!actual.loadBytes(corrupt.data(),corrupt.size()),"count check missing");
    corrupt=good;
    put16(corrupt.data()+16,601);seal(corrupt);
    check(!actual.loadBytes(corrupt.data(),corrupt.size()),
          "unexpected movie-frame accepted");
    corrupt=good;
    corrupt[16+2]=99;seal(corrupt);
    check(!actual.loadBytes(corrupt.data(),corrupt.size()),
          "published original RGB anchor altered");
    corrupt=good;
    corrupt[16+3]=0;seal(corrupt);
    check(!actual.loadBytes(corrupt.data(),corrupt.size()),
          "source road coordinate reversed");
    corrupt=good;
    corrupt[0]='X';seal(corrupt);
    check(!actual.loadBytes(corrupt.data(),corrupt.size()),"magic not checked");
    check(!actual.loadBytes(good.data(),good.size()-1),
          "truncated source accepted");
    check(!actual.loadBytes(nullptr,good.size()),"null source accepted");
    check(actual.loadBytes(good.data(),good.size()),"reload after failure broken");
    actual.clear();
    check(!actual.loaded() && actual.count()==0,"private source state not cleared");
    std::cout<<"VPD_ROMFREE_PRIVATE_ROAD_BUNDLE_PASS"
             <<" synthetic_frames=37 rejected_ambiguities=4"
             <<" source_art=no camera_collision_proven=no\n";
}
