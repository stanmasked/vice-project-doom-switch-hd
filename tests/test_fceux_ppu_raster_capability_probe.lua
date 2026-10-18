-- Stage95 synthetic, side-effect-free Lua symbol detection.
local function run(env)
  local lines={}
  env.print=function(line) lines[#lines+1]=line end
  env.type=type; env.rawget=rawget; env.ipairs=ipairs
  env.table=table
  env._G=env
  local chunk=assert(loadfile('tools/probe_fceux_ppu_raster.lua','t',env))
  local returned=chunk()
  assert(returned==table.concat(lines,'\n')..'\n')
  return returned
end
local absence=run({})
assert(absence:find('framecount_symbol=absent\n',1,true))
assert(absence:find('emu_scanline_candidate=absent\n',1,true))
assert(absence:find('vblank_edge_observed=no\n',1,true))

local calls=0
local function forbidden() calls=calls+1; error('Candidate function was called!') end
local candidate=run({
  emu={framecount=forbidden, registerafter=forbidden,
       registerbefore=forbidden, getscanline=forbidden, getdot=forbidden},
  debugger={getcyclescount=forbidden},
  memory={registerwrite=forbidden},
  ppu={readbyterange=forbidden,getscanline=forbidden,getdot=forbidden},
})
assert(candidate:find('emu_scanline_candidate=present\n',1,true))
assert(candidate:find('ppu_dot_candidate=present\n',1,true))
assert(candidate:find('cpu_cycle_symbol=present\n',1,true))
assert(candidate:find('candidate_api_called=no\n',1,true))
assert(candidate:find('register_callbacks_installed=no\n',1,true))
assert(calls==0)

-- Nonfunction keys must not be misidentified as supported.
local wrong=run({emu={getscanline=1, getdot='not-a-function'}})
assert(wrong:find('emu_scanline_candidate=absent\n',1,true))
assert(wrong:find('emu_dot_candidate=absent\n',1,true))
print('Stage95 no-ROM FCEUX Lua raster API symbol preflight PASS')
