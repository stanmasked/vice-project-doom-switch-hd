-- Only for synthetic test ROM generated in ephemeral GitHub runner.
VPD_STORYBOARD_DIRECTORY=assert(os.getenv("VPD_SMOKE_DIRECTORY"))
VPD_STORYBOARD_START_FRAME=8
VPD_STORYBOARD_STOP_FRAME=16
VPD_STORYBOARD_INTERVAL=8
VPD_STORYBOARD_LIMIT=2
dofile("tools/capture_fceux_movie_storyboard.lua")
