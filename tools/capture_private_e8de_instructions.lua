-- PRIVATE original ROM/FM2 CPU instruction-execution witness, no source pixels.
-- Requires owner-local paths and ROM digest through environment variables.
local function required(name)
  local value=os.getenv(name)
  assert(type(value)=="string" and #value>0,name.." required")
  return value
end
local root=required("VPD_PRIVATE_EXEC_OUTPUT_DIR")
local movie_path=required("VPD_PRIVATE_FM2_PATH")
local identity=required("VPD_PRIVATE_ROM_PAYLOAD_MD5"):lower()
local frames=tonumber(required("VPD_PRIVATE_FRAME_COUNT"))
local start=tonumber(required("VPD_PRIVATE_EXEC_START_FRAME"))
local stop=tonumber(required("VPD_PRIVATE_EXEC_STOP_FRAME"))
assert(frames and frames==math.floor(frames) and frames>=2 and frames<=100000000)
assert(start and stop and start==math.floor(start) and stop==math.floor(stop) and
       start>=1 and stop>=start and stop<frames and stop-start<=1200,
       "private executable range invalid")
assert(#identity==32 and not identity:find("[^a-f0-9]"),"expected ROM identity invalid")
assert(type(memory)=="table" and type(memory.registerexec)=="function",
       "FCEUX CPU execution callback unavailable")
assert(type(debugger)=="table" and type(debugger.getcyclescount)=="function",
       "FCEUX CPU cycle clock unavailable")
assert(type(movie)=="table" and type(movie.play)=="function" and
       type(movie.readonly)=="function" and type(movie.length)=="function")
assert(rom.gethash("md5"):lower()==identity,"private ROM does not match")
assert(movie.play(movie_path,true),"private read-only FM2 playback failed")
assert(movie.readonly() and movie.length()==frames,"private FM2 identity mismatch")
assert(rom.gethash("md5"):lower()==identity,"loaded ROM changed")
local function unique_file(name)
  local file=root.."/"..name
  local existing=io.open(file,"rb")
  if existing then existing:close();error("private output already exists") end
  return assert(io.open(file,"wb"))
end
local output=unique_file("emitter_pc_exec.tsv")
assert(output:write("frame\tcycle\tpc\n"))
local positions={0xE8DE,0xE8E4,0xE8E7,0xE8EC,0xE8F1}
local counts={}
local events=0
for _,pc in ipairs(positions) do
  counts[pc]=0
  memory.registerexec(pc,function()
    local frame=emu.framecount()
    if frame<start or frame>stop then return end
    local cycle=debugger.getcyclescount()
    assert(type(cycle)=="number" and cycle==math.floor(cycle) and cycle>=0,
           "invalid CPU clock at instruction execution")
    assert(output:write(string.format("%d\t%.0f\t%04X\n",frame,cycle,pc)),
           "private PC trace write failed")
    counts[pc]=counts[pc]+1
    events=events+1
  end)
end
local first,last=nil,nil
local finished=false
emu.registerafter(function()
  if finished then return end
  local frame=emu.framecount()
  if last==frame then return end
  assert(type(frame)=="number" and frame==math.floor(frame) and
         frame>=0 and frame<frames,"invalid FCEUX frame")
  if first==nil then
    assert(frame<=1,"movie playback callback attached late")
    first=frame
  else
    assert(frame==last+1,"private FM2 frame callback jumped")
  end
  last=frame
  if frame==stop then
    for _,pc in ipairs(positions) do
      assert(counts[pc]==stop-start+1,"missing or duplicate emitter instruction callback")
    end
    assert(movie.readonly() and movie.length()==frames and
           rom.gethash("md5"):lower()==identity,"ROM or movie identity changed")
    assert(output:flush() and output:close(),"private PC file close failed")
    local witness=unique_file("COMPLETE.txt")
    assert(witness:write("format=private_e8de_instruction_trace_v1\n"..
                         "first_observed_frame="..first.."\n"..
                         "last_observed_frame="..last.."\n"..
                         "frame_gaps=0\n"..
                         "total_instruction_callbacks="..events.."\n"..
                         "rom_identity_verified=yes\n"..
                         "movie_readonly_verified=yes\n"))
    assert(witness:close(),"private execution witness close failed")
    finished=true
  end
end)
