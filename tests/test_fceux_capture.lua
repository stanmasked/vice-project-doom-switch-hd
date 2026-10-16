-- Exercise the unmodified FCEUX capture script with synthetic API callbacks.
-- Requires Lua 5.4 interpreter on CI; captures contain invented data only.
VPD_CAPTURE_DIRECTORY=os.tmpname()..'_vice_capture'
assert(os.execute('mkdir -p '..VPD_CAPTURE_DIRECTORY))
local hooks={}
local after, exit
local frame=0
memory={
 registerwrite=function(addr, cb) assert(not hooks[addr]);hooks[addr]=cb end,
 readbyterange=function(addr,n)assert(addr==0 and n==2048);return string.rep(string.char(0x42),n)end,
 readbyte=function(addr)return (addr*3)%256 end
}
ppu={readbyterange=function(addr,n)assert(addr==0 and n==16384);return string.rep(string.char(0x5A),n)end}
rom={gethash=function(which)assert(which=='md5');return 'abcd1234' end}
emu={framecount=function()return frame end,
 registerafter=function(cb)after=cb end,
 registerexit=function(cb)exit=cb end,
 message=function(s)assert(type(s)=='string')end}

dofile('tools/capture_fceux_ppu.lua')
assert(type(after)=='function' and type(exit)=='function')
assert(hooks[0x8000] and hooks[0x8001] and hooks[0x2000])
local function write(addr,value) assert(hooks[addr]);hooks[addr](addr,1,value)end
write(0x8000,0x80);write(0x8001,0x14);write(0x2000,0x10)
after()
frame=1
for n=1,12005 do write(0x2007,n%256) end
after()
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
local text=read(p..'/frame_000120.meta.txt')
assert(text:find('format=fceux_ppu_snapshot_v2',1,true))
assert(text:find('dropped_register_writes=5',1,true),text)
assert(text:find('register_log_complete=no',1,true),text)
assert(text:find('chr_r0=06',1,true),text)
assert(text:find('chr_ram_0=B7',1,true),text)
local log=read(p..'/mmc3_video_writes.tsv')
assert(log:find('frame\taddress\tvalue',1,true))
assert(log:find('0\t8001\t14',1,true))
assert(log:find('120\t8001\t06',1,true))
print('PASS: two captures, MMC3 register tracking, overflow reporting and write log')
assert(os.execute('rm -rf '..VPD_CAPTURE_DIRECTORY))
