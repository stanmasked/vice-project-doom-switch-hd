-- ROM-free mock of stage49 callback order and unknown initial mapper.
local folder=os.tmpname();os.remove(folder);assert(os.execute('mkdir -p "'..folder..'"'))
VPD_JOINT_DIRECTORY=folder;VPD_JOINT_MAX_EVENTS=5
local execs,reads,writes={},nil,{}
memory={
 registerexec=function(a,f)execs[a]=f end,
 registerread=function(a,n,f)assert(a==0x8000 and n==0x8000);reads=f end,
 registerwrite=function(a,size,fn)
   assert(a==0x8000 and size==0x2000)
   writes[0x8000]=fn;writes[0x8001]=fn
 end
}
local exit
emu={framecount=function()return 9 end,registerexit=function(f)exit=f end}
dofile('tools/capture_fceux_joint_exec_reads.lua')
execs[0x835B]()                    -- unresolved bank
writes[0x8000](0x8002,1,6)         -- select R6
writes[0x8001](0x8003,1,12)        -- map bank 12
execs[0x835B]()                    -- mapped execution
reads(0x835C,1,0)               -- observed next read, causality not proven
reads(0x835D,1,0)               -- overflow
local ok,err=pcall(reads,0x835B,1,0x7F)
assert(not ok and tostring(err):find('READ callback address/size/zero sentinel',1,true))
local bad,why=pcall(writes[0x8000],0x9FFF,1,nil)
assert(not bad and tostring(why):find('mirrored MMC3 write',1,true))
exit()
local f=assert(io.open(folder..'/stage49_joint.tsv'))
local lines={};for l in f:lines() do lines[#lines+1]=l end;f:close()
assert(#lines==6)
assert(lines[2]=='9\t1\tEXEC\t835B\tunknown\tunknown')
assert(lines[5]=='9\t4\tEXEC\t835B\tunknown\t12')
assert(lines[6]=='9\t5\tREAD\t835C\tunknown\t12')
local m=assert(io.open(folder..'/stage49_joint.meta.txt'))
local meta=m:read('*a');m:close()
assert(meta:find('events_dropped=1',1,true))
assert(meta:find('callback_errors=2',1,true))
assert(meta:find('mmc3_write_coverage=full_8000_9fff_even_odd',1,true))
assert(meta:find('complete=no',1,true))
assert(meta:find('read_causality=not_proven',1,true))
assert(meta:find('read_value_provenance=address_only_fceux_zero_sentinel',1,true))
os.remove(folder..'/stage49_joint.tsv')
os.remove(folder..'/stage49_joint.meta.txt')
assert(os.execute('rmdir "'..folder..'"'))
print('Stage49 ordered joint mock PASS')
