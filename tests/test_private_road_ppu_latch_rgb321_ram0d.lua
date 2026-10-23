-- ROM-free mock for same-session RAM $0D/CPU/PPU/RGB capture.
local root=os.tmpname().."_roadppu_ram0d_trace_mock"
os.remove(root)
assert(os.execute("mkdir -p "..root))
local expected_md5="7d836d9dfa536db69d929935a1e28bf3"
local current_frame,current_cycle,current_pc=0,0,0
local regs={a=0,x=0,y=0,pc=0}
local instruction_bytes={}
local exec_hooks,write_hooks={},{}
local before_callback,after_callback=nil,nil
local paused,ram0d=false,0
local env={
 VPD_PRIVATE_PPU_LATCH_OUTPUT_DIR=root,
 VPD_PRIVATE_FM2_PATH="/synthetic/ram0d.fm2",
 VPD_PRIVATE_ROM_PAYLOAD_MD5=expected_md5,
 VPD_PRIVATE_FRAME_COUNT="43652",
 VPD_RAM0D_TRACE_DIR=root,
}
local old_getenv=os.getenv
os.getenv=function(name)return env[name]end
emu={
 framecount=function()return current_frame end,
 registerbefore=function(fn)before_callback=fn end,
 registerafter=function(fn)after_callback=fn end,
 pause=function()paused=true end,
 getscreenpixel=function(x,y,raw)
  assert(raw and x>=0 and x<256 and (y==120 or y==140 or y==160 or y==180))
  return (x+current_frame)%256,(y+current_frame)%256,(x+y)%256,1
 end,
}
movie={
 play=function(path,readonly)assert(path==env.VPD_PRIVATE_FM2_PATH and readonly);return true end,
 readonly=function()return true end,
 length=function()return 43652 end
}
rom={gethash=function(kind)assert(kind=="md5");return expected_md5 end}
debugger={getcyclescount=function()return current_cycle end}
memory={
 getregister=function(name)if name=="pc" then return current_pc end;return regs[name]end,
 readbyte=function(address)if address==0x0D then return ram0d end;return instruction_bytes[address] or 0 end,
 registerexec=function(address,fn)assert(exec_hooks[address]==nil);exec_hooks[address]=fn end,
 registerwrite=function(address,fn)assert(write_hooks[address]==nil);write_hooks[address]=fn end,
}
local function write(address,value,pc,cycle)
 current_pc,current_cycle=pc,cycle
 regs.pc,regs.a=pc,value
 if address==0x0D then ram0d=value end
 assert(type(write_hooks[address])=="function")
 write_hooks[address](address,1,value)
end
instruction_bytes[0xE8E7]=0xAD
instruction_bytes[0xE8E8]=0x02
instruction_bytes[0xE8E9]=0x20
for _,pc in ipairs({0xE8EC,0xE8F1}) do
 instruction_bytes[pc]=0x8D;instruction_bytes[pc+1]=0x05;instruction_bytes[pc+2]=0x20
end
for _,pc in ipairs({0xE369,0xE36C}) do
 instruction_bytes[pc]=0x8E;instruction_bytes[pc+1]=0x05;instruction_bytes[pc+2]=0x20
end
instruction_bytes[0xD3C7]=0xF0
instruction_bytes[0xD3C8]=0x85;instruction_bytes[0xD3C9]=0x0D
instruction_bytes[0xD3CA]=0xC6;instruction_bytes[0xD3CB]=0x0D
dofile("tools/capture_private_road_ppu_latch_rgb321_ram0d.lua")
os.getenv=old_getenv
local exec_count,write_count=0,0
for _ in pairs(exec_hooks)do exec_count=exec_count+1 end
for _ in pairs(write_hooks)do write_count=write_count+1 end
assert(exec_count==72,"68 PPUSTATUS candidates plus four writer PCs expected")
assert(write_count==6,"five PPU port hooks plus the RAM $0D hook expected")
local before_pcs={0xE8EC,0xE8F1,0xE369,0xE36C}
local after_pcs={0xE8EF,0xE8F4,0xE36C,0xE36F}
local offsets={800,807,24283,24287}
local sta_remaining=6
local function ram_write_count(frame)
 local i=frame-600
 if i<13 then return 0
 elseif i<15 then return 1
 elseif i<22 then return 2
 elseif i<26 then return 3
 elseif i<32 then return 4
 elseif i<314 then return 5
 elseif i<320 then return 6
 else return 8 end
end
for frame=0,920 do
 current_frame=frame
 current_cycle=frame*30000
 before_callback()
 if frame==10 or frame==12 then write(0x2005,0,0xE8EF,current_cycle+800) end
 if frame>=600 then
  local index=frame-600
  local begin=frame*30000
  for i=1,(index<166 and 3 or 2) do write(0x2000,0x88,0xE69A,begin+20+2*(i-1)) end
  for i=1,2 do write(0x2001,0x1E,0xE6A1,begin+30+2*(i-1)) end
  for i=1,(index<203 and 3 or 2) do
   current_pc,current_cycle=0xE8E7,begin+100+2*(i-1)
   regs.pc,regs.a,regs.x,regs.y=0xE8E7,0x88,0,0
   assert(type(exec_hooks[0xE8E7])=="function")
   exec_hooks[0xE8E7]()
  end
  for pair=0,(index<102 and 11 or 10)-1 do
   write(0x2006,0x23,0xE6A2,begin+200+4*pair)
   write(0x2006,0x00,0xE6A5,begin+202+4*pair)
  end
  local second
  if frame==600 then second=77
  elseif frame==601 then second=(ram0d+1)%256
  else second=ram0d end
  local values={0,second,0,0}
  for i=1,4 do
   local before_pc,after_pc,value,offset=before_pcs[i],after_pcs[i],values[i],offsets[i]
   current_pc,current_cycle=before_pc,begin+offset
   regs.pc=before_pc
   regs.a=(i<=2) and value or 0x55
   regs.x=(i>=3) and value or 0
   regs.y=0
   assert(type(exec_hooks[before_pc])=="function")
   exec_hooks[before_pc]()
   write(0x2005,value,after_pc,begin+offset)
  end
  for i=1,ram_write_count(frame) do
   local value,pc
   if sta_remaining>0 then
    value=(ram0d+10)%256;pc=0xD3CA;sta_remaining=sta_remaining-1
   else
    value=(ram0d-1)%256;pc=0xD3CC
   end
   write(0x0D,value,pc,begin+26000+20*i)
  end
 end
 current_cycle=frame*30000+30000
 after_callback()
 if frame==920 then break end
end
assert(sta_remaining==0,"six synthetic STA writes must be exercised")
assert(paused,"capture must pause after the full bounded window")
local function read_all(name)local f=assert(io.open(root.."/"..name,"rb"));local s=f:read("*a");f:close();return s end
local counts=read_all("ppu_register_counts.tsv")
assert(counts:find("R2002=845",1,true) and counts:find("W2000=808",1,true))
assert(counts:find("W2001=642",1,true) and counts:find("W2005=1284",1,true))
assert(counts:find("W2006=6624",1,true) and counts:find("total_events=10203",1,true))
assert(counts:find("cpu_writer_events=1284",1,true) and counts:find("postframe_ram_samples=321",1,true))
assert(counts:find("rgb_slots=41",1,true))
local trace=read_all("road_321_ram_writes.tsv");local trace_rows=0
for _ in trace:gmatch("\n")do trace_rows=trace_rows+1 end
assert(trace_rows==1507,"header plus 1,506 RAM writes expected")
local ramdone=read_all("RAM0D_TRACE_COMPLETE.txt")
assert(ramdone:find("ram0d_write_events=1506",1,true))
assert(ramdone:find("ram0d_dec_events=1500",1,true) and ramdone:find("ram0d_sta_events=6",1,true))
assert(ramdone:find("writer_prev_frame_matches=319",1,true))
local events=read_all("ppu_register_events.tsv");local event_rows=0
for _ in events:gmatch("\n")do event_rows=event_rows+1 end
assert(event_rows==10204,"header plus 10,203 PPU events expected")
local clocks=read_all("source_frame_clock.tsv");local clock_rows=0
for _ in clocks:gmatch("\n")do clock_rows=clock_rows+1 end
assert(clock_rows==322,"header plus 321 shared frame clocks expected")
local writers=read_all("road_321_writers.tsv");local writer_rows=0
for _ in writers:gmatch("\n")do writer_rows=writer_rows+1 end
assert(writer_rows==1285,"header plus 1,284 CPU writer events expected")
local ram=read_all("road_321_postframe.tsv");local ram_rows=0
for _ in ram:gmatch("\n")do ram_rows=ram_rows+1 end
assert(ram_rows==322,"header plus 321 RAM samples expected")
local rgb=read_all("road_321_rgb_scanlines.bin")
assert(#rgb==126054 and rgb:sub(1,8)=="VPDRGB41")
local complete=read_all("COMPLETE.txt")
assert(complete:find("format=private_road_ppu_latch_rgb321_v1",1,true))
assert(complete:find("events=10203",1,true) and complete:find("rgb_slots=41",1,true))
os.execute("rm -rf "..root)
print("PRIVATE_ROAD_PPU_RAM0D_LATCH_RGB321_LUA_MOCK_PASS frames=321 ram_writes=1506 cpu_writes=1284 ppu_events=10203 rgb_slots=41")
