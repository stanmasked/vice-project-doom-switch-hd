-- Private FCEUX CPU execution callbacks for fixed-bank $2005 store candidates.
-- Never publish owner ROM/FM2 or local execution TSV.
local function required(name)
  local value=os.getenv(name)
  assert(type(value)=="string" and #value>0,name.." is required")
  return value
end
local root=required("VPD_PRIVATE_WRITER_OUTPUT_DIR")
local movie_path=required("VPD_PRIVATE_FM2_PATH")
local digest=required("VPD_PRIVATE_ROM_PAYLOAD_MD5"):lower()
local frames=tonumber(required("VPD_PRIVATE_FRAME_COUNT"))
local start=tonumber(required("VPD_PRIVATE_WRITER_START_FRAME"))
local stop=tonumber(required("VPD_PRIVATE_WRITER_STOP_FRAME"))
assert(frames and frames==math.floor(frames) and frames>=2)
assert(start and stop and start==math.floor(start) and stop==math.floor(stop)
       and start>=1 and stop>=start and stop<frames and stop-start<=1200)
assert(#digest==32 and not digest:find("[^0-9a-f]"))
assert(type(memory.registerexec)=="function")
assert(type(debugger.getcyclescount)=="function")
assert(rom.gethash("md5"):lower()==digest)
assert(movie.play(movie_path,true) and movie.readonly() and movie.length()==frames)
local function new_file(name)
  local filename=root.."/"..name
  local old=io.open(filename,"rb")
  if old then old:close();error("private writer output already exists")end
  return assert(io.open(filename,"wb"))
end
local out=new_file("pc_2005_writer_candidates.tsv")
assert(out:write("frame\tcycle\tpc\n"))
-- Candidate source addresses validated by the separate fixed-bank PRG audit.
-- Registering a candidate never implies that address actually executes.
local pcs={0xE25E,0xE261,0xE2BC,0xE2BF,0xE319,0xE31E,0xE369,
           0xE36C,0xE84F,0xE854,0xE86E,0xE873,0xE892,0xE897,
           0xE8EC,0xE8F1}
local hits,first,last=0,nil,nil
local done=false
for _,pc in ipairs(pcs) do
  memory.registerexec(pc,function()
    local frame=emu.framecount()
    if frame<start or frame>stop then return end
    local cycle=debugger.getcyclescount()
    assert(type(cycle)=="number" and cycle==math.floor(cycle) and cycle>=0)
    assert(out:write(string.format("%d\t%.0f\t%04X\n",frame,cycle,pc)))
    hits=hits+1
  end)
end
emu.registerafter(function()
  if done then return end
  local f=emu.framecount()
  if last==f then return end
  assert(type(f)=="number" and f==math.floor(f) and f>=0 and f<frames)
  if first==nil then
    assert(f<=1,"private FM2 hook attached late");first=f
  else
    assert(f==last+1,"movie callback sequence not contiguous")
  end
  last=f
  if f==stop then
    assert(movie.readonly() and movie.length()==frames and
           rom.gethash("md5"):lower()==digest)
    assert(out:flush() and out:close())
    local complete=new_file("COMPLETE.txt")
    assert(complete:write("format=private_ppuscroll_writer_pc_v1\n"..
          "first_observed_frame="..first.."\n"..
          "last_observed_frame="..last.."\n"..
          "frame_gaps=0\n"..
          "writer_pc_hits="..hits.."\n"..
          "rom_identity_verified=yes\n"..
          "movie_readonly_verified=yes\n"))
    assert(complete:close())
    done=true
  end
end)
