-- Synthetic emulator callbacks only. Executes actual production Lua trace script.
local short=os.getenv('VPD_MOCK_SHORT')=='1'
local invalid=os.getenv('VPD_MOCK_BAD_MMC3')=='1'
local noclock=os.getenv('VPD_MOCK_NOCLOCK')=='1'
VPD_TRACE_DIRECTORY=os.tmpname()..'_vpd_stage38'
VPD_TRACE_MAX_EVENTS=short and 3 or 100
VPD_TRACE_SESSION_LABEL='invented_test_fixture'
assert(os.execute('mkdir -p '..VPD_TRACE_DIRECTORY))
local exec_hooks,write_hooks={},{}
local exit_hook
local ram={}
for _,addr in ipairs({0x07,0x90,0x91,0x92,0xAA,0xAB,0xA8,0xA9}) do
  ram[addr]=addr%256
end
memory={
 registerexec=function(pc,cb)assert(exec_hooks[pc]==nil);exec_hooks[pc]=cb end,
 registerwrite=function(addr,size_or_cb,callback)
   if callback~=nil then
     assert(addr==0x8000 and size_or_cb==0x2000)
     write_hooks.mapper=callback
   else
     assert(write_hooks[addr]==nil)
     write_hooks[addr]=size_or_cb
   end
 end,
 readbyte=function(addr)return ram[addr] or 0 end
}
rom={gethash=function(which)
 assert(which=='md5');return 'ffffffffffffffffffffffffffffffff'
end}
local frame=120
emu={framecount=function()return frame end,
     registerexit=function(f)assert(not exit_hook);exit_hook=f end}
if not noclock then
  local tick=100000
  debugger={getcyclescount=function()tick=tick+5;return tick end}
end
dofile('tools/capture_fceux_dispatch.lua')
assert(type(exit_hook)=='function')
assert(exec_hooks[0xE479] and exec_hooks[0xE4E6] and exec_hooks[0xE4F3])
assert(exec_hooks[0xC906] and exec_hooks[0x835B])
assert(write_hooks[0x92] and write_hooks.mapper)
local function write(addr,value)
 local callback=addr>=0x8000 and write_hooks.mapper or write_hooks[addr]
 assert(callback)
 callback(addr,1,value)
 if addr<=0xff then ram[addr]=value end
end
exec_hooks[0x835B]()
exec_hooks[0xE479]()
write(0x8002,0x06)
write(0x8003,12)
exec_hooks[0x835B]()
exec_hooks[0xC906]()
write(0x92,21)
exec_hooks[0xE4E6]()
exec_hooks[0xE4F3]()
write(0x9FFE,0x46)
write(0x9FFF,14)
exec_hooks[0xC906]()
exec_hooks[0x835B]()
frame=121
exec_hooks[0xE50F]()
if invalid then
 local ok,err=pcall(write_hooks.mapper,0x8002,2,6)
 assert(not ok and tostring(err):find('Unsupported FCEUX callback contract',1,true))
end
exit_hook()
local function read(path)
 local f=assert(io.open(path,'rb'))
 local content=f:read('*a');f:close();return content
end
local data=read(VPD_TRACE_DIRECTORY..'/stage38_dispatch_exec.tsv')
local meta=read(VPD_TRACE_DIRECTORY..'/stage38_dispatch_exec.meta.txt')
assert(data:find('frame\tseq\tcpu_cycle\tkind\tcpu_address\tvalue\tmmc3_mode',1,true))
assert(data:find('EXEC\t835B\tunknown\tunknown\tunknown\tunknown\tunknown\tunknown_mode',1,true),data)
assert(data:find('EXEC\tE479\tunknown\tunknown\tunknown\tunknown\t15\tfixed_last_bank',1,true),data)
if not short then
 assert(data:find('MMC3_SELECT\\t8002\\t06',1,true),data)
 assert(data:find('MMC3_DATA\\t8003\\t0C',1,true),data)
 assert(data:find('MMC3_SELECT\\t9FFE\\t46',1,true),data)
 assert(data:find('MMC3_DATA\\t9FFF\\t0E',1,true),data)
 assert(data:find('EXEC\t835B\tunknown\t0\t0C\tunknown\t12\tmapped_r6',1,true),data)
 assert(data:find('EXEC\tC906\tunknown\t0\t0C\tunknown\t14\tfixed_second_last_bank',1,true),data)
 assert(data:find('EXEC\tC906\tunknown\t1\t0E\tunknown\t14\tmapped_r6',1,true),data)
 assert(data:find('EXEC\t835B\tunknown\t1\t0E\tunknown\t14\tfixed_second_last_bank',1,true),data)
 assert(data:find('RAM_WRITE\t0092\t15',1,true),data)
end
assert(meta:find('format=vice_stage38_execution_v1',1,true))
assert(meta:find('rom_md5=ffffffffffffffffffffffffffffffff',1,true))
assert(meta:find('session_label=invented_test_fixture',1,true))
assert(meta:find('cycle_trace_available='..(noclock and 'no' or 'yes'),1,true))
assert(meta:find('initial_prg_r6=unknown',1,true))
assert(meta:find('mmc3_write_coverage=full_8000_9fff_even_odd',1,true))
assert(meta:find('callback_errors='..(invalid and '1' or '0'),1,true))
if short then
 assert(meta:find('events_recorded=3',1,true))
 assert(meta:find('trace_complete=no',1,true))
 assert(meta:find('events_dropped=11',1,true),meta)
else
 assert(meta:find('events_recorded=14',1,true),meta)
 assert(meta:find('events_dropped=0',1,true))
 assert(meta:find('trace_complete='..(invalid and 'no' or 'yes'),1,true))
end
print('PASS stage38 execution trace: '..(short and 'overflow' or 'complete'))
assert(os.execute('rm -rf '..VPD_TRACE_DIRECTORY))
