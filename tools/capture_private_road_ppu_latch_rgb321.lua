-- Stage322 unified private original-source road/CPU/PPU/RGB capture.
-- Original ROM/FM2 and raw event values must remain owner-private.
local root=assert(os.getenv('VPD_PRIVATE_PPU_LATCH_OUTPUT_DIR'))
local fm2=assert(os.getenv('VPD_PRIVATE_FM2_PATH'))
local md5=assert(os.getenv('VPD_PRIVATE_ROM_PAYLOAD_MD5')):lower()
local movie_frames=tonumber(assert(os.getenv('VPD_PRIVATE_FRAME_COUNT')))
assert(rom.gethash('md5'):lower()==md5,'original ROM payload identity mismatch')
assert(movie.play(fm2,true) and movie.readonly() and movie.length()==movie_frames,
       'original readonly FM2 mismatch')
assert(type(emu.getscreenpixel)=='function','FCEUX raw source pixel callback unavailable')
local function exclusive(name)
 local p=root..'/'..name
 local old=io.open(p,'rb')
 if old then old:close();error('private output already exists: '..name) end
 return assert(io.open(p,'wb'))
end
local events=exclusive('ppu_register_events.tsv')
local countsfile=exclusive('ppu_register_counts.tsv')
local frameclock=exclusive('source_frame_clock.tsv')
local roadwriter=exclusive('road_321_writers.tsv')
local ramfile=exclusive('road_321_postframe.tsv')
local rgbfile=exclusive('road_321_rgb_scanlines.bin')
assert(roadwriter:write('frame\tordinal\tpc\tvalue\tcycle\n'))
assert(ramfile:write('frame\tram_0d\tppu_2005_writes\n'))
local rgbscanlines={120,140,160,180}
local rgbslots=0
assert(rgbfile:write('VPDRGB41'..string.char(41,0,0,1,4,0,0,0,120,140,160,180)))
local function capture_rgb(frame)
 assert(frame>=600 and frame<=920 and frame%8==0,'unexpected RGB capture frame')
 local buffer={string.char(frame%256,math.floor(frame/256))}
 for _,y in ipairs(rgbscanlines) do
  for x=0,255 do
   local r,g,b=emu.getscreenpixel(x,y,true)
   for _,v in ipairs({r,g,b}) do
    assert(type(v)=='number' and v==math.floor(v) and v>=0 and v<=255,
           'FCEUX source RGB channel unavailable')
   end
   buffer[#buffer+1]=string.char(r,g,b)
  end
 end
 assert(rgbfile:write(table.concat(buffer)),'private RGB sample write failed')
 rgbslots=rgbslots+1
end
assert(events:write('frame\tseq\ttype\taddress\tsize\tvalue\tpc\topcode\ta\tx\ty\tcycle\n'))
assert(frameclock:write('frame\tbegin_cycle\tend_cycle\n'))
local counts={R2002=0,W2000=0,W2001=0,W2002=0,W2005=0,W2006=0}
local seq=0
local first,last=600,920
local frame_starts={}
local records,writes={},{}
local writer_total,road_samples=0,0
local frame_rows=0
local last_after=nil
local function emit(kind,address,size,value,pc,opcode)
 local frame=emu.framecount()
 if frame<first or frame>last then return end
 local a,x,y=memory.getregister('a'),memory.getregister('x'),memory.getregister('y')
 local cycle=debugger.getcyclescount()
 assert(type(pc)=='number' and type(cycle)=='number' and cycle>=0,
        'source CPU provenance unavailable')
 seq=seq+1; counts[kind]=counts[kind]+1
 assert(events:write(string.format('%d\t%d\t%s\t%04X\t%d\t%s\t%04X\t%02X\t%02X\t%02X\t%02X\t%.0f\n',
  frame,seq,kind,address,size,value,pc,opcode,a,x,y,cycle)))
end
-- This FCEUX build lacks memory.registerread. Hook direct/indexed $2002
-- candidates found in original PRG banks, verify live opcodes, and require
-- X/Y=0 for indexed reads. No ROM bytes or register values are printed.
-- Offsets are local to an 8 KiB PRG bank; MMC3 can map banks to four slots.
local slot_bases={0x8000,0xA000,0xC000,0xE000}
local read_offsets={0x001E,0x1EA8,0x03AC,0x03B1,0x03C7,0x062E,0x0659,
                     0x069A,0x070E,0x072E,0x08E7,0x0923,0x0928,
                     0x1218,0x1434,0x1522,0x1D01}
local registered={}
for _,base in ipairs(slot_bases) do
 for _,off in ipairs(read_offsets) do
  local pc=base+off
  if not registered[pc] then
   registered[pc]=true
   memory.registerexec(pc,function()
    local here=memory.getregister('pc')
    local op=memory.readbyte(here)
    if memory.readbyte(here+1)==0x02 and memory.readbyte(here+2)==0x20 then
     local x,y=memory.getregister('x'),memory.getregister('y')
     local direct=(op==0xAD or op==0x2C or op==0xCE)
     local indexed=(op==0x19 and y==0) or
                   ((op==0xDD or op==0x1F) and x==0)
     if direct or indexed then emit('R2002',0x2002,1,'--',here,op) end
    end
   end)
  end
 end
end
-- The registerwrite callback does not provide a reliable instruction PC
-- across FCEUX builds. Bind each observed $2005 bus write to the known
-- pre-instruction execution hook, then record the instruction's post-PC.
local active_scroll_writer=nil
local writer_specs={
 {0xE8EC,0xE8EF,'a',0x8D},
 {0xE8F1,0xE8F4,'a',0x8D},
 {0xE369,0xE36C,'x',0x8E},
 {0xE36C,0xE36F,'x',0x8E},
}
local function register_scroll_writer(before_pc,after_pc,register_name,expected_opcode)
 memory.registerexec(before_pc,function()
  local frame=emu.framecount()
  if frame<first or frame>last then active_scroll_writer=nil;return end
  assert(memory.readbyte(before_pc)==expected_opcode and
         memory.readbyte(before_pc+1)==0x05 and
         memory.readbyte(before_pc+2)==0x20,
         'original scroll-writer instruction bytes changed')
  local value=memory.getregister(register_name)
  local cycle=debugger.getcyclescount()
  assert(type(value)=='number' and value==math.floor(value) and
         value>=0 and value<=255 and
         type(cycle)=='number' and cycle>=0,
         'original scroll-writer execution context invalid')
  local row=records[frame]
  if not row then row={};records[frame]=row end
  row[#row+1]={pc=before_pc,cycle=cycle,value=value}
  active_scroll_writer={frame=frame,pc=after_pc,value=value,cycle=cycle}
 end)
end
for _,spec in ipairs(writer_specs) do
 register_scroll_writer(spec[1],spec[2],spec[3],spec[4])
end
for _,spec in ipairs({{0x2000,'W2000'},{0x2001,'W2001'},
                       {0x2002,'W2002'},{0x2005,'W2005'},{0x2006,'W2006'}}) do
 local address,kind=spec[1],spec[2]
 memory.registerwrite(address,function(a,s,v)
  local frame=emu.framecount()
  -- The source game writes these ports outside the audited window too.
  -- Ignore those writes before enforcing the window-specific CPU witness.
  if frame<first or frame>last then return end
  local pc=memory.getregister('pc')
  if kind=='W2005' then
   local writer=active_scroll_writer
   local cycle=debugger.getcyclescount()
   assert(writer and writer.frame==frame and writer.value==v,
          'actual $2005 bus write lacks matching CPU instruction witness')
   assert(type(cycle)=='number' and cycle>=writer.cycle and
          cycle-writer.cycle<=16,
          'actual $2005 bus write is outside its instruction cycle window')
   pc=writer.pc
   local row=writes[frame]
   if not row then row={};writes[frame]=row end
   row[#row+1]=v
   active_scroll_writer=nil
  else
   active_scroll_writer=nil
  end
  emit(kind,a,s,string.format('%02X',v),pc,0)
 end)
end
emu.registerbefore(function()
 local frame=emu.framecount()
 if frame<first or frame>last then return end
 assert(frame_starts[frame]==nil,'duplicate source frame-begin callback')
 local cycle=debugger.getcyclescount()
 assert(type(cycle)=='number' and cycle>=0 and cycle==math.floor(cycle),
        'invalid source frame-begin CPU cycle')
 frame_starts[frame]=cycle
end)
emu.registerafter(function()
 local frame=emu.framecount()
 if last_after==frame then return end
 if last_after==nil then assert(frame<=1,'first callback began late')
 else assert(frame==last_after+1,'source frame callback skipped or reordered') end
 last_after=frame
 if frame>=first and frame<=last then
  local begin=frame_starts[frame]
  local finish=debugger.getcyclescount()
  assert(type(begin)=='number' and type(finish)=='number' and finish>begin,
         'missing or reversed source frame clock')
  assert(frameclock:write(string.format('%d\t%.0f\t%.0f\n',frame,begin,finish)))
  local source=records[frame] or {}
  local actual=writes[frame] or {}
  local pcs={0xE8EC,0xE8F1,0xE369,0xE36C}
  assert(#source==4 and #actual==4,'source CPU/PPU writer coverage is not four per frame')
  for i=1,4 do
   assert(source[i].pc==pcs[i],'source CPU writer PC sequence changed')
   assert(source[i].value==actual[i],'CPU writer value differs from actual PPU port write')
   assert(roadwriter:write(string.format('%d\t%d\t%04X\t%02X\t%.0f\n',frame,i,source[i].pc,source[i].value,source[i].cycle)))
  end
  assert(source[1].value==0 and source[3].value==0 and source[4].value==0,
         'original four-write value pattern changed')
  assert(source[2].cycle-source[1].cycle==7 and source[4].cycle-source[3].cycle==4,
         'original CPU writer pair phase changed')
  assert(source[1].cycle<=source[2].cycle and source[2].cycle<source[3].cycle and
         source[3].cycle<=source[4].cycle,'source CPU writer phases reordered')
  assert(begin<=source[1].cycle and source[4].cycle<=finish,
         'source CPU writer lies outside the frame clock')
  local ram0d=memory.readbyte(0x0D)
  assert(type(ram0d)=='number' and ram0d==math.floor(ram0d) and
         ram0d>=0 and ram0d<=255,'invalid private postframe RAM $0D')
  assert(ramfile:write(string.format('%d\t%02X\t4\n',frame,ram0d)))
  if frame%8==0 then capture_rgb(frame) end
  records[frame]=nil;writes[frame]=nil
  writer_total=writer_total+4;road_samples=road_samples+1
  frame_starts[frame]=nil
  frame_rows=frame_rows+1
 end
 if frame==last then
  assert(frame_rows==321 and seq==10203 and writer_total==1284 and
         road_samples==321 and rgbslots==41,
         'full same-session road/CPU/PPU/RGB evidence window missing')
  assert(movie.readonly() and movie.length()==movie_frames and
         rom.gethash('md5'):lower()==md5,'source identity changed during trace')
  assert(events:flush() and events:close() and
         countsfile:write('frames=321\nfirst=600\nlast=920\n'))
  for _,k in ipairs({'R2002','W2000','W2001','W2002','W2005','W2006'}) do
   assert(countsfile:write(k..'='..counts[k]..'\n'))
  end
  assert(countsfile:write('frame_clock_rows='..frame_rows..'\ntotal_events='..seq..'\ncpu_writer_events='..writer_total..'\npostframe_ram_samples='..road_samples..'\nrgb_slots='..rgbslots..'\nsource_values_disclosed=no\n'))
  assert(countsfile:close() and frameclock:flush() and frameclock:close() and
         roadwriter:flush() and roadwriter:close() and ramfile:flush() and ramfile:close() and
         rgbfile:flush() and rgbfile:close())
  local f=exclusive('COMPLETE.txt')
  assert(f:write('format=private_road_ppu_latch_rgb321_v1\nframes=321\nevents='..seq..
   '\nframe_clock_rows='..frame_rows..'\ncpu_writer_events='..writer_total..
   '\npostframe_ram_samples='..road_samples..'\nrgb_slots='..rgbslots..
   '\nrom_identity_verified=yes\nmovie_readonly_verified=yes\nsource_values_disclosed=no\n'))
  assert(f:close())
  emu.pause()
 end
end)
