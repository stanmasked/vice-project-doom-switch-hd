-- Entirely invented FCEUX frame/CPU-clock callbacks; no original game data.
local root=os.tmpname().."_frame_anchors_mock"
assert(os.execute("mkdir -p "..root))
local orig_getenv=os.getenv
local environment={
 VPD_PRIVATE_ANCHOR_OUTPUT_DIR=root,
 VPD_PRIVATE_FM2_PATH="/tmp/invented.fm2",
 VPD_PRIVATE_ROM_PAYLOAD_MD5=string.rep("f",32),
 VPD_PRIVATE_FRAME_COUNT="7",
 VPD_PRIVATE_ANCHOR_START_FRAME="3",
 VPD_PRIVATE_ANCHOR_STOP_FRAME="5"
}
os.getenv=function(key)return environment[key] or orig_getenv(key)end
local frame,after,cycle=0,nil,0
rom={gethash=function(which)assert(which=="md5");return string.rep("f",32)end}
movie={
 play=function(path,readonly)
  assert(path==environment.VPD_PRIVATE_FM2_PATH and readonly);return true
 end,
 readonly=function()return true end,
 length=function()return 7 end
}
debugger={getcyclescount=function()return cycle end}
emu={
 framecount=function()return frame end,
 registerafter=function(callback)assert(after==nil);after=callback end
}
dofile("tools/capture_private_fceux_frame_anchors.lua")
for n=0,6 do
 frame=n
 cycle=1234+30000*n
 after()
end
after()
local function read(name)
 local f=assert(io.open(root.."/"..name,"rb"))
 local s=assert(f:read("*a"));assert(f:close());return s
end
local trace=read("after_frame_cycles.tsv")
assert(trace=="frame\tcycle\n2\t61234\n3\t91234\n4\t121234\n5\t151234\n",trace)
local witness=read("COMPLETE.txt")
assert(witness:find("format=private_original_fceux_frame_anchor_v1",1,true))
assert(witness:find("first_observed_frame=0",1,true))
assert(witness:find("last_observed_frame=5",1,true))
assert(witness:find("frame_gaps=0",1,true))
assert(witness:find("rom_identity_verified=yes",1,true))
assert(witness:find("movie_readonly_verified=yes",1,true))
print("PRIVATE_FCEUX_SYNTHETIC_FRAME_ANCHORS_PASS frames=2..5 unique=4")
assert(os.execute("rm -rf "..root))
os.getenv=orig_getenv
