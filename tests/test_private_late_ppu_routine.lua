-- Synthetic FCEUX callback test for private Stage 1-1 late CPU/PPU capture.
local root=os.tmpname()..'_late_ppu_mock'
assert(os.execute('mkdir -p '..root))
local previous=os.getenv
local env={
 VPD_PRIVATE_LATE_PPU_OUTPUT_DIR=root,
 VPD_PRIVATE_FM2_PATH='/tmp/synthetic_invented.fm2',
 VPD_PRIVATE_ROM_PAYLOAD_MD5=string.rep('f',32),
 VPD_PRIVATE_FRAME_COUNT='7',
 VPD_PRIVATE_LATE_START_FRAME='2',
 VPD_PRIVATE_LATE_STOP_FRAME='4'
}
os.getenv=function(name)return env[name] or previous(name)end
local frame,clock,a,x,callback=0,0,0,0,nil
local hooks,ports={},{}
rom={gethash=function(which)assert(which=='md5');return string.rep('f',32)end}
movie={play=function(file,readonly)
  assert(file==env.VPD_PRIVATE_FM2_PATH and readonly);return true end,
  readonly=function()return true end,
  length=function()return 7 end}
debugger={getcyclescount=function()return clock end}
memory={
 registerexec=function(pc,fn)assert(hooks[pc]==nil);hooks[pc]=fn end,
 registerwrite=function(addr,fn)assert(ports[addr]==nil);ports[addr]=fn end,
 getregister=function(reg)
   if reg=='a' then return a elseif reg=='x' then return x
   elseif reg=='y' then return 0 elseif reg=='p' then return 0x24 end
   error('unexpected register')
 end}
emu={
 framecount=function()return frame end,
 registerafter=function(fn)assert(callback==nil);callback=fn end}
dofile('tools/capture_private_late_ppu_routine.lua')
local instructions={
 {0xE367,0},{0xE369,4,0x2005,0},{0xE36C,8,0x2005,0},
 {0xE36F,10},{0xE371,12},{0xE373,16,0x2006,15},
 {0xE376,20,0x2006,0},{0xE379,22},{0xE37B,24},
 {0xE37D,28,0x8000,0},{0xE380,32,0x8001,0},
 {0xE383,34},{0xE384,38,0x8000,1},
 {0xE387,42,0x8001,2},{0xE38A,45},
 {0xE38E,51,0x2001,14}}
for n=0,6 do
  frame=n
  if n>=2 and n<=4 then
    clock=n*30000-100
    hooks[0xE8E7]()
    for _,entry in ipairs(instructions) do
      local pc,delta,port,value=entry[1],entry[2],entry[3],entry[4]
      clock=n*30000+delta
      a=0;x=0
      if pc==0xE371 or pc==0xE373 or pc==0xE376 or pc==0xE379 then a=15 end
      if pc>=0xE37B and pc<=0xE38A then a=2 end
      if pc==0xE384 or pc==0xE387 or pc==0xE38A or pc==0xE38E then x=1 end
      if pc==0xE38E then a=14 end
      assert(type(hooks[pc])=='function')
      hooks[pc]()
      if port then assert(type(ports[port])=='function');ports[port](port,1,value)end
    end
  end
  callback()
end
local function read(name)
  local f=assert(io.open(root..'/'..name,'rb'))
  local result=assert(f:read('*a'));assert(f:close());return result
end
local trace=read('cpu_sequence.tsv')
local rows=0
for _ in trace:gmatch('[^\n]+') do rows=rows+1 end
assert(rows==1+3*(17+9),rows)
assert(trace:find('4\t120051\tWR\t2001\t0E',1,true))
local marker=read('COMPLETE.txt')
assert(marker:find('callback_events=78',1,true))
assert(marker:find('last_observed_frame=4',1,true))
assert(marker:find('frame_gaps=0',1,true))
assert(marker:find('movie_readonly_verified=yes',1,true))
print('PRIVATE_LATE_PPU_SYNTHETIC_FCEUX_CALLBACKS_PASS frames=3 events=78')
assert(os.execute('rm -rf '..root))
os.getenv=previous
