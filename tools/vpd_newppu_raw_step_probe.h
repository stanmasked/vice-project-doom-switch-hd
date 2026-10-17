// Stage98: optional internal newppu observations, NOT normalized NES raster.
// Header-only, no FCEUX dependencies; no file output and no implicit sink.
// Install callback explicitly only on a controlled private emulator build.
#ifndef VPD_NEWPPU_RAW_STEP_PROBE_H
#define VPD_NEWPPU_RAW_STEP_PROBE_H
#if defined(VPD_NATIVE_SYNTHETIC_SMOKE) || defined(VPD_NATIVE_SYNTHETIC_VBLANK) || defined(VPD_NATIVE_SYNTHETIC_PPUSTATUS_READ) || defined(VPD_NATIVE_SYNTHETIC_EVENT_ORDER) || defined(VPD_NATIVE_SYNTHETIC_PRECLEAR) || defined(VPD_NATIVE_SYNTHETIC_MMC3_CHR) || defined(VPD_NATIVE_SYNTHETIC_BG_PIXELS) || defined(VPD_NATIVE_SYNTHETIC_BG_FETCH) || defined(VPD_NATIVE_SYNTHETIC_CHR_TIMELINE) || defined(VPD_NATIVE_SYNTHETIC_MIDFRAME_CHR) || defined(VPD_NATIVE_SYNTHETIC_BG_TILES) || defined(VPD_NATIVE_SYNTHETIC_BG_PREFETCH) || defined(VPD_NATIVE_SYNTHETIC_BG_PLANE_PAIRS)
#include <cstdio>
#include <cstdlib>
#include <cstring>
#endif

namespace vpd_ppu_probe {
struct RawStep {
    int internal_scanline;
    int cycle_before;
    int cycle_after;
    int cycle_modulus;
    int increment;
};
typedef void (*Sink)(const RawStep&, void*);

struct Channel {
    Sink callback = nullptr;
    void* user = nullptr;
    unsigned long observed = 0;
    unsigned long long internal_tick_units = 0;
    unsigned long invalid = 0;
    unsigned long zero_advance_calls = 0;
};

inline Channel& channel() {
    static Channel instance;
    return instance;
}

inline void set_sink(Sink callback, void* user) {
    Channel& c = channel();
    c.callback = callback;
    c.user = user;
}

// Stage100: synthetic-only, double-opt-in aggregate witness; no raw positions.
#ifdef VPD_NATIVE_SYNTHETIC_SMOKE
inline void smoke_callback(const RawStep& step, void*) {
    struct Aggregate {
        unsigned long count = 0;
        unsigned long wrapped = 0;
        unsigned long label_changes = 0;
        int previous_label = -1;
        bool emitted = false;
    };
    static Aggregate aggregate;
    if (aggregate.emitted) return;
    ++aggregate.count;
    if (step.cycle_after < step.cycle_before) ++aggregate.wrapped;
    if (aggregate.previous_label >= 0 &&
        aggregate.previous_label != step.internal_scanline)
        ++aggregate.label_changes;
    aggregate.previous_label = step.internal_scanline;
    if (aggregate.count == 8192) {
        std::fprintf(stderr,
            "VPD_STAGE100_NEWPPU_RUNTIME_PASS raw_steps=8192 "
            "cycle_wraps=%lu internal_label_changes=%lu "
            "invalid_steps=%lu zero_advance_calls=%lu "
            "normalized_scanlines=no real_game_data=no\n",
            aggregate.wrapped, aggregate.label_changes,
            channel().invalid, channel().zero_advance_calls);
        std::fflush(stderr);
        aggregate.emitted = true;
        set_sink(nullptr, nullptr);
    }
}
inline void arm_synthetic_smoke_once() {
    static bool checked = false;
    if (checked) return;
    checked = true;
    const char* opt_in = std::getenv("VPD_STAGE100_SYNTHETIC_SMOKE");
    if (opt_in && std::strcmp(opt_in, "1") == 0)
        set_sink(smoke_callback, nullptr);
}
#endif

inline void observe(int sl, int before, int after, int modulus, int increment) {
    Channel& c = channel();
    // Verifies internal modulo arithmetic only; no PPU scanline semantics.
    if (sl < 0 || modulus <= 0 || increment < 0 ||
        before < 0 || before >= modulus ||
        after < 0 || after >= modulus ||
        static_cast<long long>(after) !=
            (static_cast<long long>(before) + increment) % modulus) {
        ++c.invalid;
        return;
    }
    if (increment == 0) {
        // FCEUX newppu invokes runppu(garbage_todo) even when 0;
        // it is not an advancing PPU tick nor a malformed callback.
        ++c.zero_advance_calls;
        return;
    }
    ++c.observed;
    c.internal_tick_units += static_cast<unsigned long long>(increment);
#ifdef VPD_NATIVE_SYNTHETIC_SMOKE
    arm_synthetic_smoke_once();
#endif
    if (c.callback) {
        const RawStep step{sl, before, after, modulus, increment};
        c.callback(step, c.user);
    }
}


// Stage104: source-level sequence relative to the same advancing runppu clock.
// No scanline/dot, ROM, register byte or original-game information is emitted.
// These are emulator-assigned status windows, NOT physical NES VBlank timings.
#ifdef VPD_NATIVE_SYNTHETIC_EVENT_ORDER
struct EventOrderState {
    unsigned long source_entries = 0;
    unsigned long source_clears = 0;
    unsigned long cpu_reads = 0;
    unsigned long high_reads = 0;
    unsigned long high_read_clears = 0;
    unsigned long high_within_window = 0;
    unsigned long low_after_high = 0;
    unsigned long invalid = 0;
    unsigned long long current_entry_tick = 0;
    unsigned long long high_lag_min = 0;
    unsigned long long high_lag_max = 0;
    bool source_window = false;
    bool high_read_this_window = false;
    bool emitted = false;
};

inline EventOrderState& event_order_state() {
    static EventOrderState state;
    return state;
}

inline bool event_order_enabled() {
    static const char* opt = std::getenv("VPD_STAGE104_EVENT_ORDER_PROBE");
    return opt && std::strcmp(opt, "1") == 0;
}

inline void event_order_assignment(bool entering, bool bit_after) {
    if (!event_order_enabled()) return;
    EventOrderState& e = event_order_state();
    if (e.emitted) return;
    const unsigned long long tick = channel().internal_tick_units;
    if (entering) {
        if (!bit_after || e.source_window) ++e.invalid;
        ++e.source_entries;
        e.current_entry_tick = tick;
        e.source_window = true;
        e.high_read_this_window = false;
    } else {
        if (bit_after || !e.source_window) ++e.invalid;
        ++e.source_clears;
        e.source_window = false;
        e.high_read_this_window = false;
    }
}

inline void event_order_read(bool returned_high, bool before_high,
                             bool after_high) {
    if (!event_order_enabled()) return;
    EventOrderState& e = event_order_state();
    if (e.emitted) return;
    ++e.cpu_reads;
    if (returned_high != before_high || after_high) ++e.invalid;
    if (before_high) {
        ++e.high_reads;
        if (!after_high) ++e.high_read_clears;
        if (e.source_window) {
            ++e.high_within_window;
            if (e.high_read_this_window) ++e.invalid;
            e.high_read_this_window = true;
        } else {
            ++e.invalid;
        }
        const unsigned long long now = channel().internal_tick_units;
        if (now < e.current_entry_tick || e.source_entries == 0) {
            ++e.invalid;
        } else {
            const unsigned long long lag = now - e.current_entry_tick;
            if (e.high_reads == 1 || lag < e.high_lag_min) e.high_lag_min = lag;
            if (lag > e.high_lag_max) e.high_lag_max = lag;
        }
    } else if (e.source_window && e.high_read_this_window) {
        ++e.low_after_high;
    }
    if (e.cpu_reads == 16384) {
        std::fprintf(stderr,
            "VPD_STAGE104_NATIVE_EVENT_ORDER_PASS reads=16384 "
            "source_entries=%lu source_clears=%lu "
            "high_reads=%lu high_read_clears=%lu "
            "high_within_window=%lu low_after_high=%lu "
            "high_lag_min=%llu high_lag_max=%llu invalid=%lu "
            "source_timeline_only=yes physical_vblank_proven=no\n",
            e.source_entries, e.source_clears, e.high_reads,
            e.high_read_clears, e.high_within_window, e.low_after_high,
            e.high_lag_min, e.high_lag_max, e.invalid);
        std::fflush(stderr);
        e.emitted = true;
    }
}
#endif


// Stage105: independent pre-clear status snapshot. These are software source
// callbacks, never NES hardware PPUSTATUS samples or pixel observations.
#ifdef VPD_NATIVE_SYNTHETIC_PRECLEAR
struct PreclearState {
    unsigned long sets = 0, clears = 0, pre_calls = 0, reads = 0;
    unsigned long high_reads = 0, read_clears = 0, low_after_high = 0;
    unsigned long pre_low_after_high = 0, pre_high_after_high = 0;
    unsigned long pre_high_no_read = 0, pre_low_no_read = 0;
    unsigned long invalid = 0;
    unsigned long long last_high_tick = 0, lag_min = 0, lag_max = 0;
    unsigned long long last_pre_tick = 0;
    bool window = false, high_this_window = false, pre_seen = false;
    bool emitted = false;
};

inline PreclearState& preclear_state() {
    static PreclearState s;
    return s;
}

inline bool preclear_enabled() {
    static const char* opt = std::getenv("VPD_STAGE105_PRECLEAR_PROBE");
    return opt && std::strcmp(opt, "1") == 0;
}

inline void preclear_source_assignment(bool entering, bool after_high) {
    if (!preclear_enabled()) return;
    PreclearState& s = preclear_state();
    if (s.emitted) return;
    if (entering) {
        if (s.window || !after_high) ++s.invalid;
        ++s.sets;
        s.window = true;
        s.high_this_window = false;
        s.pre_seen = false;
    } else {
        if (!s.window || !s.pre_seen || after_high ||
            s.last_pre_tick != channel().internal_tick_units)
            ++s.invalid;
        ++s.clears;
        s.window = false;
        s.high_this_window = false;
        s.pre_seen = false;
    }
}

inline void preclear_before_assignment(bool before_high) {
    if (!preclear_enabled()) return;
    PreclearState& s = preclear_state();
    if (s.emitted) return;
    ++s.pre_calls;
    if (!s.window || s.pre_seen) ++s.invalid;
    s.pre_seen = true;
    s.last_pre_tick = channel().internal_tick_units;
    if (s.high_this_window) {
        if (before_high) {
            ++s.pre_high_after_high;
            ++s.invalid;
        } else {
            ++s.pre_low_after_high;
        }
        if (s.last_pre_tick < s.last_high_tick) {
            ++s.invalid;
        } else {
            unsigned long long lag = s.last_pre_tick - s.last_high_tick;
            if (s.pre_low_after_high + s.pre_high_after_high == 1 ||
                lag < s.lag_min) s.lag_min = lag;
            if (lag > s.lag_max) s.lag_max = lag;
        }
    } else if (before_high) {
        ++s.pre_high_no_read;
    } else {
        ++s.pre_low_no_read;
    }
}

inline void preclear_cpu_read(bool returned_high, bool before_high,
                               bool after_high) {
    if (!preclear_enabled()) return;
    PreclearState& s = preclear_state();
    if (s.emitted) return;
    ++s.reads;
    if (returned_high != before_high || after_high) ++s.invalid;
    if (before_high) {
        ++s.high_reads;
        if (!after_high) ++s.read_clears;
        if (!s.window || s.high_this_window || s.pre_seen) ++s.invalid;
        s.high_this_window = true;
        s.last_high_tick = channel().internal_tick_units;
    } else if (s.window && s.high_this_window) {
        ++s.low_after_high;
    }
    if (s.reads == 16384) {
        std::fprintf(stderr,
            "VPD_STAGE105_NATIVE_PRECLEAR_PASS reads=16384 "
            "sets=%lu clears=%lu pre_calls=%lu high_reads=%lu "
            "read_clears=%lu low_after_high=%lu "
            "pre_low_after_high=%lu pre_high_after_high=%lu "
            "pre_high_no_read=%lu pre_low_no_read=%lu "
            "high_to_pre_min=%llu high_to_pre_max=%llu invalid=%lu "
            "source_only=yes hardware_vblank_proven=no\n",
            s.sets, s.clears, s.pre_calls, s.high_reads,
            s.read_clears, s.low_after_high, s.pre_low_after_high,
            s.pre_high_after_high, s.pre_high_no_read, s.pre_low_no_read,
            s.lag_min, s.lag_max, s.invalid);
        std::fflush(stderr);
        s.emitted = true;
    }
}
#endif

// Stage110: synthetic mid-frame real MMC3 write and final FCEUX framebuffer bytes.
// A single rendered frame must have both blank and filled sample windows.
#ifdef VPD_NATIVE_SYNTHETIC_MIDFRAME_CHR
struct MidframeChr {
    unsigned writes = 0, last_sl = 0, switch_sl = 0;
    unsigned long frame = 0, switch_frame = 0;
    unsigned pre = 0, post = 0, pre_zero = 0, post_three = 0;
    unsigned long invalid = 0;
    unsigned long long pre_hash = 14695981039346656037ULL;
    unsigned long long post_hash = 14695981039346656037ULL;
    unsigned long long switch_tick = 0;
    bool switched = false, emitted = false;
};
inline MidframeChr& stage110_state() {
    static MidframeChr state;
    return state;
}
inline bool stage110_enabled() {
    static const char* opt = std::getenv("VPD_STAGE110_MIDFRAME_CHR_PROBE");
    return opt && std::strcmp(opt, "1") == 0;
}
inline void stage110_register_write(unsigned selector, unsigned value) {
    if (!stage110_enabled()) return;
    MidframeChr& s = stage110_state();
    if (s.emitted) return;
    ++s.writes;
    if (selector != 2 || s.writes > 2 || value != (s.writes == 1 ? 0U : 1U))
        ++s.invalid;
    if (s.writes == 2) {
        s.switched = true;
        s.switch_frame = s.frame;
        s.switch_sl = s.last_sl;
        s.switch_tick = channel().internal_tick_units;
        if (s.switch_sl < 40 || s.switch_sl > 210 || s.pre < 2048)
            ++s.invalid;
        std::fprintf(stderr,
            "VPD_STAGE110_DIAGNOSTIC switch_sl=%u pre_pixels=%u invalid=%lu "
            "synthetic_only=yes\n",
            s.switch_sl, s.pre, s.invalid);
        std::fflush(stderr);
    }
}
inline void stage110_raster_pixel(unsigned sl, unsigned pattern, unsigned color) {
    if (!stage110_enabled()) return;
    MidframeChr& s = stage110_state();
    if (s.emitted) return;
    if (sl < 1 || sl > 240 || pattern > 3 || color > 255) {
        ++s.invalid;
        return;
    }
    if (sl < s.last_sl) {
        ++s.frame;
        if (s.switched && s.switch_frame != s.frame) ++s.invalid;
        if (!s.switched) {
            s.pre = s.pre_zero = 0;
            s.pre_hash = 14695981039346656037ULL;
        }
    }
    s.last_sl = sl;
    if (s.writes == 1 && !s.switched && s.pre < 2048) {
        ++s.pre;
        if (pattern == 0) ++s.pre_zero;
        else ++s.invalid;
        s.pre_hash = (s.pre_hash ^ static_cast<unsigned long long>(color)) *
            1099511628211ULL;
    }
    if (s.switched && s.frame == s.switch_frame &&
        sl >= s.switch_sl + 4 && s.post < 2048) {
        ++s.post;
        if (pattern == 3) ++s.post_three;
        else ++s.invalid;
        s.post_hash = (s.post_hash ^ static_cast<unsigned long long>(color)) *
            1099511628211ULL;
        if (s.post == 2048) {
            if (s.writes != 2 || s.pre != 2048 || s.pre_zero != 2048 ||
                s.post_three != 2048 || s.pre_hash == s.post_hash)
                ++s.invalid;
            if (s.invalid != 0) {
                std::fprintf(stderr,
                    "VPD_STAGE110_REJECTED_CONTROL invalid=%lu synthetic_only=yes\n",
                    s.invalid);
                std::fflush(stderr);
                s.emitted = true;
                return;
            }
            std::fprintf(stderr,
                "VPD_STAGE110_NATIVE_MIDFRAME_CHR_PASS "
                "writes=%u switch_sl=%u pre_pixels=%u post_pixels=%u "
                "pre_zero=%u post_three=%u pre_fnv64=%llu post_fnv64=%llu "
                "invalid=%lu same_native_frame=yes synthetic_only=yes "
                "original_game_raster_proven=no\n",
                s.writes, s.switch_sl, s.pre, s.post,
                s.pre_zero, s.post_three, s.pre_hash, s.post_hash, s.invalid);
            std::fflush(stderr);
            s.emitted = true;
        }
    }
}
#endif

// Stage111: observe buffer values ACTUALLY CONSUMED by newppu pixels.
// Private synthetic ROM only. Do not confuse earlier fetches with buffered
// pattern data; this callback receives bgdata.main[bgtile].pt[0/1].
#if defined(VPD_NATIVE_SYNTHETIC_BG_TILES) && defined(VPD_NATIVE_SYNTHETIC_MIDFRAME_CHR)
struct TileBoundary {
    unsigned long pre = 0, pre_zero = 0, transient_old = 0;
    unsigned long filled = 0, filled_ok = 0, regression = 0, invalid = 0;
    unsigned long frame = 0;
    unsigned last_sl = 0, last_xt = 0, switch_xt = 0;
    unsigned first_new_sl = 0, first_new_xt = 0;
    bool switched_seen = false, new_seen = false, emitted = false;
};
inline TileBoundary& stage111_state() {
    static TileBoundary t;
    return t;
}
inline bool stage111_enabled() {
    static const char* env = std::getenv("VPD_STAGE111_BG_TILE_PROBE");
    return env && std::strcmp(env, "1") == 0;
}
inline void stage111_tile_pixel(unsigned sl, unsigned xt, unsigned xp,
                                unsigned index, unsigned lo,
                                unsigned hi, unsigned pattern) {
    if (!stage111_enabled() || xp != 0) return;
    TileBoundary& t = stage111_state();
    MidframeChr& m = stage110_state();
    if (t.emitted) return;
    if (sl < 1 || sl > 240 || xt >= 32 || index >= 34 ||
        lo > 255 || hi > 255 || pattern > 3 ||
        (sl == t.last_sl && xt <= t.last_xt)) ++t.invalid;
    if (t.frame != m.frame && !m.switched) {
        t.frame = m.frame;
        t.pre = t.pre_zero = 0;
        t.switched_seen = t.new_seen = false;
        t.transient_old = t.filled = t.filled_ok = t.regression = 0;
    }
    if (m.writes == 1 && !m.switched && t.pre < 128) {
        ++t.pre;
        if (lo == 0 && hi == 0 && pattern == 0) ++t.pre_zero;
        else ++t.invalid;
    }
    if (m.writes == 2 && m.switched && !t.switched_seen) {
        t.switched_seen = true;
        t.switch_xt = t.last_xt;
        if (t.frame != m.switch_frame || t.pre != 128 ||
            t.pre_zero != 128 || sl < m.switch_sl ||
            sl > m.switch_sl + 1 || m.switch_sl < 40 ||
            m.switch_sl > 210) ++t.invalid;
    }
    if (t.switched_seen && m.writes == 2 && m.frame == m.switch_frame &&
        t.filled < 128) {
        if (lo == 0 && hi == 0 && pattern == 0) {
            if (t.new_seen) ++t.regression;
            else ++t.transient_old;
        } else if (lo == 255 && hi == 255 && pattern == 3) {
            if (!t.new_seen) {
                t.new_seen = true;
                t.first_new_sl = sl;
                t.first_new_xt = xt;
            }
            ++t.filled;
            ++t.filled_ok;
        } else {
            ++t.invalid;
        }
    }
    t.last_sl = sl;
    t.last_xt = xt;
    if (t.filled == 128 && !t.emitted) {
        if (!t.new_seen || t.first_new_sl < m.switch_sl ||
            t.first_new_sl > m.switch_sl + 3 ||
            t.transient_old > 64 || t.regression != 0 ||
            t.pre != 128 || t.pre_zero != 128 ||
            t.filled_ok != 128 || m.frame != m.switch_frame ||
            m.writes != 2) ++t.invalid;
        if (t.invalid) {
            std::fprintf(stderr,
                "VPD_STAGE111_REJECTED_TILE_BOUNDARY invalid=%lu "
                "transient_old=%lu regressions=%lu synthetic_only=yes\n",
                t.invalid, t.transient_old, t.regression);
        } else {
            std::fprintf(stderr,
                "VPD_STAGE111_NATIVE_TILE_BOUNDARY_PASS "
                "switch_sl=%u last_rendered_xt=%u "
                "pre_tiles=128 pre_zero=128 transient_old=%lu "
                "first_new_sl=%u first_new_xt=%u "
                "new_tiles=128 new_ff=128 regressions=0 invalid=0 "
                "same_rendered_frame=yes synthetic_only=yes "
                "original_game_tile_proven=no\n",
                m.switch_sl, t.switch_xt, t.transient_old,
                t.first_new_sl, t.first_new_xt);
        }
        std::fflush(stderr);
        t.emitted = true;
    }
}
#endif

// Stage113: bounded provenance of buffered 8-pixel tile records actually
// prefetched by BGData::Record::Read. Source-clock values are NOT PPU dots.
#if defined(VPD_NATIVE_SYNTHETIC_BG_PREFETCH) && defined(VPD_NATIVE_SYNTHETIC_BG_TILES) && defined(VPD_NATIVE_SYNTHETIC_MIDFRAME_CHR)
struct PrefetchRecord {
    unsigned sl = 0, lo = 0, hi = 0;
    unsigned long long start = 0, end = 0;
    bool begun = false, valid = false;
};
struct PrefetchAggregate {
    PrefetchRecord records[34];
    unsigned long matched_old = 0, matched_new = 0;
    unsigned long old_after_write = 0, old_started_before = 0;
    unsigned long old_started_after = 0, new_started_after = 0;
    unsigned long invalid = 0;
    unsigned long long lag_min = 0, lag_max = 0;
    unsigned first_sl = 0, first_xt = 0;
    bool saw_new = false, emitted = false;
};
inline PrefetchAggregate& stage113_state() {
    static PrefetchAggregate a;
    return a;
}
inline bool stage113_enabled() {
    static const char* env = std::getenv("VPD_STAGE113_BG_PREFETCH_PROBE");
    return env && std::strcmp(env, "1") == 0;
}
inline void stage113_begin(unsigned sl, unsigned slot) {
    if (!stage113_enabled()) return;
    PrefetchAggregate& a = stage113_state();
    if (a.emitted) return;
    if (sl > 240 || slot < 2 || slot >= 34) { ++a.invalid; return; }
    PrefetchRecord& r = a.records[slot];
    r.sl = sl;
    r.start = channel().internal_tick_units;
    r.begun = true;
    r.valid = false;
}
inline void stage113_end(unsigned sl, unsigned slot, unsigned lo, unsigned hi) {
    if (!stage113_enabled()) return;
    PrefetchAggregate& a = stage113_state();
    if (a.emitted) return;
    if (sl > 240 || slot < 2 || slot >= 34 || lo > 255 || hi > 255) {
        ++a.invalid;
        return;
    }
    PrefetchRecord& r = a.records[slot];
    r.end = channel().internal_tick_units;
    if (!r.begun || r.sl != sl || r.end < r.start) ++a.invalid;
    r.lo = lo;
    r.hi = hi;
    r.valid = true;
}
inline void stage113_draw(unsigned sl, unsigned xt, unsigned xp,
                          unsigned index, unsigned lo, unsigned hi) {
    if (!stage113_enabled() || xp != 0 || xt < 2) return;
    PrefetchAggregate& a = stage113_state();
    MidframeChr& m = stage110_state();
    if (a.emitted) return;
    if (sl < 1 || sl > 240 || xt >= 32 || index != xt ||
        lo > 255 || hi > 255) { ++a.invalid; return; }
    PrefetchRecord& r = a.records[index];
    const unsigned long long now = channel().internal_tick_units;
    if (!r.valid || r.sl != sl || r.lo != lo || r.hi != hi ||
        r.end > now) { ++a.invalid; return; }
    if (m.writes == 1 && !m.switched) {
        if (a.matched_old < 128) {
            ++a.matched_old;
            if (lo != 0 || hi != 0) ++a.invalid;
        }
    } else if (m.writes == 2 && m.switched &&
               m.switch_frame == m.frame && sl >= m.switch_sl) {
        if (lo == 0 && hi == 0 && !a.saw_new) {
            ++a.old_after_write;
            if (r.start < m.switch_tick) ++a.old_started_before;
            else ++a.old_started_after;
        } else if (lo == 255 && hi == 255) {
            if (!a.saw_new) {
                a.saw_new = true;
                a.first_sl = sl;
                a.first_xt = xt;
            }
            if (a.matched_new < 128) {
                ++a.matched_new;
                if (r.start >= m.switch_tick) ++a.new_started_after;
                else ++a.invalid;
                const unsigned long long lag = now - r.end;
                if (a.matched_new == 1 || lag < a.lag_min) a.lag_min = lag;
                if (lag > a.lag_max) a.lag_max = lag;
            }
        } else {
            ++a.invalid;
        }
    }
    if (a.matched_new == 128 && !a.emitted) {
        const TileBoundary& t = stage111_state();
        if (a.matched_old != 128 || a.old_after_write != t.transient_old ||
            a.old_after_write > 64 ||
            a.old_started_before + a.old_started_after != a.old_after_write ||
            a.new_started_after != 128 ||
            a.first_sl != t.first_new_sl ||
            a.first_xt != t.first_new_xt ||
            a.first_sl < m.switch_sl || a.first_sl > m.switch_sl + 3 ||
            a.lag_min == 0 || a.lag_max < a.lag_min ||
            a.lag_max > 1000000ULL || t.invalid != 0)
            ++a.invalid;
        if (a.invalid) {
            std::fprintf(stderr,
                "VPD_STAGE113_REJECTED_PREFETCH invalid=%lu "
                "matched_old=%lu matched_new=%lu synthetic_only=yes\n",
                a.invalid, a.matched_old, a.matched_new);
        } else {
            std::fprintf(stderr,
                "VPD_STAGE113_NATIVE_PREFETCH_PASS "
                "switch_sl=%u first_new_sl=%u first_new_xt=%u "
                "lookahead_tiles=2 matched_old=128 matched_new=128 "
                "old_after_write=%lu old_prefetched_before=%lu "
                "old_read_started_after=%lu new_read_started_after=128 "
                "fetch_to_draw_min=%llu fetch_to_draw_max=%llu invalid=0 "
                "paired_tile_xbuf_frame=yes synthetic_only=yes "
                "original_game_prefetch_proven=no\n",
                m.switch_sl, a.first_sl, a.first_xt, a.old_after_write,
                a.old_started_before, a.old_started_after,
                a.lag_min, a.lag_max);
        }
        std::fflush(stderr);
        a.emitted = true;
    }
}
#endif

// Stage114: verify BOTH low and high CHR plane bytes actually read by newppu
// for the buffer that was later used to produce a rendered background tile.
// Classification is specific to generated all-0 / all-FF synthetic CHR ROM.
#if defined(VPD_NATIVE_SYNTHETIC_BG_PLANE_PAIRS) && defined(VPD_NATIVE_SYNTHETIC_MIDFRAME_CHR)
struct NativePlaneRecord {
    unsigned sl = 0, slot = 0, lo = 0, hi = 0;
    unsigned addr0 = 0, addr1 = 0, epoch0 = 0, epoch1 = 0;
    unsigned long long tick0 = 0, tick1 = 0;
    bool low = false, high = false, complete = false;
};
struct PlanePairAudit {
    NativePlaneRecord records[34];
    unsigned active_slot = 0;
    bool active = false, emitted = false;
    unsigned long old_tiles = 0, new_tiles = 0, mixed_pairs = 0;
    unsigned long split_writes = 0, invalid = 0;
    unsigned long long min_gap = 0, max_gap = 0;
};
inline PlanePairAudit& stage114_state() {
    static PlanePairAudit a;
    return a;
}
inline bool stage114_enabled() {
    static const char* env = std::getenv("VPD_STAGE114_PLANE_PAIR_PROBE");
    return env && std::strcmp(env,"1") == 0;
}
inline void stage114_begin(unsigned sl, unsigned slot) {
    if (!stage114_enabled()) return;
    PlanePairAudit& a = stage114_state();
    a.active = !a.emitted && sl >= 1 && sl <= 240 &&
               slot >= 2 && slot < 34;
    if (!a.active) return;
    a.active_slot = slot;
    NativePlaneRecord& r = a.records[slot];
    r = NativePlaneRecord();
    r.sl = sl;
    r.slot = slot;
}
inline void stage114_plane(unsigned plane, unsigned address, unsigned value) {
    if (!stage114_enabled()) return;
    PlanePairAudit& a = stage114_state();
    if (!a.active || a.emitted) return;
    NativePlaneRecord& r = a.records[a.active_slot];
    if (plane > 1 || address < 0x1000 || address >= 0x2000 || value > 255) {
        ++a.invalid; return;
    }
    if (plane == 0) {
        if (r.low || r.high) ++a.invalid;
        r.low = true;
        r.lo = value;
        r.addr0 = address;
        r.tick0 = channel().internal_tick_units;
        r.epoch0 = stage110_state().writes;
    } else {
        if (!r.low || r.high) ++a.invalid;
        r.high = true;
        r.hi = value;
        r.addr1 = address;
        r.tick1 = channel().internal_tick_units;
        r.epoch1 = stage110_state().writes;
    }
}
inline void stage114_end(unsigned sl, unsigned slot, unsigned lo, unsigned hi) {
    if (!stage114_enabled()) return;
    PlanePairAudit& a = stage114_state();
    if (!a.active || a.emitted) return;
    NativePlaneRecord& r = a.records[a.active_slot];
    if (slot != a.active_slot || sl != r.sl || !r.low || !r.high ||
        r.lo != lo || r.hi != hi || r.addr1 != (r.addr0 | 8) ||
        r.addr0 >= 0x2000 || r.tick1 <= r.tick0 ||
        r.tick1 - r.tick0 > 8) ++a.invalid;
    r.complete = true;
    a.active = false;
}
inline void stage114_draw(unsigned sl, unsigned xt, unsigned xp,
                          unsigned slot, unsigned lo, unsigned hi) {
    if (!stage114_enabled() || xp != 0 || xt < 2) return;
    PlanePairAudit& a = stage114_state();
    MidframeChr& m = stage110_state();
    if (a.emitted) return;
    if (slot != xt || xt >= 32 || sl < 1 || sl > 240) {
        ++a.invalid; return;
    }
    NativePlaneRecord& r = a.records[slot];
    if (!r.complete || r.sl != sl || r.lo != lo || r.hi != hi ||
        r.tick1 > channel().internal_tick_units) {
        ++a.invalid; return;
    }
    const bool zero = lo == 0 && hi == 0;
    const bool filled = lo == 255 && hi == 255;
    const bool mixed = (lo == 0 && hi == 255) ||
                       (lo == 255 && hi == 0);
    if (m.writes == 1 && !m.switched && a.old_tiles < 128) {
        ++a.old_tiles;
        if (!zero || r.epoch0 != 1 || r.epoch1 != 1) ++a.invalid;
    }
    if (m.writes == 2 && m.switched &&
        m.switch_frame == m.frame && sl >= m.switch_sl) {
        if (mixed) ++a.mixed_pairs;
        if (r.epoch0 != r.epoch1) ++a.split_writes;
        if (filled && a.new_tiles < 128) {
            ++a.new_tiles;
            if (r.epoch0 != 2 || r.epoch1 != 2) ++a.invalid;
            const unsigned long long gap = r.tick1 - r.tick0;
            if (a.new_tiles == 1 || gap < a.min_gap) a.min_gap = gap;
            if (gap > a.max_gap) a.max_gap = gap;
        } else if (!zero && !mixed && !filled) {
            ++a.invalid;
        }
    }
    if (a.new_tiles == 128) {
        if (a.old_tiles != 128 || a.mixed_pairs != 0 ||
            a.split_writes != 0 || a.min_gap == 0 ||
            a.max_gap < a.min_gap || a.max_gap > 8) ++a.invalid;
        if (a.invalid) {
            std::fprintf(stderr,
                "VPD_STAGE114_REJECTED_PLANE_PAIR invalid=%lu "
                "mixed=%lu split=%lu synthetic_only=yes\n",
                a.invalid, a.mixed_pairs, a.split_writes);
        } else {
            std::fprintf(stderr,
                "VPD_STAGE114_NATIVE_PLANE_PAIR_PASS "
                "switch_sl=%u old_tiles=128 new_tiles=128 "
                "mixed_pairs=0 writes_between_planes=0 "
                "low_to_high_min=%llu low_to_high_max=%llu "
                "source_clock_only=yes pinned_fceux_only=yes "
                "synthetic_only=yes original_game_mixed_tiles_proven=no\n",
                m.switch_sl, a.min_gap, a.max_gap);
        }
        std::fflush(stderr);
        a.emitted = true;
    }
}
#endif

// Stage109 synthetic-only MMC3 write -> BG CHR read -> framebuffer timeline.
// Internal runppu tick units are not authoritative NTSC dots or CPU cycles.
#ifdef VPD_NATIVE_SYNTHETIC_CHR_TIMELINE
struct ChrChronology {
    unsigned long writes = 0, fetches = 0, pixels = 0, invalid = 0;
    unsigned chosen_bank = 0;
    unsigned long long write_tick = 0, first_fetch_tick = 0;
    unsigned long long first_pixel_tick = 0, last_fetch_tick = 0;
    unsigned long long last_pixel_tick = 0;
    bool emitted = false;
};
inline ChrChronology& chr_chronology() {
    static ChrChronology c;
    return c;
}
inline bool chr_chronology_enabled() {
    static const char* enabled = std::getenv("VPD_STAGE109_CHR_TIMELINE_PROBE");
    return enabled && std::strcmp(enabled, "1") == 0;
}
inline void chr_chronology_try_emit() {
    ChrChronology& c = chr_chronology();
    if (c.emitted || c.fetches < 8192 || c.pixels < 32768) return;
    const unsigned long long first_fetch_lag =
        c.first_fetch_tick >= c.write_tick ? c.first_fetch_tick - c.write_tick : 0;
    const unsigned long long fetch_to_pixel_lag =
        c.first_pixel_tick >= c.first_fetch_tick ?
            c.first_pixel_tick - c.first_fetch_tick : 0;
    const unsigned long long write_to_last_pixel_lag =
        c.last_pixel_tick >= c.write_tick ? c.last_pixel_tick - c.write_tick : 0;
    if (c.writes != 1 || c.first_fetch_tick < c.write_tick ||
        c.first_pixel_tick < c.first_fetch_tick ||
        c.last_pixel_tick < c.first_pixel_tick ||
        write_to_last_pixel_lag < first_fetch_lag ||
        first_fetch_lag > 1000000ULL || fetch_to_pixel_lag > 1000000ULL ||
        write_to_last_pixel_lag > 1000000ULL) ++c.invalid;
    std::fprintf(stderr,
        "VPD_STAGE109_NATIVE_CHR_TIMELINE_PASS writes=%lu fetches=%lu "
        "pixels=%lu bank=%u first_fetch_lag=%llu "
        "first_pixel_after_fetch_lag=%llu last_pixel_after_write_lag=%llu "
        "invalid=%lu synthetic_only=yes original_game_timing_proven=no\n",
        c.writes, c.fetches, c.pixels, c.chosen_bank,
        first_fetch_lag, fetch_to_pixel_lag, write_to_last_pixel_lag,
        c.invalid);
    std::fflush(stderr);
    c.emitted = true;
}
inline void chr_chronology_write(unsigned selector, unsigned bank) {
    if (!chr_chronology_enabled()) return;
    ChrChronology& c = chr_chronology();
    if (c.emitted) return;
    if (selector != 2 || bank > 1 || c.writes != 0 ||
        c.fetches != 0 || c.pixels != 0) ++c.invalid;
    ++c.writes;
    c.chosen_bank = bank;
    c.write_tick = channel().internal_tick_units;
}
inline void chr_chronology_fetch(unsigned addr, unsigned byte) {
    if (!chr_chronology_enabled()) return;
    ChrChronology& c = chr_chronology();
    if (c.emitted || c.fetches >= 8192) return;
    const unsigned long long now = channel().internal_tick_units;
    if (c.writes != 1 || now < c.write_tick ||
        (c.fetches > 0 && now < c.last_fetch_tick) ||
        addr < 0x1000 || addr >= 0x2000 ||
        byte != (c.chosen_bank ? 255U : 0U)) ++c.invalid;
    if (c.fetches == 0) c.first_fetch_tick = now;
    c.last_fetch_tick = now;
    ++c.fetches;
    chr_chronology_try_emit();
}
inline void chr_chronology_pixel(unsigned pattern) {
    if (!chr_chronology_enabled()) return;
    ChrChronology& c = chr_chronology();
    if (c.emitted || c.pixels >= 32768) return;
    const unsigned long long now = channel().internal_tick_units;
    if (c.writes != 1 || c.fetches == 0 ||
        now < c.first_fetch_tick || now < c.write_tick ||
        (c.pixels > 0 && now < c.last_pixel_tick) ||
        pattern != (c.chosen_bank ? 3U : 0U)) ++c.invalid;
    if (c.pixels == 0) c.first_pixel_tick = now;
    c.last_pixel_tick = now;
    ++c.pixels;
    chr_chronology_try_emit();
}
#endif

// Stage106: MMC3 $8001 CHR register writes, source-frame windows ONLY.
// The source register values are never written to logs. A changed register
// is not proof that any changed tile was fetched or rendered by a real PPU.
#ifdef VPD_NATIVE_SYNTHETIC_MMC3_CHR
inline void observe_native_mmc3_chr_write(unsigned selector, unsigned value) {
#ifdef VPD_NATIVE_SYNTHETIC_MIDFRAME_CHR
    stage110_register_write(selector, value);
#endif
#ifdef VPD_NATIVE_SYNTHETIC_CHR_TIMELINE
    chr_chronology_write(selector, value);
#endif
    static const char* opt = std::getenv("VPD_STAGE106_MMC3_CHR_PROBE");
    if (!opt || std::strcmp(opt, "1") != 0) return;
    struct Mmc3Aggregate {
        unsigned long writes = 0;
        unsigned long changed = 0;
        unsigned long inside = 0;
        unsigned long outside = 0;
        unsigned long after_cpu_high = 0;
        unsigned long invalid = 0;
        unsigned long long inside_tick_lag_min = 0;
        unsigned long long inside_tick_lag_max = 0;
        unsigned char seen[6] = {0, 0, 0, 0, 0, 0};
        unsigned char previous[6] = {0, 0, 0, 0, 0, 0};
        bool emitted = false;
    };
    static Mmc3Aggregate a;
    if (a.emitted) return;
    if (selector >= 6 || value > 255) {
        ++a.invalid;
        return;
    }
    ++a.writes;
    if (a.seen[selector] && a.previous[selector] != value) ++a.changed;
    a.seen[selector] = 1;
    a.previous[selector] = static_cast<unsigned char>(value);
#ifdef VPD_NATIVE_SYNTHETIC_EVENT_ORDER
    const EventOrderState& e = event_order_state();
    if (e.source_window) {
        ++a.inside;
        if (e.high_read_this_window) ++a.after_cpu_high;
        const unsigned long long now = channel().internal_tick_units;
        if (e.source_entries == 0 || now < e.current_entry_tick) {
            ++a.invalid;
        } else {
            const unsigned long long lag = now - e.current_entry_tick;
            if (a.inside == 1 || lag < a.inside_tick_lag_min)
                a.inside_tick_lag_min = lag;
            if (lag > a.inside_tick_lag_max)
                a.inside_tick_lag_max = lag;
        }
    } else {
        ++a.outside;
    }
#else
    ++a.invalid;
#endif
    if (a.writes == 4096) {
        std::fprintf(stderr,
            "VPD_STAGE106_NATIVE_MMC3_CHR_PASS writes=4096 "
            "changed=%lu within_source_window=%lu outside_source_window=%lu "
            "after_cpu_high_read=%lu lag_min=%llu lag_max=%llu invalid=%lu "
            "source_only=yes chr_pixel_causality_proven=no\n",
            a.changed, a.inside, a.outside, a.after_cpu_high,
            a.inside_tick_lag_min, a.inside_tick_lag_max, a.invalid);
        std::fflush(stderr);
        a.emitted = true;
    }
}
#endif

// Stage107: synthetic ROM only; actual final newppu framebuffer byte aggregate.
// No per-frame screenshots, pixel positions, or original game bytes published.
#ifdef VPD_NATIVE_SYNTHETIC_BG_PIXELS
inline void observe_native_bg_pixel(unsigned bg_pattern, unsigned final_byte) {
    static const char* enabled = std::getenv("VPD_STAGE107_BG_PIXEL_PROBE");
    if (!enabled || std::strcmp(enabled, "1") != 0) return;
    struct Aggregate {
        unsigned long sampled = 0, zero = 0, nonzero = 0, invalid = 0;
        unsigned long long hash = 14695981039346656037ULL;
        bool emitted = false;
    };
    static Aggregate a;
    if (a.emitted) return;
    if (bg_pattern > 3 || final_byte > 255) { ++a.invalid; return; }
#ifdef VPD_NATIVE_SYNTHETIC_CHR_TIMELINE
    chr_chronology_pixel(bg_pattern);
#endif
    ++a.sampled;
    if (bg_pattern == 0) ++a.zero;
    else ++a.nonzero;
    a.hash = (a.hash ^ static_cast<unsigned long long>(final_byte)) * 1099511628211ULL;
    if (a.sampled == 32768) {
        std::fprintf(stderr,
            "VPD_STAGE107_NATIVE_BG_PIXEL_PASS sampled=32768 "
            "bg_zero=%lu bg_nonzero=%lu final_fnv64=%llu invalid=%lu "
            "synthetic_only=yes original_pixel_proof=no\n",
            a.zero, a.nonzero, a.hash, a.invalid);
        std::fflush(stderr);
        a.emitted = true;
    }
}
#endif

// Stage108: actual newppu background pattern fetch values, synthetic ROM ONLY.
// Never logs addresses, bytes, ROM contents, or any screen pixels.
#ifdef VPD_NATIVE_SYNTHETIC_BG_FETCH
inline void observe_native_bg_fetch(unsigned int address, unsigned int value, bool high) {
    static const char* enabled = std::getenv("VPD_STAGE108_BG_FETCH_PROBE");
    if (!enabled || std::strcmp(enabled, "1") != 0) return;
    struct FetchAggregate {
        unsigned long reads = 0, low = 0, high = 0, zero = 0, ff = 0;
        unsigned long other = 0, pairs = 0, invalid = 0;
        unsigned int last_low = 0;
        bool expecting_high = false;
        bool emitted = false;
    };
    static FetchAggregate a;
    if (a.emitted) return;
#ifdef VPD_NATIVE_SYNTHETIC_CHR_TIMELINE
    chr_chronology_fetch(address, value);
#endif
    if (address < 0x1000 || address >= 0x2000 || value > 0xff) ++a.invalid;
    if (high) {
        ++a.high;
        if (!a.expecting_high || address != (a.last_low | 8)) ++a.invalid;
        else ++a.pairs;
        a.expecting_high = false;
    } else {
        ++a.low;
        if (a.expecting_high || (address & 8) != 0) ++a.invalid;
        a.last_low = address;
        a.expecting_high = true;
    }
    if (value == 0) ++a.zero;
    else if (value == 0xff) ++a.ff;
    else ++a.other;
    ++a.reads;
    if (a.reads == 8192) {
        if (a.expecting_high) ++a.invalid;
        std::fprintf(stderr,
            "VPD_STAGE108_NATIVE_BG_FETCH_PASS reads=8192 "
            "low=%lu high=%lu zero=%lu ff=%lu other=%lu "
            "paired=%lu invalid=%lu synthetic_only=yes "
            "original_game_fetch_proven=no\n",
            a.low, a.high, a.zero, a.ff, a.other, a.pairs, a.invalid);
        std::fflush(stderr);
        a.emitted = true;
    }
}
#endif

// Stage102 observes *source-level* PPU_status assignment boundaries, NOT
// validated hardware VBlank edges. Intentionally export aggregates only.
#ifdef VPD_NATIVE_SYNTHETIC_VBLANK
inline void observe_native_status_assignment(bool entering, bool bit_after) {
#ifdef VPD_NATIVE_SYNTHETIC_PRECLEAR
    preclear_source_assignment(entering, bit_after);
#endif
#ifdef VPD_NATIVE_SYNTHETIC_EVENT_ORDER
    event_order_assignment(entering, bit_after);
#endif
    static const char* enabled = std::getenv("VPD_STAGE102_STATUS_PROBE");
    if (!enabled || std::strcmp(enabled, "1") != 0) return;
    struct Windows {
        unsigned entries = 0;
        unsigned clears = 0;
        unsigned invalid = 0;
        unsigned long long last_entry = 0;
        unsigned long long period_min = 0;
        unsigned long long period_max = 0;
        unsigned long long window_min = 0;
        unsigned long long window_max = 0;
        bool emitted = false;
    };
    static Windows w;
    if (w.emitted) return;
    const unsigned long long now = channel().internal_tick_units;
    if (entering) {
        if (!bit_after || w.entries != w.clears) ++w.invalid;
        if (w.entries > 0) {
            const unsigned long long period = now - w.last_entry;
            if (now <= w.last_entry) ++w.invalid;
            if (w.entries == 1 || period < w.period_min) w.period_min = period;
            if (period > w.period_max) w.period_max = period;
        }
        w.last_entry = now;
        ++w.entries;
    } else {
        if (bit_after || w.entries != w.clears + 1) ++w.invalid;
        const unsigned long long window = now - w.last_entry;
        if (now <= w.last_entry) ++w.invalid;
        if (w.clears == 0 || window < w.window_min) w.window_min = window;
        if (window > w.window_max) w.window_max = window;
        ++w.clears;
    }
    if (w.entries == 3 && w.clears == 3) {
        std::fprintf(stderr,
            "VPD_STAGE102_NATIVE_STATUS_WINDOW_PASS entries=3 clears=3 "
            "entry_period_min=%llu entry_period_max=%llu "
            "entry_to_clear_min=%llu entry_to_clear_max=%llu "
            "invalid=%u hardware_vblank_proven=no raw_positions=no\n",
            w.period_min, w.period_max, w.window_min, w.window_max,
            w.invalid);
        std::fflush(stderr);
        w.emitted = true;
    }
}
#endif

// Stage103: the *CPU A2002 read path* (not the frame-loop assignment).
// Aggregates booleans only; returned register byte is never written out.
#ifdef VPD_NATIVE_SYNTHETIC_PPUSTATUS_READ
inline void observe_native_ppustatus_read(bool returned_high,
                                          bool before_high,
                                          bool after_high) {
#ifdef VPD_NATIVE_SYNTHETIC_PRECLEAR
    preclear_cpu_read(returned_high, before_high, after_high);
#endif
#ifdef VPD_NATIVE_SYNTHETIC_EVENT_ORDER
    event_order_read(returned_high, before_high, after_high);
#endif
    static const char* env = std::getenv("VPD_STAGE103_PPUSTATUS_READ_PROBE");
    if (!env || std::strcmp(env, "1") != 0) return;
    struct ReadAggregate {
        unsigned long reads = 0;
        unsigned long returned_high = 0;
        unsigned long before_high = 0;
        unsigned long cleared_high = 0;
        unsigned long after_high = 0;
        unsigned long invalid = 0;
        bool emitted = false;
    };
    static ReadAggregate reads;
    if (reads.emitted) return;
    ++reads.reads;
    if (returned_high) ++reads.returned_high;
    if (before_high) ++reads.before_high;
    if (before_high && !after_high) ++reads.cleared_high;
    if (after_high) ++reads.after_high;
    if (returned_high != before_high || after_high) ++reads.invalid;
    if (reads.reads == 16384) {
        std::fprintf(stderr,
            "VPD_STAGE103_NATIVE_PPUSTATUS_READ_PASS reads=16384 "
            "returned_high=%lu before_high=%lu cleared_high=%lu "
            "after_high=%lu invalid=%lu source_only=yes "
            "hardware_vblank_proven=no\n",
            reads.returned_high, reads.before_high,
            reads.cleared_high, reads.after_high, reads.invalid);
        std::fflush(stderr);
        reads.emitted = true;
    }
}
#endif
}  // namespace vpd_ppu_probe
#endif
