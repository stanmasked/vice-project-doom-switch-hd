-- Stage95 FCEUX Lua raster capability preflight (read-only / no ROM access).
-- Inspect *symbol presence only*. Candidate names below are exploratory:
-- existence of a Lua function NEVER proves raster timing, VBlank or accuracy.
-- This standalone script deliberately installs no emulator/memory callback.
local function function_exists(library, name)
  local container=rawget(_G,library)
  if type(container)~='table' then return false end
  return type(rawget(container,name))=='function'
end

local fields={
  {'format','vpd_fceux_raster_capability_probe_v1'},
  {'probe_scope','lua_symbol_presence_only'},
  {'framecount_symbol',function_exists('emu','framecount')},
  {'registerbefore_symbol',function_exists('emu','registerbefore')},
  {'registerafter_symbol',function_exists('emu','registerafter')},
  {'registerwrite_symbol',function_exists('memory','registerwrite')},
  {'cpu_cycle_symbol',function_exists('debugger','getcyclescount')},
  {'ppu_readback_symbol',function_exists('ppu','readbyterange')},
  -- Undocumented candidate names; never called, validated or endorsed.
  {'emu_scanline_candidate',function_exists('emu','getscanline')},
  {'emu_dot_candidate',function_exists('emu','getdot')},
  {'ppu_scanline_candidate',function_exists('ppu','getscanline')},
  {'ppu_dot_candidate',function_exists('ppu','getdot')},
  {'candidate_api_called','no'},
  {'register_callbacks_installed','no'},
  {'game_memory_accessed','no'},
  {'vblank_edge_observed','no'},
  {'ppu_scanline_observed','no'},
  {'ppu_dot_observed','no'},
  {'frame_boundary_proven','no'},
  {'visible_chr_scroll_timing_proven','no'},
}
local output={}
for _,field in ipairs(fields) do
  local value=field[2]
  if type(value)=='boolean' then value=value and 'present' or 'absent' end
  local line=field[1]..'='..value
  output[#output+1]=line
  print(line)
end
return table.concat(output,'\n')..'\n'
