-- Fully synthetic isolated FCEUX Lua hook test for windowed FM2 replay captures.
VPD_CAPTURE_DIRECTORY=os.tmpname()..'_fm2_window_test'
assert(os.execute("mkdir -p "..VPD_CAPTURE_DIRECTORY))
VPD_CAPTURE_START_FRAME=16
VPD_CAPTURE_STOP_FRAME=24
VPD_CAPTURE_INTERVAL=8
VPD_CAPTURE_LIMIT=3
VPD_CAPTURE_SCREEN=false
local hooks,reads={},{}
local after,exit
local frame=0
memory={
 registerwrite=function(addr,cb) assert(not hooks[addr]);hooks[addr]=cb end,
 registerread=function(addr,cb) assert(not reads[addr]);reads[addr]=cb end,
 readbyterange=function(addr,n)assert(addr==0 and n==2048);return string.rep("R",n)end,
 readbyte=function(addr)return addr%256 end
}
ppu={readbyterange=function(addr,n)assert(addr==0 and n==16384);return string.rep("P",n)end}
rom={gethash=function(which)assert(which=="md5");return string.rep("f",32)end}
emu={framecount=function()return frame end,
 registerafter=function(cb)after=cb end,
 registerexit=function(cb)exit=cb end,
 message=function(m)assert(type(m)=="string")end}
dofile("tools/capture_fceux_ppu.lua")
assert(type(after)=="function" and type(exit)=="function")
local function event(f,addr,value)
  frame=f
  hooks[addr](addr,1,value)
  after()
end
event(0,0x8000,0x04)
event(8,0x8001,0x10)
event(16,0x8000,0x80)
event(20,0x8001,0x22)
event(24,0x2000,0x10)
event(32,0x8000,0x03)
exit()
local function read(path)
 local file=io.open(path,"rb")
 if not file then return nil end
 local data=file:read("*a");file:close();return data
end
local root=VPD_CAPTURE_DIRECTORY.."/"
assert(read(root.."frame_000000.meta.txt")==nil,"captured before configured window")
assert(read(root.."frame_000008.meta.txt")==nil,"captured before configured window")
assert(read(root.."frame_000032.meta.txt")==nil,"captured after configured window")
assert(#read(root.."frame_000016.ppu.bin")==16384)
assert(#read(root.."frame_000024.ram.bin")==2048)
assert(read(root.."frame_000016.screen.pal.bin")==nil,"unexpected screen reference")
local start_meta=read(root.."frame_000016.meta.txt")
local end_meta=read(root.."frame_000024.meta.txt")
assert(start_meta:find("capture_window_start=16",1,true))
assert(start_meta:find("capture_window_stop=24",1,true))
assert(start_meta:find("register_log_scope=selected_frame_window_only",1,true))
assert(start_meta:find("logged_register_writes=1",1,true),start_meta)
assert(end_meta:find("logged_register_writes=3",1,true),end_meta)
local log=read(root.."mmc3_video_writes.tsv")
assert(log:find("16\t8000\t80",1,true),log)
assert(log:find("20\t8001\t22",1,true),log)
assert(log:find("24\t2000\t10",1,true),log)
assert(not log:find("8\t8001\t10",1,true),log)
assert(not log:find("32\t8000\t03",1,true),log)
print("PASS: FM2 windowed FCEUX PPU/RAM capture and bounded register log")
assert(os.execute("rm -rf "..VPD_CAPTURE_DIRECTORY))
