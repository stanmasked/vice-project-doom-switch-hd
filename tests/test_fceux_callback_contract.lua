-- Synthetic fail-closed checks for FCEUX (address,size,value) callbacks.
local dir=os.tmpname();os.remove(dir)
assert(os.execute('mkdir -p "'..dir..'"'))
VPD_STAGE53_DIRECTORY=dir
VPD_STAGE53_MAX_EVENTS=20
local execs,writes={},{}
local read_hook,exit_hook
memory={
  registerexec=function(addr,fn) execs[addr]=fn end,
  registerread=function(addr,size,fn)
    assert(addr==0x8000 and size==0x8000)
    read_hook=fn
  end,
  registerwrite=function(addr,fn) writes[addr]=fn end,
  getregister=function(name)
    return ({a=1,x=2,y=3,s=4,p=5})[name]
  end
}
emu={framecount=function()return 17 end,registerexit=function(fn)exit_hook=fn end}
dofile('tools/capture_fceux_joint_cpu_context.lua')
local function fails(fn,...)
  local ok,err=pcall(fn,...)
  assert(not ok and tostring(err):find('Unsupported FCEUX callback contract',1,true),
    'Expected explicit FCEUX callback failure, got '..tostring(err))
end
fails(writes[0x8000],0x8000,1)               -- legacy 2-argument write
fails(writes[0x8001],0x8000,1,12)            -- wrong callback address
fails(read_hook,0x835B,2,0xAB)               -- wrong bus operation size
fails(read_hook,0x835B,1)                    -- absent read byte
fails(execs[0x835B],0xE479,1,0)             -- wrong EXEC callback PC
writes[0x8001](0x8001,1,12)                 -- no selected R6, remains unknown
read_hook(0x835C,1,0xAB)                   -- still unknown physical bank
exit_hook()
local file=assert(io.open(dir..'/stage53_joint_context.tsv'))
local rows={}
for line in file:lines() do rows[#rows+1]=line end
file:close()
assert(#rows==3)
assert(rows[2]:find('17\t1\tDATA\t8001\t0C\tunknown',1,true))
assert(rows[3]:find('17\t2\tREAD\t835C\tAB\tunknown',1,true))
local meta_file=assert(io.open(dir..'/stage53_joint_context.meta.txt'))
local meta=meta_file:read('*a'); meta_file:close()
assert(meta:find('events_recorded=2',1,true))
assert(meta:find('callback_errors=5',1,true))
assert(meta:find('callback_contract=address_size_value_v1',1,true))
assert(meta:find('complete=no',1,true))
os.remove(dir..'/stage53_joint_context.tsv')
os.remove(dir..'/stage53_joint_context.meta.txt')
assert(os.execute('rmdir "'..dir..'"'))
print('Stage67 FCEUX callback contract and fail-closed metadata PASS')
