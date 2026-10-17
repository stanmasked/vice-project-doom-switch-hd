// Stage98: optional internal newppu observations, NOT normalized NES raster.
// Header-only, no FCEUX dependencies; no file output and no implicit sink.
// Install callback explicitly only on a controlled private emulator build.
#ifndef VPD_NEWPPU_RAW_STEP_PROBE_H
#define VPD_NEWPPU_RAW_STEP_PROBE_H
#if defined(VPD_NATIVE_SYNTHETIC_SMOKE) || defined(VPD_NATIVE_SYNTHETIC_VBLANK)
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

// Stage102 observes *source-level* PPU_status assignment boundaries, NOT
// validated hardware VBlank edges. Intentionally export aggregates only.
#ifdef VPD_NATIVE_SYNTHETIC_VBLANK
inline void observe_native_status_assignment(bool entering, bool bit_after) {
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
}  // namespace vpd_ppu_probe
#endif
