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
       type(emu.registerafter)=="function")
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
assert(writer:write("frame\tordinal\tpc\tvalue\tcycle\n"))
assert(ram:write("frame\tram_0d\tppu_2005_writes\n"))
local pcs={0xE8EC,0xE8F1,0xE369,0xE36C}
local records,writes={},{}
local first,last=nil,nil
local captured,write_total,samples=0,0,0
local done=false
for _,pc in ipairs(pcs) do
  memory.registerexec(pc,function()
    local frame=emu.framecount()
    if frame<600 or frame>920 then return end
    local cycle=debugger.getcyclescount()
    local value=memory.getregister("a")
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
    local ram0d=memory.readbyte(0x0D)
    assert(type(ram0d)=="number" and ram0d==math.floor(ram0d) and
           ram0d>=0 and ram0d<=255,"invalid private postframe RAM $0D")
    for i=1,4 do
      local event=source[i]
      assert(writer:write(string.format("%d\t%d\t%04X\t%02X\t%.0f\n",
                           frame,i,event.pc,event.value,event.cycle)))
    end
    assert(ram:write(string.format("%d\t%02X\t4\n",frame,ram0d)))
    records[frame]=nil
    writes[frame]=nil
    captured=captured+4
    write_total=write_total+4
    samples=samples+1
  end
  if frame==920 then
    assert(samples==321 and captured==1284 and write_total==1284,
           "full original CPU writer coverage not achieved")
    assert(movie.readonly() and movie.length()==movie_frames and
           rom.gethash("md5"):lower()==md5,
           "private ROM/movie identity changed during capture")
    assert(writer:flush() and writer:close() and
           ram:flush() and ram:close(),"private numerical file close failed")
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
