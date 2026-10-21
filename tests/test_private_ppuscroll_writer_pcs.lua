-- Invented callback sequence only; no original content or FM2.
local root=os.tmpname().."_writer_mock"
assert(os.execute("mkdir -p "..root))
local get=os.getenv
local env={
 VPD_PRIVATE_WRITER_OUTPUT_DIR=root,
 VPD_PRIVATE_FM2_PATH="/tmp/invented.fm2",
 VPD_PRIVATE_ROM_PAYLOAD_MD5=string.rep("f",32),
 VPD_PRIVATE_FRAME_COUNT="6",
 VPD_PRIVATE_WRITER_START_FRAME="2",
 VPD_PRIVATE_WRITER_STOP_FRAME="4"
}
os.getenv=function(name) return env[name] or get(name) end
local frame,after=0,nil
local listeners={}
rom={gethash=function(which) assert(which=="md5");return string.rep("f",32)end}
movie={
 play=function(path,readonly)
   assert(path==env.VPD_PRIVATE_FM2_PATH and readonly);return true
 end,
 readonly=function()return true end,
 length=function()return 6 end
}
local clock=0
debugger={getcyclescount=function()return clock end}
memory={registerexec=function(addr,cb)
 assert(listeners[addr]==nil);listeners[addr]=cb
end}
emu={
 framecount=function()return frame end,
 registerafter=function(cb) assert(after==nil);after=cb end
}
dofile("tools/capture_private_ppuscroll_writer_pcs.lua")
local pcs={0xE8EC,0xE8F1,0xE369,0xE36C}
local offsets={20,27,150,154}
for i=0,5 do
 frame=i
 if i>=2 and i<=4 then
   for n,pc in ipairs(pcs) do
     assert(type(listeners[pc])=="function")
     clock=frame*100+offsets[n]
     listeners[pc]()
   end
 end
 after()
end
after()
local function read(name)
 local f=assert(io.open(root.."/"..name,"rb"))
 local content=assert(f:read("*a"));assert(f:close());return content
end
local tsv=read("pc_2005_writer_candidates.tsv")
local lines=0
for _ in tsv:gmatch("[^\n]+")do lines=lines+1 end
assert(lines==13)
assert(tsv:find("2\t350\tE369",1,true))
assert(tsv:find("4\t554\tE36C",1,true))
local witness=read("COMPLETE.txt")
assert(witness:find("format=private_ppuscroll_writer_pc_v1",1,true))
assert(witness:find("writer_pc_hits=12",1,true))
assert(witness:find("last_observed_frame=4",1,true))
assert(witness:find("frame_gaps=0",1,true))
print("PRIVATE_2005_WRITER_PC_MOCK_PASS frames=3 writers=4 events=12")
assert(os.execute("rm -rf "..root))
os.getenv=get
