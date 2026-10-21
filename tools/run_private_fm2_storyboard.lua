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
VPD_STORYBOARD_DIRECTORY=directory
VPD_STORYBOARD_START_FRAME=interval
VPD_STORYBOARD_STOP_FRAME=frames-1
VPD_STORYBOARD_INTERVAL=interval
VPD_STORYBOARD_LIMIT=limit
local seen_movie=false
local timeline_end=false
local after=emu.registerafter
emu.registerafter=function(capture)
  return after(function()
    capture()
    local current=emu.framecount()
    if current>=1 and current<frames-1 then
      assert(movie.active(),"movie stopped before requested terminal frame")
      assert(movie.mode()=="playback","movie exited playback prematurely")
      assert(movie.readonly(),"movie unexpectedly became writable")
      assert(movie.length()==frames,"movie length changed during playback")
      seen_movie=true
    end
    if current==frames-1 and not timeline_end then
      assert(seen_movie,"no movie playback witness before terminal frame")
      assert(movie.readonly(),"movie writable at terminal frame")
      assert(movie.length()==frames,"movie length changed")
      local mode=movie.mode()
      assert(mode=="playback" or mode=="finished",
             "movie did not reach a permitted terminal state")
      timeline_end=true
      local prior=io.open(witness,"rb")
      if prior then prior:close();error("private terminal witness already exists") end
      local f=assert(io.open(witness,"wb"))
      assert(f:write("format=private_fm2_terminal_witness_v1\n"..
                     "movie_readonly=yes\n"..
                     "movie_terminal_frame="..tostring(current).."\n"..
                     "movie_frame_count="..tostring(frames).."\n"..
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
