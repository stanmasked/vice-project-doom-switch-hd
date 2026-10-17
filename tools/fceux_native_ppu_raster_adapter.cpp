// Candidate-only native PPU raster trace encoder for offline synthetic testing.
// A future FCEUX adapter must first independently normalize its own PPU
// scanline/dot phase and validate every edge; this code installs no hooks.
#include "fceux_native_ppu_raster_adapter.h"

#include <ostream>
#include <stdexcept>
#include <tuple>

namespace vice_raster {
namespace {
const char* name(Kind kind) {
  switch (kind) {
    case Kind::Anchor: return "frame_anchor";
    case Kind::PixelSample: return "pixel_fetch_sample";
    case Kind::ChrContext: return "chr_context";
    case Kind::ScrollContext: return "scroll_context";
    case Kind::PpuWrite: return "ppu_write";
    case Kind::VblankEnter: return "vblank_enter";
    case Kind::VblankExit: return "vblank_exit";
  }
  throw std::invalid_argument("unknown native raster event kind");
}
}  // namespace

CandidateTrace::CandidateTrace(std::ostream& out) : out_(out) {
  out_ << "frame\tscanline\tdot\tkind\n";
  if (!out_) throw std::runtime_error("failed writing trace header");
}

void CandidateTrace::finish_frame() const {
  if (anchors_ != 1 || enter_ != 1 || exit_ != 1)
    throw std::logic_error("incomplete candidate raster frame");
}

void CandidateTrace::event(int frame, int scanline, int dot, Kind kind) {
  if (frame < 0 || frame > 500000 || scanline < 0 || scanline > 261
      || dot < 0 || dot > 340)
    throw std::invalid_argument("raster sample outside bounded NTSC contract");
  const char* event_name = name(kind);
  if (frame_ < 0 || frame != frame_) {
    if (frame_ >= 0) {
      finish_frame();
      if (frame != frame_ + 1)
        throw std::logic_error("candidate frame labels not contiguous");
    }
    if (kind != Kind::Anchor || scanline != 0 || dot != 0)
      throw std::logic_error("candidate frame requires 0,0 anchor");
    frame_ = frame;
    ++frames_;
    anchors_ = enter_ = exit_ = 0;
    y_ = -1;
    dot_ = -1;
  }
  if (std::tie(scanline, dot) < std::tie(y_, dot_))
    throw std::logic_error("candidate PPU raster coordinates decreased");
  if (kind == Kind::Anchor) {
    if (++anchors_ != 1 || scanline != 0 || dot != 0)
      throw std::logic_error("duplicate or misplaced raster anchor");
  } else if (kind == Kind::VblankEnter) {
    if (++enter_ != 1 || exit_ != 0 || scanline != 241 || dot != 1)
      throw std::logic_error("invalid candidate VBlank entry");
  } else if (kind == Kind::VblankExit) {
    if (enter_ != 1 || ++exit_ != 1 || scanline != 261 || dot != 1)
      throw std::logic_error("invalid candidate VBlank exit");
  } else if (kind == Kind::PixelSample) {
    if (scanline > 239 || dot < 1 || dot > 256)
      throw std::logic_error("pixel sample outside visible raster");
  }
  out_ << frame << '\t' << scanline << '\t' << dot << '\t'
       << event_name << '\n';
  if (!out_) throw std::runtime_error("failed writing native trace event");
  ++events_;
  y_ = scanline;
  dot_ = dot;
}

void CandidateTrace::finish() const {
  if (frames_ == 0) throw std::logic_error("no candidate raster frames");
  finish_frame();
  if (!out_) throw std::runtime_error("native trace output stream failure");
}
}  // namespace vice_raster
