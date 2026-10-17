// Stage98: optional internal newppu observations, NOT normalized NES raster.
// Header-only, no FCEUX dependencies; no file output and no implicit sink.
// Install callback explicitly only on a controlled private emulator build.
#ifndef VPD_NEWPPU_RAW_STEP_PROBE_H
#define VPD_NEWPPU_RAW_STEP_PROBE_H
#ifdef VPD_NATIVE_SYNTHETIC_SMOKE
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
    unsigned long invalid = 0;
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
            "invalid_steps=%lu normalized_scanlines=no real_game_data=no\n",
            aggregate.wrapped, aggregate.label_changes,
            channel().invalid);
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
    if (sl < 0 || modulus <= 0 || increment < 1 ||
        before < 0 || before >= modulus ||
        after < 0 || after >= modulus ||
        static_cast<long long>(after) !=
            (static_cast<long long>(before) + increment) % modulus) {
        ++c.invalid;
        return;
    }
    ++c.observed;
#ifdef VPD_NATIVE_SYNTHETIC_SMOKE
    arm_synthetic_smoke_once();
#endif
    if (c.callback) {
        const RawStep step{sl, before, after, modulus, increment};
        c.callback(step, c.user);
    }
}
}  // namespace vpd_ppu_probe
#endif
