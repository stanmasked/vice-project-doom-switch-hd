-- Synthesized FCEUX API hooks and 921 callback frames, no source media.
local root=os.tmpname().."_ppu321_mock"
assert(os.execute("mkdir -p "..root))
local env={
 VPD_PRIVATE_PPU321_OUTPUT_DIR=root,
 VPD_PRIVATE_FM2_PATH="/tmp/fabricated_road_321.fm2",
 VPD_PRIVATE_ROM_PAYLOAD_MD5=string.rep("f",32),
 VPD_PRIVATE_FRAME_COUNT="1000",
}
local getenv=os.getenv
os.getenv=function(key)return env[key] or getenv(key)end
local exec,write,before,after={},nil,nil,nil
local frame,cycle,acc,ram0d=0,0,0,0
rom={gethash=function(kind)assert(kind=="md5");return string.rep("f",32)end}
movie={
 play=function(path,readonly)
   assert(readonly and path==env.VPD_PRIVATE_FM2_PATH)
   return true
 end,
 readonly=function()return true end,
 length=function()return 1000 end
}
debugger={getcyclescount=function()return cycle end}
memory={
 registerexec=function(pc,fn)assert(exec[pc]==nil);exec[pc]=fn end,
 registerwrite=function(addr,fn)assert(addr==0x2005 and write==nil);write=fn end,
 getregister=function(name)assert(name=="a");return acc end,
 readbyte=function(addr)assert(addr==0x0D);return ram0d end
}
emu={
 framecount=function()return frame end,
 registerbefore=function(fn)assert(before==nil);before=fn end,
 registerafter=function(fn)assert(after==nil);after=fn end,
 getscreenpixel=function(x,y,raw)
    assert(raw and x>=0 and x<256 and (y==120 or y==140 or y==160 or y==180))
    return (x+frame)%256,(y+frame)%256,(x+y)%256,1
 end,
}
dofile("tools/capture_private_road_ppu_321.lua")
local pcs={0xE8EC,0xE8F1,0xE369,0xE36C}
local shifts={800,807,24283,24287}
local anchor_second={[600]=79,[744]=136,[800]=144,[920]=24}
local anchor_ram={[600]=79,[744]=134,[800]=139,[920]=19}
for f=0,920 do
  frame=f
  cycle=30000*f
  before()
  if f>=600 then
    local second=anchor_second[f] or 42
    local values={0,second,0,0}
    for k,pc in ipairs(pcs) do
      cycle=30000*f+shifts[k]
      acc=values[k]
      assert(type(exec[pc])=="function")
      exec[pc]()
      write(0x2005,1,values[k])
    end
    ram0d=anchor_ram[f] or 18
  end
  cycle=30000*f+29780
  after()
end
after()
local function read(name)
  local f=assert(io.open(root.."/"..name,"rb"))
  local s=assert(f:read("*a"));assert(f:close());return s
end
local w=read("road_321_writers.tsv")
local a=read("road_321_postframe.tsv")
local complete=read("COMPLETE.txt")
local b=read("road_321_frame_clock.tsv")
local img=read("road_321_rgb_scanlines.bin")
assert(#img==20+41*(2+4*256*3))
assert(img:sub(1,8)=="VPDRGB41")
assert(img:sub(21,22)==string.char(600%256,math.floor(600/256)))
assert(img:sub(-3074,-3073)==string.char(920%256,math.floor(920/256)))
local count=0
for _ in w:gmatch("[^\n]+")do count=count+1 end
assert(count==1285)
assert(w:find("600\t2\tE8F1\t4F\t18000807",1,true))
assert(w:find("920\t2\tE8F1\t18\t27600807",1,true))
local ramcount=0
for _ in a:gmatch("[^\n]+")do ramcount=ramcount+1 end
assert(ramcount==322)
assert(a:find("800\t8B\t4",1,true))
local boundarycount=0
for _ in b:gmatch("[^\n]+") do boundarycount=boundarycount+1 end
assert(boundarycount==322)
assert(b:find("600\t18000000\t18029780",1,true))
assert(b:find("920\t27600000\t27629780",1,true))
assert(complete:find("frames_sampled=321",1,true))
assert(complete:find("registerwrite_2005_events=1284",1,true))
print("PRIVATE_ROAD_PPU321_MOCK_PASS frames=321 exec=1284 writes=1284 boundaries=321 rgb_slots=41")
assert(os.execute("rm -rf "..root))
os.getenv=getenv
