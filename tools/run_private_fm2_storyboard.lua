-- Private FM2 full-run storyboard witness. NEVER run in public CI with a real ROM.
local function required_env(name)
  local v=os.getenv(name)
  assert(type(v)=="string" and #v>0, name.." is required")
  return v
end
local directory=required_env("VPD_PRIVATE_OUTPUT_DIR")
local movie_path=required_env("VPD_PRIVATE_FM2_PATH")
local source=required_env("VPD_PRIVATE_STORYBOARD_SCRIPT")
local witness=required_env("VPD_PRIVATE_WITNESS")
local expected_rom_md5=required_env("VPD_PRIVATE_ROM_PAYLOAD_MD5"):lower()
assert(required_env("VPD_PRIVATE_FM2_HEADER_POWERON_PREFLIGHT")=="yes",
       "FM2 header power-on preflight not confirmed")
assert(expected_rom_md5:match("^[0-9a-f]+$") and #expected_rom_md5==32,
       "expected private payload digest invalid")
assert(type(rom)=="table" and type(rom.gethash)=="function",
       "FCEUX ROM identity API unavailable")
local function check_rom()
  local actual=rom.gethash("md5")
  assert(type(actual)=="string" and actual:lower()==expected_rom_md5,
         "FCEUX loaded ROM does not match verified private PRG/CHR content")
end
check_rom()
local frames=tonumber(required_env("VPD_PRIVATE_FRAME_COUNT"))
local interval=tonumber(required_env("VPD_PRIVATE_CAPTURE_INTERVAL"))
local limit=tonumber(required_env("VPD_PRIVATE_CAPTURE_LIMIT"))
assert(frames and frames==math.floor(frames) and frames>=2 and frames<=100000000,
       "private frame count outside supported range")
assert(interval and interval==math.floor(interval) and interval>=1 and interval<=120000,
       "private interval outside supported range")
assert(limit and limit==math.floor(limit) and limit>=1 and limit<=64,
       "private sample count outside supported range")
assert(source:sub(1,1)=="/" and movie_path:sub(1,1)=="/",
       "source script and movie paths must be absolute")
assert(type(movie)=="table" and type(movie.play)=="function" and
       type(movie.active)=="function" and type(movie.mode)=="function" and
       type(movie.readonly)=="function" and type(movie.length)=="function",
       "real FCEUX movie API unavailable")
assert(movie.play(movie_path,true),"FCEUX refused private FM2 read-only playback")
assert(movie.length()==frames,"FCEUX loaded a different FM2 frame count")
assert(movie.readonly(),"private FM2 was not opened read-only")
-- FM2 power-on provenance is established by an independent strict
-- source file audit. FCEUX 2.6.5 movie.ispoweron Lua implementation is
-- unusable: it returns a Lua C result count without pushing a boolean.
check_rom()
local trace_script=os.getenv("VPD_PRIVATE_MMC3_TRACE_SCRIPT")
if trace_script~=nil and #trace_script>0 then
  assert(trace_script:sub(1,1)=="/","private CHR tracer path must be absolute")
  dofile(trace_script)
end
VPD_STORYBOARD_DIRECTORY=directory
VPD_STORYBOARD_START_FRAME=interval
VPD_STORYBOARD_STOP_FRAME=frames-1
VPD_STORYBOARD_INTERVAL=interval
VPD_STORYBOARD_LIMIT=limit
local seen_movie=false
local timeline_end=false
local first_observed_frame=nil
local last_observed_frame=nil
local consecutive_unique_frames=0
local after=emu.registerafter
emu.registerafter=function(capture)
  return after(function()
    capture()
    local current=emu.framecount()
    assert(type(current)=="number" and current==math.floor(current) and
           current>=0 and current<frames,"invalid FCEUX FM2 frame index")
    if last_observed_frame==nil then
      -- A Lua hook may attach at 0 or 1, but must not attach mid-movie.
      assert(current<=1,"FM2 callback attached after movie start")
      first_observed_frame=current
      consecutive_unique_frames=1
    elseif current~=last_observed_frame then
      assert(current==last_observed_frame+1,
             "FCEUX FM2 callback skipped, rewound or jumped a frame")
      consecutive_unique_frames=consecutive_unique_frames+1
    end
    last_observed_frame=current
    if current>=1 and current<frames-1 then
      assert(movie.active(),"movie stopped before requested terminal frame")
      assert(movie.mode()=="playback","movie exited playback prematurely")
      assert(movie.readonly(),"movie unexpectedly became writable")
      assert(movie.length()==frames,"movie length changed during playback")
      check_rom()
      seen_movie=true
    end
    if current==frames-1 and not timeline_end then
      assert(seen_movie,"no movie playback witness before terminal frame")
      assert(first_observed_frame==0 or first_observed_frame==1,
             "movie earliest observed callback missing")
      assert(last_observed_frame==frames-1 and
             consecutive_unique_frames==frames-first_observed_frame,
             "movie callback timeline is not contiguous through terminal frame")
      assert(movie.readonly(),"movie writable at terminal frame")
      assert(movie.length()==frames,"movie length changed")
      check_rom()
      local mode=movie.mode()
      assert(mode=="playback" or mode=="finished",
             "movie did not reach a permitted terminal state")
      -- Without a complete, closed mapper trace the movie terminal marker
      -- must not be issued as a positive mapping-capture witness.
      local finish_trace=rawget(_G,"VPD_FINALIZE_PRIVATE_MMC3_TRACE")
      if finish_trace~=nil then
        assert(type(finish_trace)=="function","invalid MMC3 trace finalizer")
        finish_trace(current)
      end
      timeline_end=true
      local prior=io.open(witness,"rb")
      if prior then prior:close();error("private terminal witness already exists") end
      local f=assert(io.open(witness,"wb"))
      assert(f:write("format=private_fm2_terminal_witness_v4\n"..
                     "loaded_rom_verified=yes\n"..
                     "fm2_header_power_on_preflight_verified=yes\n"..
                     "movie_readonly=yes\n"..
                     "movie_terminal_frame="..tostring(current).."\n"..
                     "movie_frame_count="..tostring(frames).."\n"..
                     "movie_first_observed_frame="..tostring(first_observed_frame).."\n"..
                     "movie_last_observed_frame="..tostring(last_observed_frame).."\n"..
                     "movie_consecutive_unique_frames="..tostring(consecutive_unique_frames).."\n"..
                     "movie_frame_gaps=0\n"..
                     "movie_active_before_terminal=yes\n"..
                     "movie_mode_at_terminal="..mode.."\n"..
                     "original_stage_proven=no\n"..
                     "game_completion_proven=no\n"))
      assert(f:close())
    end
  end)
end
dofile(source)
emu.registerafter=after
