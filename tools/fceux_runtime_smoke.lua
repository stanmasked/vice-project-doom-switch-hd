-- Only for synthetic test ROM generated in ephemeral GitHub runner.
VPD_STORYBOARD_DIRECTORY=assert(os.getenv("VPD_SMOKE_DIRECTORY"))
VPD_STORYBOARD_START_FRAME=8
VPD_STORYBOARD_STOP_FRAME=16
VPD_STORYBOARD_INTERVAL=8
VPD_STORYBOARD_LIMIT=2
local storyboard=assert(os.getenv("VPD_STORYBOARD_SCRIPT"),
  "VPD_STORYBOARD_SCRIPT must be an absolute path")
assert(storyboard:sub(1,1)=="/","VPD_STORYBOARD_SCRIPT must be absolute")
dofile(storyboard)
