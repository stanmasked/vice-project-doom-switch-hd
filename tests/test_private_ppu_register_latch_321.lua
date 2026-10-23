-- Source-free FCEUX mock for the Stage321 private PPU latch capture.
local root=os.tmpname().."_ppu_latch321_mock"
os.remove(root)
assert(os.execute("mkdir -p "..root))
local expected_md5="7d836d9dfa536db69d929935a1e28bf3"
local current_frame,current_cycle,current_pc=0,0,0
local regs={a=0,x=0,y=0,pc=0}
local instruction_bytes={}
local exec_hooks,write_hooks={},{}
local before_callback,after_callback=nil,nil
local paused=false
local env={
 VPD_PRIVATE_PPU_LATCH_OUTPUT_DIR=root,
 VPD_PRIVATE_FM2_PATH="/synthetic/mock.fm2",
 VPD_PRIVATE_ROM_PAYLOAD_MD5=expected_md5,
 VPD_PRIVATE_FRAME_COUNT="43652",
}
local old_getenv=os.getenv
os.getenv=function(name) return env[name] end
emu={
 framecount=function() return current_frame end,
 registerbefore=function(fn) before_callback=fn end,
 registerafter=function(fn) after_callback=fn end,
 pause=function() paused=true end,
}
movie={
 play=function(path,readonly) assert(path==env.VPD_PRIVATE_FM2_PATH and readonly==true);return true end,
 readonly=function() return true end,
 length=function() return 43652 end,
}
rom={gethash=function(kind) assert(kind=="md5");return expected_md5 end}
debugger={getcyclescount=function() return current_cycle end}
memory={
 getregister=function(name) if name=="pc" then return current_pc end;return regs[name] end,
 readbyte=function(address) return instruction_bytes[address] or 0 end,
 registerexec=function(address,fn) assert(exec_hooks[address]==nil);exec_hooks[address]=fn end,
 registerwrite=function(address,fn) assert(write_hooks[address]==nil);write_hooks[address]=fn end,
}
local function write(address,value,pc,cycle)
 current_pc,current_cycle=pc,cycle
 regs.pc=pc;regs.a=value
 assert(type(write_hooks[address])=="function")
 write_hooks[address](address,1,value)
end
dofile("tools/capture_private_ppu_register_latch_321.lua")
os.getenv=old_getenv
local exec_count,write_count=0,0
for _ in pairs(exec_hooks) do exec_count=exec_count+1 end
for _ in pairs(write_hooks) do write_count=write_count+1 end
assert(exec_count==68,"all PRG-slot direct PPUSTATUS candidates must be hooked")
assert(write_count==5,"PPUCTRL, PPUMASK, PPUSTATUS, PPUSCROLL and PPUADDR writes must be observed")
assert(type(before_callback)=="function" and type(after_callback)=="function")
instruction_bytes[0xE8E7]=0xAD
instruction_bytes[0xE8E8]=0x02
instruction_bytes[0xE8E9]=0x20
for frame=0,920 do
 current_frame=frame
 current_cycle=frame*30000
 before_callback()
 if frame>=600 then
  write(0x2000,0x88,0xE69A,current_cycle+20)
  write(0x2001,0x1E,0xE6A1,current_cycle+30)
  current_pc,current_cycle=0xE8E7,frame*30000+100
  regs.pc,regs.a,regs.x,regs.y=0xE8E7,0x88,0,0
  assert(type(exec_hooks[0xE8E7])=="function")
  exec_hooks[0xE8E7]()
  write(0x2006,0x23,0xE6A2,frame*30000+200)
  write(0x2006,0x00,0xE6A5,frame*30000+204)
  write(0x2005,0x00,0xE8EF,frame*30000+800)
  write(0x2005,frame%256,0xE8F4,frame*30000+807)
  write(0x2005,0x00,0xE36C,frame*30000+24283)
  write(0x2005,0x00,0xE36F,frame*30000+24287)
  write(0x2006,0x23,0xE6A2,frame*30000+25000)
  write(0x2006,0x00,0xE6A5,frame*30000+25004)
 end
 current_cycle=frame*30000+30000
 after_callback()
end
assert(paused,"capture must pause only after the complete bounded window")
local function read_all(path)
 local f=assert(io.open(root.."/"..path,"rb"))
 local s=f:read("*a");f:close();return s
end
local counts=read_all("ppu_register_counts.tsv")
assert(counts:find("frames=321",1,true))
assert(counts:find("R2002=321",1,true))
assert(counts:find("W2005=1284",1,true))
assert(counts:find("W2006=1284",1,true))
assert(counts:find("total_events=3531",1,true))
local clock=read_all("ppu_register_frame_clock.tsv")
local clock_rows=0
for _ in clock:gmatch("\n") do clock_rows=clock_rows+1 end
assert(clock_rows==322,"header plus all 321 frame clocks required")
local events=read_all("ppu_register_events.tsv")
local event_rows=0
for _ in events:gmatch("\n") do event_rows=event_rows+1 end
assert(event_rows==3532,"header plus all 3531 events required")
assert(read_all("COMPLETE.txt"):find("frame_clock_rows=321",1,true))
os.execute("rm -rf "..root)
print("PRIVATE_PPU_LATCH_CAPTURE_LUA_MOCK_PASS frames=321 hooks=68 status_reads=321 scroll_writes=1284 frame_clocks=321")
