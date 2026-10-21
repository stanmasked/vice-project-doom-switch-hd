-- Synthetic-only FCEUX 5-PC instruction witness test; no NES files.
local root=os.tmpname().."_e8de_exec_mock"
assert(os.execute("mkdir -p "..root))
local prior_getenv=os.getenv
local env={
 VPD_PRIVATE_EXEC_OUTPUT_DIR=root,
 VPD_PRIVATE_FM2_PATH="/tmp/synthetic_invented.fm2",
 VPD_PRIVATE_ROM_PAYLOAD_MD5=string.rep("f",32),
 VPD_PRIVATE_FRAME_COUNT="6",
 VPD_PRIVATE_EXEC_START_FRAME="2",
 VPD_PRIVATE_EXEC_STOP_FRAME="4"
}
os.getenv=function(name)return env[name] or prior_getenv(name)end
local frame,after=0,nil
local handlers={}
rom={gethash=function(which)assert(which=="md5");return string.rep("f",32)end}
movie={
 play=function(path,readonly)
   assert(path==env.VPD_PRIVATE_FM2_PATH and readonly);return true
 end,
 readonly=function()return true end,
 length=function()return 6 end
}
memory={registerexec=function(pc,callback)
  assert(handlers[pc]==nil);handlers[pc]=callback
end}
local cycles=0
debugger={getcyclescount=function()return cycles end}
emu={
 framecount=function()return frame end,
 registerafter=function(fn)assert(after==nil);after=fn end
}
dofile("tools/capture_private_e8de_instructions.lua")
local pcs={0xE8DE,0xE8E4,0xE8E7,0xE8EC,0xE8F1}
local offsets={0,9,13,20,27}
for index=0,5 do
  frame=index
  if frame>=2 and frame<=4 then
    for n,pc in ipairs(pcs) do
      assert(type(handlers[pc])=="function")
      cycles=frame*100+offsets[n]
      handlers[pc]()
    end
  end
  after()
end
after() -- no duplicate output following private window
local function read(name)
  local file=assert(io.open(root.."/"..name,"rb"))
  local result=assert(file:read("*a"));assert(file:close());return result
end
local trace=read("emitter_pc_exec.tsv")
local expected=1+3*5
local lines=0
for _ in trace:gmatch("[^\n]+") do lines=lines+1 end
assert(lines==expected)
assert(trace:find("2\t213\tE8E7",1,true))
assert(trace:find("4\t427\tE8F1",1,true))
local witness=read("COMPLETE.txt")
assert(witness:find("format=private_e8de_instruction_trace_v1",1,true))
assert(witness:find("total_instruction_callbacks=15",1,true))
assert(witness:find("last_observed_frame=4",1,true))
assert(witness:find("frame_gaps=0",1,true))
assert(witness:find("rom_identity_verified=yes",1,true))
assert(witness:find("movie_readonly_verified=yes",1,true))
print("PRIVATE_E8DE_SYNTHETIC_INSTRUCTION_CALLBACKS_PASS pcs=5 frames=3 events=15")
assert(os.execute("rm -rf "..root))
os.getenv=prior_getenv
