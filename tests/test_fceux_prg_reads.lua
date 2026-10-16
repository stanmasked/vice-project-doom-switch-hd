-- Stage45 synthetic FCEUX PRG read and mapper write callbacks.
local dir=os.tmpname();os.remove(dir);assert(os.execute('mkdir -p "'..dir..'"'))
VPD_PRG_DIRECTORY=dir;VPD_PRG_MAX_EVENTS=7
local reads,writes={},{}
memory={
 registerread=function(addr,size,fn)
   assert(addr==0x8000 and size==0x8000)
   reads.all=fn
 end,
 registerwrite=function(addr,fn)writes[addr]=fn end
}
local exit_fn
emu={framecount=function()return 42 end,registerexit=function(fn)exit_fn=fn end}
dofile('tools/capture_fceux_prg_reads.lua')
assert(type(reads.all)=='function')
reads.all(0x835B,1,0x12) -- unknown initial mapping
writes[0x8000](0x8000,1,0x06)
writes[0x8001](0x8001,1,0x0C)
reads.all(0x835B,1,0x34) -- bank 12
writes[0x8000](0x8000,1,0x46)
writes[0x8001](0x8001,1,0x0E)
reads.all(0xC906,1,0x56) -- bank 14
reads.all(0x835B,1,0x78) -- overflow; never written
exit_fn()
local file=assert(io.open(dir..'/stage45_prg_reads.tsv'))
local lines={};for line in file:lines() do lines[#lines+1]=line end;file:close()
assert(#lines==8)
assert(lines[2]=='42\t1\tREAD\t835B\t12\tunknown')
assert(lines[5]=='42\t4\tREAD\t835B\t34\t12')
assert(lines[8]=='42\t7\tREAD\tC906\t56\t14')
local f=assert(io.open(dir..'/stage45_prg_reads.meta.txt'))
local meta=f:read('*a');f:close()
assert(meta:find('events_recorded=7',1,true))
assert(meta:find('events_dropped=1',1,true))
assert(meta:find('complete=no',1,true))
os.remove(dir..'/stage45_prg_reads.tsv')
os.remove(dir..'/stage45_prg_reads.meta.txt')
assert(os.execute('rmdir "'..dir..'"'))
print('Stage45 synthetic read and MMC3 callbacks PASS')
