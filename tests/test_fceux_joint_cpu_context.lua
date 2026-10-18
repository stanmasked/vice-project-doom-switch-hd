rom={
 readbyteunsigned=function(i)
   local header={[0]=0x4e,[1]=0x45,[2]=0x53,[3]=0x1a,
     [4]=8,[5]=16,[6]=0x40,[7]=0}
   return header[i] or 0
 end
}
-- ROM-free stage53 joint callback and optional CPU register test.
local dir=os.tmpname();os.remove(dir);assert(os.execute('mkdir -p "'..dir..'"'))
VPD_STAGE53_DIRECTORY=dir;VPD_STAGE53_MAX_EVENTS=4
local hooks,writes={},{}
memory={
 registerexec=function(addr,fn)hooks[addr]=fn end,
 registerread=function(a,n,fn)assert(a==0x8000 and n==0x8000);hooks.read=fn end,
 registerwrite=function(a,size,fn)
   assert(a==0x8000 and size==0x2000)
   writes[0x8000]=fn;writes[0x8001]=fn
 end,
 getregister=function(name)
   assert(name==name:lower(),'FCEUX register names must be lowercase')
   if name=='p' then error('unavailable') end
   return ({a=1,x=2,y=3,s=4})[name]
 end
}
local onexit
emu={
 framecount=function()return 19 end,
 registerexit=function(fn)onexit=fn end,
 getregister=function() error('wrong emu API used') end
}
dofile('tools/capture_fceux_joint_cpu_context.lua')
hooks[0x835B](0x835B,1,0)
writes[0x8000](0x8002,1,6)
writes[0x8001](0x8003,1,12)
hooks.read(0x835C,1,0)
hooks.read(0x835D,1,0)
onexit()
local f=assert(io.open(dir..'/stage53_joint_context.tsv'))
local rows={};for l in f:lines() do rows[#rows+1]=l end;f:close()
assert(#rows==5)
assert(rows[2]=='19\t1\tEXEC\t835B\tunknown\tunknown\t01\t02\t03\t04\tunknown')
assert(rows[5]=='19\t4\tREAD\t835C\tunknown\t12\t01\t02\t03\t04\tunknown')
local m=assert(io.open(dir..'/stage53_joint_context.meta.txt'))
local data=m:read('*a');m:close()
assert(data:find('events_dropped=1',1,true))
assert(data:find('read_causality=not_proven',1,true))
assert(data:find('register_api=memory.getregister',1,true))
assert(data:find('rom_header_profile=ines_mapper4_prg128k_chr128k',1,true))
assert(data:find('rom_md5_pin=not_supplied',1,true))
assert(data:find('callback_errors=0',1,true))
assert(data:find('mmc3_write_coverage=full_8000_9fff_even_odd',1,true))
assert(data:find('read_value_provenance=address_only_fceux_zero_sentinel',1,true))
assert(data:find('callback_contract=address_size_value_v1',1,true))
os.remove(dir..'/stage53_joint_context.tsv')
os.remove(dir..'/stage53_joint_context.meta.txt')
assert(os.execute('rmdir "'..dir..'"'))
print('Stage53 joint CPU context synthetic test passed')
