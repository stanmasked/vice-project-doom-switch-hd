-- Stage77: ROM-free full MMC3 $8000-$FFFF mirrored video callback probe.
local dir=os.tmpname()
os.remove(dir)
assert(os.execute('mkdir -p "'..dir..'"'))
VPD_CAPTURE_DIRECTORY=dir
VPD_CAPTURE_INTERVAL=1
VPD_CAPTURE_LIMIT=1
VPD_CAPTURE_SCREEN=false
local hooks,after,exit={},nil,nil
local mwrite
local ppu_data=string.rep(string.char(0x55),0x4000)
local ram_data=string.rep(string.char(0x11),0x0800)
memory={
 registerwrite=function(address,size_or_fn,fn)
  if fn~=nil then
    assert(address==0x8000 and size_or_fn==0x8000 and not mwrite)
    mwrite=fn
  else
    hooks[address]=size_or_fn
  end
 end,
 registerread=function(address,fn)assert(address==0x2002 and type(fn)=='function')end,
 readbyte=function()return 0 end,
 readbyterange=function(a,size)
   assert(a==0 and size==0x0800)
   return ram_data
 end,
}
ppu={readbyterange=function(a,size)
 assert(a==0 and size==0x4000)
 return ppu_data
end}
rom={gethash=function(which)
 assert(which=='md5')
 return string.rep('a',32)
end}
emu={
 framecount=function()return 1 end,
 registerafter=function(fn)after=fn end,
 registerexit=function(fn)exit=fn end,
 message=function()end,
}
dofile('tools/capture_fceux_ppu.lua')
assert(type(mwrite)=='function' and type(after)=='function' and type(exit)=='function')
assert(type(hooks[0x2000])=='function')
assert(hooks[0x8000]==nil and hooks[0xA000]==nil)
mwrite(0x8002,1,0x80)  -- R0, inversion
mwrite(0x8003,1,0x06)  -- CHR R0
mwrite(0x9FFE,1,0x85)  -- R5
mwrite(0x9FFF,1,0x24)  -- CHR R5
mwrite(0xA002,1,0x01)  -- nametable mirroring
mwrite(0xBFFF,1,0x80)  -- PRG RAM protection
mwrite(0xC006,1,0x0B)  -- IRQ latch
mwrite(0xDFFF,1,0x12)  -- IRQ reload
mwrite(0xE00E,1,0x34)  -- IRQ disable
mwrite(0xFFFF,1,0x56)  -- IRQ enable
hooks[0x2000](0x2000,1,0x90)
after()
local function read(path)
 local f=assert(io.open(path,'rb'))
 local data=f:read('*a');assert(f:close());return data
end
local meta=read(dir..'/frame_000001.meta.txt')
assert(meta:find('mmc3_write_coverage=full_8000_ffff_even_odd',1,true))
assert(meta:find('callback_errors=0',1,true))
assert(meta:find('register_log_complete=yes',1,true))
assert(meta:find('mmc3_select=85',1,true))
assert(meta:find('chr_r0=06',1,true))
assert(meta:find('chr_r5=24',1,true))
assert(meta:find('ppuctrl=90',1,true))
local log=read(dir..'/mmc3_video_writes.tsv')
for _,fragment in ipairs({
 '8002\t80','8003\t06','9FFE\t85','9FFF\t24',
 'A002\t01','BFFF\t80','C006\t0B','DFFF\t12',
 'E00E\t34','FFFF\t56'
}) do
 assert(log:find(fragment,1,true),fragment)
end
exit()
for _,name in ipairs({
 'frame_000001.meta.txt','frame_000001.ppu.bin',
 'frame_000001.ram.bin','mmc3_video_writes.tsv'
}) do os.remove(dir..'/'..name) end
assert(os.execute('rmdir "'..dir..'"'))
print('Stage77 FCEUX MMC3 all-four-pairs mirrored video callbacks PASS')
