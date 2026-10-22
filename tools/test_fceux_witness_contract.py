#!/usr/bin/env python3
"""Keep the fabricated FCEUX guest witness schema aligned with host validation.

This is a source-contract check only, never a substitute for real FCEUX execution.
"""
from pathlib import Path
import re

source = (Path(__file__).parent / "verify_real_fceux_runtime.py").read_text(encoding="utf-8")
guest = source.split("LUA=r'''", 1)[1].split("'''", 1)[0]
marker = guest.split("assert(file:write(", 1)[1].split("assert(file:close())", 1)[0]
fields = re.findall(r'"([^"\\]*(?:\\.[^"\\]*)*)"', marker)
expected = [
    "VPD_REAL_FCEUX_EXECUTABLE_API_PASS\\n",
    "frame=",
    "\\n",
    "real_cpu_exec=yes\\n",
    "real_cpu_cycle_clock=yes\\n",
    "real_ppu_rgb_api=yes\\n",
    "repeated_frame_hooks=yes\\n",
    "midpoint_frame_observed=yes\\n",
    "continuous_frame_sequence=yes\\n",
    "source=synthetic_rom_only\\n",
]
assert fields == expected, f"guest witness fields mismatch: {fields!r}"
assert "if len(actual)!=9" in source, "host witness line-count mismatch"
for field in ("real_cpu_exec=yes", "real_cpu_cycle_clock=yes",
              "real_ppu_rgb_api=yes", "repeated_frame_hooks=yes",
              "midpoint_frame_observed=yes", "continuous_frame_sequence=yes",
              "source=synthetic_rom_only"):
    assert source.count(field) >= 2, f"host validator missing {field}"
print("VPD_FCEUX_WITNESS_CONTRACT_PASS schema_lines=9 synthetic_only=yes")
