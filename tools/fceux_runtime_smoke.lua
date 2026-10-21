-- Only for synthetic test ROM generated in ephemeral GitHub runner.
VPD_STORYBOARD_DIRECTORY=assert(os.getenv("VPD_SMOKE_DIRECTORY"))
VPD_STORYBOARD_START_FRAME=8
VPD_STORYBOARD_STOP_FRAME=16
VPD_STORYBOARD_INTERVAL=8
VPD_STORYBOARD_LIMIT=2
local storyboard=assert(os.getenv("VPD_STORYBOARD_SCRIPT"),
  "VPD_STORYBOARD_SCRIPT must be an absolute path")
assert(storyboard:sub(1,1)=="/","VPD_STORYBOARD_SCRIPT must be absolute")
-- Load an invented FM2 in strict read-only mode. No original game is used.
local movie_path=assert(os.getenv("VPD_SMOKE_MOVIE"))
local witness_path=assert(os.getenv("VPD_SMOKE_WITNESS"))
assert(type(movie)=='table' and type(movie.play)=='function' and
       type(movie.active)=='function',"FCEUX movie Lua API is missing")
assert(movie.play(movie_path,true),"FCEUX rejected the invented FM2")
local verified=false
local input_idle_seen=false
local input_held_seen=false
assert(type(memory)=='table' and type(memory.readbyte)=='function',
       "FCEUX native RAM read API missing")
-- Compose callbacks: FCEUX may allow only one after-frame registration.
local original_after=emu.registerafter
emu.registerafter=function(production_callback)
    return original_after(function()
        production_callback()
        local frame=emu.framecount()
        if frame>=8 and frame<=16 then
            assert(movie.active(),"FM2 not active at expected movie frame")
            assert(movie.mode()=="playback","FM2 is not in playback mode")
            assert(movie.readonly(),"FM2 must remain read-only")
            assert(movie.length()==64,"FM2 length differs from invented input")
        end
        -- Counter-check the *actual 6502 input port*: the invented ROM
        -- continuously latches $4016 and mirrors the A bit into RAM $0000.
        -- FM2 has A released through frame 11, then held on frames 12..23.
        -- Sampling frame 8 and 16 avoids any boundary off-by-one ambiguity.
        if frame==8 then
            assert(memory.readbyte(0x0000)==0,
                   "synthetic NES CPU observed A held before FM2 press")
            input_idle_seen=true
        elseif frame==16 then
            assert(memory.readbyte(0x0000)==1,
                   "synthetic NES CPU did not observe recorded FM2 A press")
            input_held_seen=true
        end
        if frame==16 and not verified then
            assert(input_idle_seen and input_held_seen,
                   "missing native NES controller-read witnesses")
            verified=true
            local file=assert(io.open(witness_path,"wb"))
            assert(file:write("movie_loaded=yes\nmovie_mode=playback\n"..
                              "movie_readonly=yes\nmovie_frames=64\n"..
                              "witness_frame=16\n"..
                              "cpu_ram_a_at_frame_8=0\n"..
                              "cpu_ram_a_at_frame_16=1\n"..
                              "controller_evidence=cpu_4016_to_zero_page\n"..
                              "original_game_proven=no\n"))
            assert(file:close())
        end
    end)
end
dofile(storyboard)
emu.registerafter=original_after
