-- Stage76: synthetic PPU capture must invalidate stale per-frame metadata.
-- No original ROM, visual assets or hardware data involved.
local dir=os.tmpname()
os.remove(dir)
assert(os.execute('mkdir -p "'..dir..'"'))
VPD_CAPTURE_DIRECTORY=dir
VPD_CAPTURE_INTERVAL=1
VPD_CAPTURE_LIMIT=1
VPD_CAPTURE_SCREEN=false
local frame=1
local bad_ppu=true
local after,exit
local ppu_data=string.rep(string.char(0x55),0x4000)
local ram_data=string.rep(string.char(0x11),0x0800)
emu={
  framecount=function()return frame end,
  registerafter=function(fn)after=fn end,
  registerexit=function(fn)exit=fn end,
  message=function()end,
}
memory={
  registerwrite=function(addr,size,fn)
    assert(type(fn)=='function')
    assert((addr==0x8000 and size==0x8000) or
           (addr==0x2000 and size==0x2000))
  end,
  registerread=function(addr,size,fn)
    assert(addr==0x2000 and size==0x2000 and type(fn)=='function')
  end,
  readbyte=function()return 0 end,
  readbyterange=function(a,size)
    assert(a==0 and size==0x0800)
    return ram_data
  end,
}
ppu={
  readbyterange=function(a,size)
    assert(a==0 and size==0x4000)
    return bad_ppu and 'invalid' or ppu_data
  end,
}
rom={gethash=function(k)assert(k=='md5');return string.rep('a',32)end}
local function write(path,value)
  local f=assert(io.open(path,'wb'))
  assert(f:write(value));assert(f:close())
end
local function read(path)
  local f=assert(io.open(path,'rb'))
  local s=f:read('*a');assert(f:close());return s
end
local first=dir..'/frame_000001'
local second=dir..'/frame_000002'
write(first..'.meta.txt','format=old_completed_snapshot\n')
write(first..'.ppu.bin','previous-ppu')
write(second..'.meta.txt','format=old_completed_snapshot\n')
dofile('tools/capture_fceux_ppu.lua')
assert(type(after)=='function' and type(exit)=='function')
assert(read(dir..'/ppu_capture_session.meta.txt')=='capture_in_progress=yes\n')
local ok,err=pcall(after)
assert(not ok and tostring(err):find('16384%-byte string'),
       'Invalid PPU capture should have failed: '..tostring(err))
assert(read(first..'.meta.txt')=='capture_in_progress=yes\n')
assert(read(first..'.ppu.bin')=='previous-ppu')
assert(read(dir..'/ppu_capture_session.meta.txt')=='capture_in_progress=yes\n')
frame=2;bad_ppu=false
after()
local meta=read(second..'.meta.txt')
assert(meta:find('format=fceux_ppu_snapshot_v4',1,true))
assert(not meta:find('capture_in_progress',1,true))
assert(read(second..'.ppu.bin')==ppu_data)
assert(read(second..'.ram.bin')==ram_data)
exit()
local session=read(dir..'/ppu_capture_session.meta.txt')
assert(session:find('format=fceux_ppu_session_v1',1,true))
assert(session:find('complete=no',1,true))
assert(session:find('capture_failures=1',1,true))
assert(session:find('frames_captured=1',1,true))
for _,name in ipairs({
  'frame_000001.meta.txt','frame_000001.ppu.bin',
  'frame_000002.meta.txt','frame_000002.ppu.bin',
  'frame_000002.ram.bin','mmc3_video_writes.tsv',
  'ppu_capture_session.meta.txt',
}) do os.remove(dir..'/'..name) end
assert(os.execute('rmdir "'..dir..'"'))
print('Stage76 PPU per-frame stale metadata invalidation PASS')
