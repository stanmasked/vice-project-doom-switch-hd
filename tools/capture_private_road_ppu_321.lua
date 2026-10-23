-- Stage181: owner-private complete Stage1-1 CPU writer trace, 600..920.
-- NEVER COMMIT raw output, ROM, FM2, original art or local source paths.
-- Raw CPU $2005 values do NOT establish effective PPU display scroll.
local function required(name)
  local s=os.getenv(name)
  assert(type(s)=="string" and #s>0,name.." missing")
  return s
end
local root=required("VPD_PRIVATE_PPU321_OUTPUT_DIR")
local fm2=required("VPD_PRIVATE_FM2_PATH")
local md5=required("VPD_PRIVATE_ROM_PAYLOAD_MD5"):lower()
local movie_frames=tonumber(required("VPD_PRIVATE_FRAME_COUNT"))
assert(#md5==32 and not md5:find("[^0-9a-f]"),"invalid ROM MD5 contract")
assert(movie_frames and movie_frames==math.floor(movie_frames) and
       movie_frames>920 and movie_frames<=100000000,"invalid FM2 length")
assert(type(memory)=="table" and type(memory.registerexec)=="function" and
       type(memory.registerwrite)=="function" and
       type(memory.getregister)=="function" and
       type(memory.readbyte)=="function","FCEUX CPU hooks missing")
assert(type(debugger)=="table" and type(debugger.getcyclescount)=="function",
       "CPU clock callback missing")
assert(type(emu)=="table" and type(emu.framecount)=="function" and
       type(emu.registerafter)=="function" and
       type(emu.registerbefore)=="function" and
       type(emu.getscreenpixel)=="function",
       "FCEUX CPU frame-begin boundary hook unavailable")
assert(type(movie)=="table" and type(movie.play)=="function" and
       type(movie.length)=="function" and type(movie.readonly)=="function")
assert(rom.gethash("md5"):lower()==md5,"private ROM identity mismatch")
assert(movie.play(fm2,true) and movie.readonly() and
       movie.length()==movie_frames,"read-only FM2 mismatch")
local function exclusive(name)
  local path=root.."/"..name
  local old=io.open(path,"rb")
  if old then old:close();error("raw private output already exists")end
  return assert(io.open(path,"wb"))
end
local writer=exclusive("road_321_writers.tsv")
local ram=exclusive("road_321_postframe.tsv")
local frame_clock=exclusive("road_321_frame_clock.tsv")
local rgbfile=exclusive("road_321_rgb_scanlines.bin")
local rgbscanlines={120,140,160,180}
local rgbslots=0
-- Versioned private packet header: magic, count=41, width=256,
-- rows=4, reserved=0, fixed source NES y indices.
assert(rgbfile:write("VPDRGB41"..string.char(
  41,0,0,1,4,0,0,0,120,140,160,180)))
local function capture_rgb(frame)
  assert(frame>=600 and frame<=920 and frame%8==0,
         "unexpected source RGB movie frame")
  local buffer={string.char(frame%256,math.floor(frame/256))}
  for _,y in ipairs(rgbscanlines) do
    for x=0,255 do
      local r,g,b=emu.getscreenpixel(x,y,true)
      for _,v in ipairs({r,g,b}) do
        assert(type(v)=="number" and v==math.floor(v) and
               v>=0 and v<=255,"FCEUX source RGB channel unavailable")
      end
      buffer[#buffer+1]=string.char(r,g,b)
    end
  end
  assert(rgbfile:write(table.concat(buffer)),"private RGB sample write failed")
  rgbslots=rgbslots+1
end
assert(frame_clock:write("frame\tbegin_cycle\tend_cycle\n"))
assert(writer:write("frame\tordinal\tpc\tvalue\tcycle\n"))
assert(ram:write("frame\tram_0d\tppu_2005_writes\n"))
local pcs={0xE8EC,0xE8F1,0xE369,0xE36C}
local records,writes,frame_starts={},{},{}
local first,last=nil,nil
local captured,write_total,samples=0,0,0
local last_frame_end_cycle=0
local done=false
for _,pc in ipairs(pcs) do
  memory.registerexec(pc,function()
    local frame=emu.framecount()
    if frame<600 or frame>920 then return end
    local cycle=debugger.getcyclescount()
    -- E8EC/E8F1 are STA $2005; E369/E36C are STX $2005.
    local register=(pc==0xE369 or pc==0xE36C) and "x" or "a"
    local value=memory.getregister(register)
    assert(type(cycle)=="number" and cycle>=0 and
           cycle==math.floor(cycle),"invalid CPU clock")
    assert(type(value)=="number" and value==math.floor(value) and
           value>=0 and value<=255,"invalid 6502 accumulator")
    local row=records[frame]
    if not row then row={};records[frame]=row end
    row[#row+1]={pc=pc,cycle=cycle,value=value}
  end)
end
memory.registerwrite(0x2005,function(_,__,value)
  local frame=emu.framecount()
  if frame<600 or frame>920 then return end
  assert(type(value)=="number" and value==math.floor(value) and
         value>=0 and value<=255,"invalid actual $2005 write")
  local row=writes[frame]
  if not row then row={};writes[frame]=row end
  row[#row+1]=value
end)
-- A real FCEUX frame-boundary clock is necessary: absolute CPU cycle
-- numbers alone must not be mistaken for a within-frame raster phase.
emu.registerbefore(function()
  if done then return end
  local frame=emu.framecount()
  if frame<600 or frame>920 then return end
  assert(frame_starts[frame]==nil,
         "duplicate FCEUX frame-begin timestamp")
  local count=debugger.getcyclescount()
  assert(type(count)=="number" and count==math.floor(count) and
         count>=0,"invalid FCEUX frame-begin CPU cycle")
  frame_starts[frame]=count
end)
emu.registerafter(function()
  if done then return end
  local frame=emu.framecount()
  assert(type(frame)=="number" and frame==math.floor(frame) and
         frame>=0 and frame<movie_frames,"invalid FCEUX callback frame")
  if last==frame then return end
  if first==nil then
    assert(frame<=1,"FM2 callback attached after beginning")
    first=frame
  else
    assert(frame==last+1,"skipped or reordered FM2 callback frame")
  end
  last=frame
  if frame>=600 and frame<=920 then
    local source=records[frame] or {}
    local actual=writes[frame] or {}
    local start_cycle=frame_starts[frame]
    local end_cycle=debugger.getcyclescount()
    assert(type(start_cycle)=="number" and
           type(end_cycle)=="number" and
           end_cycle==math.floor(end_cycle) and
           end_cycle>=0 and start_cycle<end_cycle,
           "missing, reversed or invalid FCEUX frame boundary")
    if frame>600 then
      assert(start_cycle>=last_frame_end_cycle,
             "CPU cycle counter epoch changed between movie frames")
    end
    assert(#source==4 and #actual==4,
           "source PC/write count differs from exactly four per frame")
    for i=1,4 do
      assert(source[i].pc==pcs[i],"actual original PC sequence changed")
      assert(source[i].value==actual[i],
             "CPU instruction A differs from actual $2005 port write")
    end
    assert(source[1].value==0 and source[3].value==0 and
           source[4].value==0,"actual four-write value pattern changed")
    assert(source[2].cycle-source[1].cycle==7 and
           source[4].cycle-source[3].cycle==4,
           "original pair CPU-cycle separation changed")
    assert(source[1].cycle<=source[2].cycle and
           source[2].cycle<source[3].cycle and
           source[3].cycle<=source[4].cycle,
           "CPU writer phases reordered")
    assert(start_cycle<=source[1].cycle and
           source[4].cycle<=end_cycle,
           "source CPU writer event outside this frame's boundaries")
    local ram0d=memory.readbyte(0x0D)
    assert(type(ram0d)=="number" and ram0d==math.floor(ram0d) and
           ram0d>=0 and ram0d<=255,"invalid private postframe RAM $0D")
    for i=1,4 do
      local event=source[i]
      assert(writer:write(string.format("%d\t%d\t%04X\t%02X\t%.0f\n",
                           frame,i,event.pc,event.value,event.cycle)))
    end
    assert(ram:write(string.format("%d\t%02X\t4\n",frame,ram0d)))
    assert(frame_clock:write(string.format("%d\t%.0f\t%.0f\n",
                                          frame,start_cycle,end_cycle)))
    -- The same original FCEUX post-frame callback produces BOTH the
    -- original CPU writer events and source image scanlines. This is a
    -- newly captured image source, not a post-hoc hash added to Stage170.
    if frame%8==0 then capture_rgb(frame) end
    last_frame_end_cycle=end_cycle
    frame_starts[frame]=nil
    records[frame]=nil
    writes[frame]=nil
    captured=captured+4
    write_total=write_total+4
    samples=samples+1
  end
  if frame==920 then
    assert(samples==321 and captured==1284 and write_total==1284 and
           rgbslots==41,"full original CPU writer and RGB coverage missing")
    assert(movie.readonly() and movie.length()==movie_frames and
           rom.gethash("md5"):lower()==md5,
           "private ROM/movie identity changed during capture")
    assert(writer:flush() and writer:close() and
           ram:flush() and ram:close() and
           frame_clock:flush() and frame_clock:close() and
           rgbfile:flush() and rgbfile:close(),
           "private numerical and RGB files close failed")
    local witness=exclusive("COMPLETE.txt")
    assert(witness:write(
          "format=private_road_ppu321_raw_v1\n"..
          "first_observed_frame="..first.."\n"..
          "last_observed_frame="..last.."\n"..
          "frame_gaps=0\n"..
          "frames_sampled="..samples.."\n"..
          "cpu_writer_events="..captured.."\n"..
          "registerwrite_2005_events="..write_total.."\n"..
          "postframe_ram_samples="..samples.."\n"..
          "movie_frames="..movie_frames.."\n"..
          "rom_identity_verified=yes\n"..
          "movie_readonly_verified=yes\n"))
    assert(witness:close())
    done=true
  end
end)
