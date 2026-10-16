-- ROM-free stage53 joint callback and optional CPU register test.
local dir=os.tmpname();os.remove(dir);assert(os.execute('mkdir -p "'..dir..'"'))
VPD_STAGE53_DIRECTORY=dir;VPD_STAGE53_MAX_EVENTS=4
local hooks,writes={},{}
memory={
 registerexec=function(addr,fn)hooks[addr]=fn end,
 registerread=function(a,n,fn)assert(a==0x8000 and n==0x8000);hooks.read=fn end,
 registerwrite=function(a,fn)writes[a]=fn end
}
local onexit
emu={
 framecount=function()return 19 end,
 registerexit=function(fn)onexit=fn end,
 getregister=function(n) if n=='P' then error('unavailable') end
   return ({A=1,X=2,Y=3,S=4})[n] end
}
dofile('tools/capture_fceux_joint_cpu_context.lua')
hooks[0x835B]()
writes[0x8000](0x8000,1,6)
writes[0x8001](0x8001,1,12)
hooks.read(0x835C,1,0xAB)
hooks.read(0x835D,1,0xCD)
onexit()
local f=assert(io.open(dir..'/stage53_joint_context.tsv'))
local rows={};for l in f:lines() do rows[#rows+1]=l end;f:close()
assert(#rows==5)
assert(rows[2]=='19\t1\tEXEC\t835B\tunknown\tunknown\t01\t02\t03\t04\tunknown')
assert(rows[5]=='19\t4\tREAD\t835C\tAB\t12\t01\t02\t03\t04\tunknown')
local m=assert(io.open(dir..'/stage53_joint_context.meta.txt'))
local data=m:read('*a');m:close()
assert(data:find('events_dropped=1',1,true))
assert(data:find('read_causality=not_proven',1,true))
os.remove(dir..'/stage53_joint_context.tsv')
os.remove(dir..'/stage53_joint_context.meta.txt')
assert(os.execute('rmdir "'..dir..'"'))
print('Stage53 joint CPU context synthetic test passed')
