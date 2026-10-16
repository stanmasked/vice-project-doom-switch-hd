-- Synthetic FCEUX Lua API tests: no ROM or real gameplay data.
local dir=os.tmpname()
os.remove(dir)
assert(os.execute('mkdir -p "'..dir..'"'))
VPD_POINTER_DIRECTORY=dir
VPD_POINTER_MAX_EVENTS=2
local reads,writes={},{}
local ram={[0xAA]=0x11,[0xAB]=0x22,[0xA8]=0x33,[0xA9]=0x44}
local callback_recursions=0
memory={
 registerread=function(addr,fn) reads[addr]=fn end,
 registerwrite=function(addr,fn) writes[addr]=fn end,
 readbyte=function(addr)
   if reads[addr] then
     callback_recursions=callback_recursions+1
     if callback_recursions>100 then error('recursive callback loop') end
     reads[addr](addr,1,0)
   end
   return ram[addr]
 end
}
local exit_fn
emu={framecount=function()return 50 end,registerexit=function(fn) exit_fn=fn end}
rom={gethash=function(alg)assert(alg=='md5');return string.rep('a',32) end}
dofile('tools/capture_fceux_pointer_access.lua')
assert(reads[0xAA] and reads[0xAB] and reads[0xA8] and reads[0xA9])
assert(writes[0xAA] and writes[0xAB] and writes[0xA8] and writes[0xA9])
reads[0xAA](0xAA,1,0)
writes[0xAB](0xAB,1,0x99)
reads[0xA8](0xA8,1,0) -- deliberate overflow
exit_fn()
local f=assert(io.open(dir..'/stage41_pointer_access.tsv'))
local lines={}
for line in f:lines() do lines[#lines+1]=line end
f:close()
assert(#lines==3,'expected header + exactly two events')
assert(lines[2]:find('50\t1\tREAD\t00AA\t11\t11\t22\t33\t44',1,true))
assert(lines[3]:find('50\t2\tWRITE\t00AB\t99\t11\t22\t33\t44',1,true))
assert(callback_recursions==8,'four sampled bytes per event should invoke callbacks once')
local m=assert(io.open(dir..'/stage41_pointer_access.meta.txt'))
local meta=m:read('*a');m:close()
assert(meta:find('events_recorded=2',1,true))
assert(meta:find('events_dropped=1',1,true))
assert(meta:find('complete=no',1,true))
assert(meta:find('callback_errors=0',1,true))
assert(meta:find('read_value_provenance=address_only_fceux_zero_sentinel',1,true))
assert(meta:find('execution_pc=not_instrumented',1,true))
os.remove(dir..'/stage41_pointer_access.tsv')
os.remove(dir..'/stage41_pointer_access.meta.txt')
assert(os.execute('rmdir "'..dir..'"'))
print('stage41 synthetic read/write recursion and overflow: PASS')
