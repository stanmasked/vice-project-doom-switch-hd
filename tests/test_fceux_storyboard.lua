-- Synthetic FCEUX storyboard test; no original game data.
VPD_STORYBOARD_DIRECTORY=os.tmpname()..'_storyboard'
assert(os.execute('mkdir -p '..VPD_STORYBOARD_DIRECTORY))
VPD_STORYBOARD_START_FRAME=8
VPD_STORYBOARD_STOP_FRAME=16
VPD_STORYBOARD_INTERVAL=8
VPD_STORYBOARD_LIMIT=2
local frame,cb,pixels=0,nil,0
rom={gethash=function(which)assert(which=='md5');return string.rep('f',32)end}
emu={framecount=function()return frame end,
     registerafter=function(fn)cb=fn end,
     message=function(s)assert(type(s)=='string')end,
     getscreenpixel=function(x,y,raw)
       assert(raw==true and x>=0 and x<256 and y>=0 and y<240)
       pixels=pixels+1
       return x,y,42,((x+y)%17==0 and 254 or (x+y)%64)
     end}
dofile('tools/capture_fceux_movie_storyboard.lua')
for _,n in ipairs({0,8,8,12,16,24}) do frame=n;cb() end
local function read(name)
  local f=io.open(VPD_STORYBOARD_DIRECTORY..'/'..name,'rb')
  if not f then return nil end
  local data=f:read('*a');f:close();return data
end
assert(pixels==2*256*240)
assert(read('frame_000000.ppm')==nil)
assert(read('frame_000024.ppm')==nil)
local screen=assert(read('frame_000008.ppm'))
assert(screen:sub(1,15)=='P6\n256 240\n255\n')
assert(#screen==15+256*240*3)
assert(screen:sub(16,18)==string.char(0,0,42))
assert(#assert(read('frame_000016.pal.bin'))==256*240)
local meta=assert(read('frame_000008.meta.txt'))
assert(meta:find('frame=8\n',1,true))
assert(meta:find('interval=8\n',1,true))
assert(meta:find('start_frame=8\n',1,true))
assert(meta:find('stop_frame=16\n',1,true))
assert(meta:find('source=emu.getscreenpixel\n',1,true))
print('PASS synthetic private storyboard: two 256x240 frames')
assert(os.execute('rm -rf '..VPD_STORYBOARD_DIRECTORY))
