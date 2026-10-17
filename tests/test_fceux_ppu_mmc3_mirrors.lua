-- Stage77: ROM-free full MMC3 $8000-$FFFF mirrored video callback probe.
local dir=os.tmpname()
os.remove(dir)
assert(os.execute('mkdir -p "'..dir..'"'))
VPD_CAPTURE_DIRECTORY=dir
VPD_CAPTURE_INTERVAL=1
VPD_CAPTURE_LIMIT=2
VPD_CAPTURE_SCREEN=false
local hooks,after,exit={},nil,nil
local current_frame=1
local status_read
local mwrite,ppuwrite
local ppu_data=string.rep(string.char(0x55),0x4000)
local ram_data=string.rep(string.char(0x11),0x0800)
memory={
 registerwrite=function(address,size_or_fn,fn)
  assert(type(fn)=='function')
  if address==0x8000 then
    assert(size_or_fn==0x8000 and not mwrite)
    mwrite=fn
  else
    assert(address==0x2000 and size_or_fn==0x2000 and not ppuwrite)
    ppuwrite=fn
  end
 end,
 registerread=function(address,size,fn)
  assert(address==0x2000 and size==0x2000 and type(fn)=='function')
  status_read=fn
 end,
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
debugger={getcyclescount=function()return 120 end}
rom={gethash=function(which)
 assert(which=='md5')
 return string.rep('a',32)
end}
emu={
 framecount=function()return current_frame end,
 registerafter=function(fn)after=fn end,
 registerexit=function(fn)exit=fn end,
 message=function()end,
}
dofile('tools/capture_fceux_ppu.lua')
assert(type(mwrite)=='function' and type(ppuwrite)=='function' and
       type(status_read)=='function' and type(after)=='function' and type(exit)=='function')
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
ppuwrite(0x2008,1,0x90) -- PPUCTRL mirror
ppuwrite(0x3FF9,1,0x1E) -- PPUMASK mirror
ppuwrite(0x200D,1,0x24) -- PPUSCROLL mirror
ppuwrite(0x3456,1,0x20) -- PPUADDR mirror
ppuwrite(0x200F,1,0x34) -- PPUDATA mirror
ppuwrite(0x2002,1,0x7F) -- ignored read-only PPUSTATUS write
status_read(0x2004,1,0) -- unrelated register read, no status marker
status_read(0x3FFA,1,0) -- mirrored PPUSTATUS: status marker
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
assert(meta:find('ppumask=1E',1,true))
assert(meta:find('ppu_register_write_coverage=full_2000_3fff_mod8',1,true))
assert(meta:find('ppu_status_read_coverage=full_2000_3fff_mod8',1,true))
assert(meta:find('cycle_trace_available=yes',1,true))
local log=read(dir..'/mmc3_video_writes.tsv')
for _,fragment in ipairs({
 '8002\t80','8003\t06','9FFE\t85','9FFF\t24',
 'A002\t01','BFFF\t80','C006\t0B','DFFF\t12',
 'E00E\t34','FFFF\t56',
 '2008\t90','3FF9\t1E','200D\t24','3456\t20','200F\t34','3FFA\t00'
}) do
 assert(log:find(fragment,1,true),fragment)
end
local timed=read(dir..'/mmc3_ppu_cycles.tsv')
assert(timed:find('\t3FFA\t00\tR',1,true))
assert(not timed:find('\t2002\t7F\tW',1,true))
-- A later frame must be tagged incomplete if malformed hooks fire.
current_frame=2
local ok,err=pcall(mwrite,0x8002,2,0x80)
assert(not ok and tostring(err):find('Unsupported FCEUX video callback contract',1,true))
ok,err=pcall(status_read,0x3FFA,1,0x80)
assert(not ok and tostring(err):find('Unsupported FCEUX video callback contract',1,true))
after()
local badmeta=read(dir..'/frame_000002.meta.txt')
assert(badmeta:find('callback_errors=2',1,true))
assert(badmeta:find('register_log_complete=no',1,true))
exit()
for _,name in ipairs({
 'frame_000001.meta.txt','frame_000001.ppu.bin',
 'frame_000001.ram.bin','frame_000002.meta.txt',
 'frame_000002.ppu.bin','frame_000002.ram.bin',
 'mmc3_video_writes.tsv','mmc3_ppu_cycles.tsv'
}) do os.remove(dir..'/'..name) end
assert(os.execute('rmdir "'..dir..'"'))
print('Stage77 FCEUX MMC3 all-four-pairs mirrored video callbacks PASS')
