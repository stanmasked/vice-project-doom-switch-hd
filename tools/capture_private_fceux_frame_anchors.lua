-- Private actual FCEUX after-frame CPU clock capture. Keep trace off GitHub.
local function required(name)
  local value=os.getenv(name)
  assert(type(value)=="string" and #value>0,name.." required")
  return value
end
local directory=required("VPD_PRIVATE_ANCHOR_OUTPUT_DIR")
local movie_path=required("VPD_PRIVATE_FM2_PATH")
local digest=required("VPD_PRIVATE_ROM_PAYLOAD_MD5"):lower()
local frames=tonumber(required("VPD_PRIVATE_FRAME_COUNT"))
local start=tonumber(required("VPD_PRIVATE_ANCHOR_START_FRAME"))
local stop=tonumber(required("VPD_PRIVATE_ANCHOR_STOP_FRAME"))
assert(frames and frames==math.floor(frames) and frames>=2)
assert(start and stop and start==math.floor(start) and stop==math.floor(stop)
       and start>=2 and stop>=start and stop<frames and stop-start<=1200)
assert(#digest==32 and not digest:find("[^0-9a-f]"))
assert(type(debugger.getcyclescount)=="function")
assert(rom.gethash("md5"):lower()==digest)
assert(movie.play(movie_path,true) and movie.readonly() and movie.length()==frames)
local function private_file(name)
  local filename=directory.."/"..name
  local prev=io.open(filename,"rb")
  if prev then prev:close();error("refusing existing private capture")end
  return assert(io.open(filename,"wb"))
end
local out=private_file("after_frame_cycles.tsv")
assert(out:write("frame\tcycle\n"))
local seen,last=nil,nil
local last_cycle=-1
local finished=false
emu.registerafter(function()
  if finished then return end
  local frame=emu.framecount()
  if frame==last then return end
  assert(type(frame)=="number" and frame==math.floor(frame) and
         frame>=0 and frame<frames)
  if seen==nil then
    assert(frame<=1,"movie callback attached after beginning")
    seen=frame
  else
    assert(frame==last+1,"frame-count callback skipped")
  end
  last=frame
  if frame>=start-1 and frame<=stop then
    local cycle=debugger.getcyclescount()
    assert(type(cycle)=="number" and cycle==math.floor(cycle) and
           cycle>last_cycle,"CPU clock epoch regressed")
    last_cycle=cycle
    assert(out:write(string.format("%d\t%.0f\n",frame,cycle)))
  end
  if frame==stop then
    assert(movie.readonly() and movie.length()==frames and
           rom.gethash("md5"):lower()==digest)
    assert(out:flush() and out:close())
    local witness=private_file("COMPLETE.txt")
    assert(witness:write("format=private_original_fceux_frame_anchor_v1\n"..
          "first_observed_frame="..seen.."\n"..
          "last_observed_frame="..last.."\n"..
          "frame_gaps=0\n"..
          "rom_identity_verified=yes\n"..
          "movie_readonly_verified=yes\n"))
    assert(witness:close())
    finished=true
  end
end)
