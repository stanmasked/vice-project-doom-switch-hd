-- ROM-free mock for post-terminal FCEUX callback handling.
-- Never needs a commercial ROM, input recording, or pixel capture.
local original_getenv=os.getenv
local original_dofile=dofile
local HASH=string.rep("a",32)

local function execute_case(name,frames,opts)
  opts=opts or {}
  local witness=os.tmpname().."_vpd_"..name..".txt"
  os.remove(witness)
  local env={
    VPD_PRIVATE_OUTPUT_DIR="/tmp/fabricated_callback_output",
    VPD_PRIVATE_FM2_PATH="/tmp/fabricated_callback.fm2",
    VPD_PRIVATE_STORYBOARD_SCRIPT="/tmp/fabricated_capture.lua",
    VPD_PRIVATE_WITNESS=witness,
    VPD_PRIVATE_ROM_PAYLOAD_MD5=HASH,
    VPD_PRIVATE_FM2_HEADER_POWERON_PREFLIGHT="yes",
    VPD_PRIVATE_FRAME_COUNT="32",
    VPD_PRIVATE_CAPTURE_INTERVAL="8",
    VPD_PRIVATE_CAPTURE_LIMIT="3"
  }
  os.getenv=function(k) return env[k] end
  local frame=0
  local hook=nil
  local capture_callbacks=0
  rom={gethash=function(which) assert(which=="md5");return HASH end}
  movie={
    play=function(path,readonly) assert(path==env.VPD_PRIVATE_FM2_PATH and readonly);return true end,
    active=function() return not(opts.stop_at and frame>=opts.stop_at) end,
    mode=function() return frame>=31 and "finished" or "playback" end,
    readonly=function() return true end,
    length=function() return 32 end
  }
  emu={
    framecount=function() return frame end,
    registerafter=function(callback) hook=callback end
  }
  dofile=function(path)
    if path==env.VPD_PRIVATE_STORYBOARD_SCRIPT then
      emu.registerafter(function() capture_callbacks=capture_callbacks+1 end)
    else
      return original_dofile(path)
    end
  end
  original_dofile("tools/run_private_fm2_storyboard.lua")
  assert(type(hook)=="function")
  local ok,err=pcall(function()
    for _,f in ipairs(frames) do frame=f;hook() end
  end)
  local file=io.open(witness,"rb")
  local contents=nil
  if file then contents=file:read("*a");file:close() end
  os.remove(witness)
  os.getenv=original_getenv
  dofile=original_dofile
  return ok,err,contents,capture_callbacks
end

local full={}
for i=1,31 do full[#full+1]=i end
for _,late in ipairs({32,33,40}) do full[#full+1]=late end
local ok,err,text,captures=execute_case("sealed",full)
assert(ok,tostring(err))
assert(text and text:find("movie_terminal_frame=31\n",1,true))
assert(text:find("movie_consecutive_unique_frames=31\n",1,true))
assert(text:find("movie_frame_gaps=0\n",1,true))
assert(captures==31,"late callbacks ran the original registered capture")

local gap,gap_error,gap_witness=execute_case("gap",{1,3})
assert(not gap and tostring(gap_error):find("skipped",1,true))
assert(gap_witness==nil,"frame discontinuity emitted a terminal witness")

local early,early_error,early_witness=execute_case("stopped",{1,2},{stop_at=2})
assert(not early and tostring(early_error):find("movie stopped",1,true))
assert(early_witness==nil,"early movie stop emitted a terminal witness")

print("PASS synthetic private FCEUX terminal: sealed callback ignored, preterminal gap/stop rejected")
