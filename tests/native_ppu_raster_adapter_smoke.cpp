// Stage97 ROM-free stand-alone C++ writer. No FCEUX link or data dependencies.
#include "fceux_native_ppu_raster_adapter.h"
#include <iostream>
#include <stdexcept>
#include <string>

using vice_raster::CandidateTrace;
using vice_raster::Kind;

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  try {
    const std::string mode = argv[1];
    CandidateTrace trace(std::cout);
    for (int frame = 0; frame < 2; ++frame) {
      trace.event(frame, 0, 0, Kind::Anchor);
      trace.event(frame, 10, 12, Kind::PixelSample);
      trace.event(frame, 60, 48, Kind::ChrContext);
      trace.event(frame, 130, 12, Kind::ScrollContext);
      if (mode == "out_of_bounds")
        trace.event(frame, 240, 44, Kind::PixelSample);
      if (mode == "duplicate_anchor")
        trace.event(frame, 130, 13, Kind::Anchor);
      if (mode == "bad_vblank")
        trace.event(frame, 241, 2, Kind::VblankEnter);
      else
        trace.event(frame, 241, 1, Kind::VblankEnter);
      if (mode != "missing_vblank")
        trace.event(frame, 261, 1, Kind::VblankExit);
    }
    trace.finish();
    return mode == "valid" ? 0 : 7;
  } catch (const std::exception& e) {
    std::cerr << e.what() << '\n';
    return 1;
  }
}
