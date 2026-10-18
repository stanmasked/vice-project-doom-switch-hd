-- Stage45 synthetic FCEUX PRG read and mapper write callbacks.
local dir=os.tmpname();os.remove(dir);assert(os.execute('mkdir -p "'..dir..'"'))
VPD_PRG_DIRECTORY=dir;VPD_PRG_MAX_EVENTS=7
local reads,writes={},{}
memory={
 registerread=function(addr,size,fn)
   assert(addr==0x8000 and size==0x8000)
   reads.all=fn
 end,
 registerwrite=function(addr,size,fn)
   assert(addr==0x8000 and size==0x2000)
   writes[0x8000]=fn;writes[0x8001]=fn
 end
}
local exit_fn
emu={framecount=function()return 42 end,registerexit=function(fn)exit_fn=fn end}
dofile('tools/capture_fceux_prg_reads.lua')
assert(type(reads.all)=='function')
reads.all(0x835B,1,0) -- unknown initial mapping
writes[0x8000](0x8002,1,0x06)
writes[0x8001](0x8003,1,0x0C)
reads.all(0x835B,1,0) -- bank 12
writes[0x8000](0x9FFE,1,0x46)
writes[0x8001](0x9FFF,1,0x0E)
reads.all(0xC906,1,0) -- bank 14
reads.all(0x835B,1,0) -- overflow; never written
local ok,err=pcall(reads.all,0x835B,1,0x7F)
assert(not ok and tostring(err):find('READ callback address/size/zero sentinel',1,true))
for _,args in ipairs({
  {0x8002,2,0x06}, -- not a byte-sized write
  {0xA000,1,0x06}, -- outside bank-select/data mirrored region
  {0x9FFE,1,256},  -- not an 8-bit value
}) do
  local bad,why=pcall(writes[0x8000],args[1],args[2],args[3])
  assert(not bad and tostring(why):find('mirrored MMC3 write',1,true))
end
exit_fn()
local file=assert(io.open(dir..'/stage45_prg_reads.tsv'))
local lines={};for line in file:lines() do lines[#lines+1]=line end;file:close()
assert(#lines==8)
assert(lines[2]=='42\t1\tREAD\t835B\tunknown\tunknown')
assert(lines[5]=='42\t4\tREAD\t835B\tunknown\t12')
assert(lines[8]=='42\t7\tREAD\tC906\tunknown\t14')
local f=assert(io.open(dir..'/stage45_prg_reads.meta.txt'))
local meta=f:read('*a');f:close()
assert(meta:find('events_recorded=7',1,true))
assert(meta:find('events_dropped=1',1,true))
assert(meta:find('callback_errors=4',1,true))
assert(meta:find('mmc3_write_coverage=full_8000_9fff_even_odd',1,true))
assert(meta:find('complete=no',1,true))
assert(meta:find('read_value_provenance=address_only_fceux_zero_sentinel',1,true))
os.remove(dir..'/stage45_prg_reads.tsv')
os.remove(dir..'/stage45_prg_reads.meta.txt')
assert(os.execute('rmdir "'..dir..'"'))
print('Stage45 synthetic read and MMC3 callbacks PASS')
