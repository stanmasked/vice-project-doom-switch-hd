#pragma once
// Optional Switch sdmc: smoke-test report. This is NOT an attestation:
// the operator must independently record which NRO/emulator was used.
#include "demo_witness.hpp"
#include <cstdio>
#include <sys/stat.h>

namespace vpd {
constexpr const char* kDemoWitnessPath=
    "sdmc:/switch/vice_project_doom/demo_witness.txt";
inline bool persistDemoWitness(const Simulation& game,unsigned cycle,
                               bool has_sd) {
    if(!has_sd || cycle==0 || cycle>kDemoWitnessMaxRecords)
        return false;
    // sdmc:/switch typically exists in a homebrew-capable SD image.
    // A missing directory, read-only SD or refused fopen cannot block play.
    (void)::mkdir("sdmc:/switch/vice_project_doom",0777);
    std::FILE* file=std::fopen(kDemoWitnessPath,"a");
    if(!file)return false;
    const bool wrote=writeDemoWitness(file,game,cycle);
    const int closed=std::fclose(file);
    return wrote && closed==0;
}
}
