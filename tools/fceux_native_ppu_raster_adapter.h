// Stage97 prototype: no FCEUX linkage, no ROM reads or game data.
#pragma once
#include <cstddef>
#include <iosfwd>

namespace vice_raster {
enum class Kind { Anchor, PixelSample, ChrContext, ScrollContext, PpuWrite, VblankEnter, VblankExit };

class CandidateTrace {
 public:
  explicit CandidateTrace(std::ostream& out);
  void event(int frame, int scanline, int dot, Kind kind);
  void finish() const;
  std::size_t events() const { return events_; }
  int frames() const { return frames_; }
 private:
  std::ostream& out_;
  int frame_ = -1;
  int y_ = -1;
  int dot_ = -1;
  int frames_ = 0;
  int anchors_ = 0;
  int enter_ = 0;
  int exit_ = 0;
  std::size_t events_ = 0;
  void finish_frame() const;
};
}  // namespace vice_raster
