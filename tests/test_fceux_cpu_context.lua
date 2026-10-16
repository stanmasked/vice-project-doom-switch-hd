-- ROM-free stage52 CPU context mock: sampled and unavailable registers.
local folder=os.tmpname();os.remove(folder);assert(os.execute('mkdir -p "'..folder..'"'))
VPD_CPU_CONTEXT_DIRECTORY=folder;VPD_CPU_CONTEXT_MAX_EVENTS=2
local execs={}
memory={registerexec=function(address,fn)execs[address]=fn end}
local done
emu={
 framecount=function()return 15 end,
 registerexit=function(fn)done=fn end,
 getregister=function(name)
   if name=='P' then error('unavailable') end
   return ({A=1,X=2,Y=3,S=4})[name]
 end
}
dofile('tools/capture_fceux_cpu_context.lua')
execs[0xE479]()
execs[0x835B]()
execs[0xE4E6]() -- overflow
done()
local f=assert(io.open(folder..'/stage52_cpu_context.tsv'))
local rows={};for line in f:lines() do rows[#rows+1]=line end;f:close()
assert(#rows==3)
assert(rows[2]=='15\t1\tE479\t01\t02\t03\t04\tunknown\tpartial_unknown')
local m=assert(io.open(folder..'/stage52_cpu_context.meta.txt'))
local data=m:read('*a');m:close()
assert(data:find('events_dropped=1',1,true))
assert(data:find('effective_address=not_recorded',1,true))
os.remove(folder..'/stage52_cpu_context.tsv')
os.remove(folder..'/stage52_cpu_context.meta.txt')
assert(os.execute('rmdir "'..folder..'"'))
print('Stage52 sparse register probe mock passed')
