-- Genuine FCEUX private Stage 1-1 late-routine CPU trace. NEVER commit outputs.
-- The user's ROM/FM2 paths and payload identity are supplied only locally.
local function required(name)
  local v=os.getenv(name)
  assert(type(v)=='string' and #v>0,name..' is required')
  return v
end
local directory=required('VPD_PRIVATE_LATE_PPU_OUTPUT_DIR')
local fm2=required('VPD_PRIVATE_FM2_PATH')
local expected=required('VPD_PRIVATE_ROM_PAYLOAD_MD5'):lower()
local total=tonumber(required('VPD_PRIVATE_FRAME_COUNT'))
local start=tonumber(required('VPD_PRIVATE_LATE_START_FRAME'))
local stop=tonumber(required('VPD_PRIVATE_LATE_STOP_FRAME'))
assert(#expected==32 and not expected:find('[^0-9a-f]'))
assert(total and total==math.floor(total) and total>1 and total<=100000000)
assert(start and stop and start==math.floor(start) and stop==math.floor(stop)
       and start>=1 and stop>=start and stop<total and stop-start<=1200)
assert(type(memory)=='table' and type(memory.registerexec)=='function' and
       type(memory.registerwrite)=='function' and
       type(memory.getregister)=='function')
assert(type(debugger)=='table' and type(debugger.getcyclescount)=='function')
assert(type(movie)=='table' and type(movie.play)=='function')
assert(rom.gethash('md5'):lower()==expected,'private ROM identity mismatch')
assert(movie.play(fm2,true) and movie.readonly() and movie.length()==total,
       'original movie must be loaded read-only')
local function fresh_file(name)
  local filename=directory..'/'..name
  local old=io.open(filename,'rb')
  if old then old:close();error('refusing private output overwrite') end
  return assert(io.open(filename,'wb'))
end
local writer=fresh_file('cpu_sequence.tsv')
assert(writer:write('frame\tcycle\ttype\taddress\tvalue\ta\tx\ty\tp\n'))
local pcs={0xE367,0xE369,0xE36C,0xE36F,0xE371,0xE373,0xE376,
           0xE379,0xE37B,0xE37D,0xE380,0xE383,0xE384,0xE387,
           0xE38A,0xE38E,0xE8E7}
local ports={0x2005,0x2006,0x8000,0x8001,0x2000,0x2001}
local observed=0
local function capture(kind,addr,value)
  local frame=emu.framecount()
  if frame<start or frame>stop then return end
  local cycle=debugger.getcyclescount()
  local a=memory.getregister('a')
  local x=memory.getregister('x')
  local y=memory.getregister('y')
  local p=memory.getregister('p')
  assert(type(cycle)=='number' and cycle>=0 and cycle==math.floor(cycle))
  for _,r in ipairs({a,x,y,p}) do
    assert(type(r)=='number' and r>=0 and r<256 and r==math.floor(r))
  end
  assert(writer:write(string.format('%d\t%.0f\t%s\t%04X\t%02X\t%02X\t%02X\t%02X\t%02X\n',
              frame,cycle,kind,addr,value,a,x,y,p)))
  observed=observed+1
end
for _,pc in ipairs(pcs) do
  memory.registerexec(pc,function()capture('PC',pc,0)end)
end
for _,addr in ipairs(ports) do
  memory.registerwrite(addr,function(_,__,v)capture('WR',addr,v)end)
end
local first,last,finished=nil,nil,false
emu.registerafter(function()
  if finished then return end
  local frame=emu.framecount()
  if frame==last then return end
  assert(type(frame)=='number' and frame==math.floor(frame) and
         frame>=0 and frame<total)
  if first==nil then
    assert(frame<=1,'private playback callback attached late')
    first=frame
  else
    assert(frame==last+1,'missing movie frame callback')
  end
  last=frame
  if frame==stop then
    assert(movie.readonly() and movie.length()==total and
           rom.gethash('md5'):lower()==expected,
           'original movie identity changed during capture')
    assert(writer:flush() and writer:close())
    local complete=fresh_file('COMPLETE.txt')
    assert(complete:write('format=private_stage155_cpu_sequence_v1\n'..
          'first_observed_frame='..first..'\n'..
          'last_observed_frame='..last..'\n'..
          'frame_gaps=0\n'..
          'callback_events='..observed..'\n'..
          'rom_identity_verified=yes\n'..
          'movie_readonly_verified=yes\n'))
    assert(complete:close())
    finished=true
    if type(emu.exit)=='function' then emu.exit() end
  end
end)
