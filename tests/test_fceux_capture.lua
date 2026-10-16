-- Exercise the unmodified FCEUX capture script with synthetic API callbacks.
-- Requires Lua 5.4 interpreter on CI; captures contain invented data only.
VPD_CAPTURE_DIRECTORY=os.tmpname()..'_vice_capture'
assert(os.execute('mkdir -p '..VPD_CAPTURE_DIRECTORY))
local hooks={}
local read_hooks={}
local after, exit
local frame=0
memory={
 registerwrite=function(addr, cb) assert(not hooks[addr]);hooks[addr]=cb end,
 registerread=function(addr, cb) assert(not read_hooks[addr]);read_hooks[addr]=cb end,
 readbyterange=function(addr,n)assert(addr==0 and n==2048);return string.rep(string.char(0x42),n)end,
 readbyte=function(addr)return (addr*3)%256 end
}
ppu={readbyterange=function(addr,n)assert(addr==0 and n==16384);return string.rep(string.char(0x5A),n)end}
rom={gethash=function(which)assert(which=='md5');return 'abcd1234' end}
local sampled_pixels=0
local cpu_clock=100000
local without_clock=arg and arg[1]=='--no-clock'
local dense=arg and arg[1]=='--dense'
if dense then
  VPD_CAPTURE_INTERVAL=8
  VPD_CAPTURE_LIMIT=3
end
-- FCEUX debugger counts CPU cycles since power-on or counter reset.
if not without_clock then
 debugger={getcyclescount=function() cpu_clock=cpu_clock+3; return cpu_clock end}
end
emu={framecount=function()return frame end,
 registerafter=function(cb)after=cb end,
 registerexit=function(cb)exit=cb end,
 message=function(s)assert(type(s)=='string')end,
 getscreenpixel=function(x,y,raw)
  assert(raw==true and x>=0 and x<256 and y>=0 and y<240)
  sampled_pixels=sampled_pixels+1
  return x,y,42,((x+y)%17==0 and 254 or (x+y)%64)
 end}

dofile('tools/capture_fceux_ppu.lua')
assert(type(after)=='function' and type(exit)=='function')
assert(hooks[0x8000] and hooks[0x8001] and hooks[0x2000])
assert(type(read_hooks[0x2002])=='function')
local function write(addr,value) assert(hooks[addr]);hooks[addr](addr,1,value)end
write(0x8000,0x80);write(0x8001,0x14);write(0x2000,0x10)
read_hooks[0x2002](0x2002,1,0x80)
after()
frame=1
for n=1,12005 do write(0x2007,n%256) end
after()
if dense then
  frame=8
  after()
end
frame=120
write(0x8000,0);write(0x8001,6)
after()
exit()
local function read(path)
 local f=assert(io.open(path,'rb'));local s=f:read('*a');f:close();return s
end
local p=VPD_CAPTURE_DIRECTORY
assert(#read(p..'/frame_000000.ppu.bin')==16384)
assert(#read(p..'/frame_000120.ram.bin')==2048)
assert(sampled_pixels==(dense and 3 or 2)*256*240)
if dense then
 assert(#read(p..'/frame_000008.ppu.bin')==16384)
 assert(read(p..'/frame_000008.meta.txt'):find('capture_interval=8',1,true))
 assert(read(p..'/frame_000008.meta.txt'):find('capture_limit=3',1,true))
end
assert(#read(p..'/frame_000000.screen.rgb.bin')==256*240*3)
assert(#read(p..'/frame_000120.screen.pal.bin')==256*240)
assert(read(p..'/frame_000000.screen.rgb.bin'):sub(1,3)==string.char(0,0,42))
assert(read(p..'/frame_000000.screen.pal.bin'):byte(1)==254)
local text=read(p..'/frame_000120.meta.txt')
assert(text:find('format=fceux_ppu_snapshot_v4',1,true))
assert(text:find('dropped_register_writes=5',1,true),text)
assert(text:find('register_log_complete=no',1,true),text)
assert(text:find('chr_r0=06',1,true),text)
assert(text:find('screen_reference=yes',1,true),text)
assert(text:find('cycle_trace_available='..(without_clock and 'no' or 'yes'),1,true),text)
assert(text:find('invalid_screen_palette_values=',1,true),text)
assert(text:find('chr_ram_0=B7',1,true),text)
assert(text:find('scroll_emitter_ram_0b=21',1,true),text)
assert(text:find('scroll_emitter_ram_0c=24',1,true),text)
assert(text:find('scroll_emitter_ram_0d=27',1,true),text)
assert(text:find('scroll_emitter_provenance=static_emitter_e8de_not_confirmed_runtime',1,true))
if without_clock then
  assert(io.open(p..'/mmc3_ppu_cycles.tsv','rb')==nil,
         'Cycle log created without FCEUX debugger clock')
else
  local times=read(p..'/mmc3_ppu_cycles.tsv')
  assert(times:find('frame\tcpu_cycle\taddress\tvalue\tkind',1,true))
  assert(times:find('0\t100012\t2002\t00\tR',1,true),times:sub(1,240))
  assert(times:find('\t8001\t06\tW',1,true))
end
local log=read(p..'/mmc3_video_writes.tsv')
assert(log:find('frame\taddress\tvalue',1,true))
assert(log:find('0\t8001\t14',1,true))
assert(log:find('0\t2002\t00',1,true))
assert(log:find('120\t8001\t06',1,true))
print('PASS: FCEUX capture (CPU clock '..(without_clock and 'absent' or 'present')..'), register writes, overflow, PPUSTATUS marker')
assert(os.execute('rm -rf '..VPD_CAPTURE_DIRECTORY))
