// Stage98: optional internal newppu observations, NOT normalized NES raster.
// Header-only, no FCEUX dependencies; no file output and no implicit sink.
// Install callback explicitly only on a controlled private emulator build.
#ifndef VPD_NEWPPU_RAW_STEP_PROBE_H
#define VPD_NEWPPU_RAW_STEP_PROBE_H
#if defined(VPD_NATIVE_SYNTHETIC_SMOKE) || defined(VPD_NATIVE_SYNTHETIC_VBLANK) || defined(VPD_NATIVE_SYNTHETIC_PPUSTATUS_READ) || defined(VPD_NATIVE_SYNTHETIC_EVENT_ORDER) || defined(VPD_NATIVE_SYNTHETIC_PRECLEAR)
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
