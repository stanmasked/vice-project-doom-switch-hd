-- Stage80: CPU-cycle errors may not create an unmatched frame-log event.
-- Entire fixture is synthetic; no ROM or commercial visual resources.
local function read(path)
  local f=assert(io.open(path,'rb'))
  local s=assert(f:read('*a'));assert(f:close());return s
end
local function count_rows(s)
  local n=0
  for _ in s:gmatch('[^\n]+') do n=n+1 end
  return n-1  -- TSV header
end
local function run(with_clock)
  local dir=os.tmpname()
  os.remove(dir)
  assert(os.execute('mkdir -p "'..dir..'"'))
  VPD_CAPTURE_DIRECTORY=dir
  VPD_CAPTURE_INTERVAL=1
  VPD_CAPTURE_LIMIT=1
  VPD_CAPTURE_SCREEN=false
  local mwrite,ppuwrite,statusread,after,exit
  local cycle_mode='good'
  local frame_mode='good'
  local frame=1
  local cycle=100
  memory={
    registerwrite=function(address,size,fn)
      if address==0x8000 then
        assert(size==0x8000 and not mwrite);mwrite=fn
      else
        assert(address==0x2000 and size==0x2000 and not ppuwrite)
        ppuwrite=fn
      end
    end,
    registerread=function(address,size,fn)
      assert(address==0x2000 and size==0x2000)
      statusread=fn
    end,
    readbyte=function()return 0 end,
    readbyterange=function(address,size)
      assert(address==0 and size==0x800)
      return string.rep('r',size)
    end,
  }
  ppu={readbyterange=function(address,size)
    assert(address==0 and size==0x4000)
    return string.rep('p',size)
  end}
  if with_clock then
    debugger={getcyclescount=function()
      if cycle_mode=='error' then error('synthetic debugger failure') end
      if cycle_mode=='nil' then return nil end
      if cycle_mode=='negative' then return -1 end
      if cycle_mode=='fraction' then return 10.5 end
      if cycle_mode=='nan' then return 0/0 end
      if cycle_mode=='infinite' then return math.huge end
      if cycle_mode=='too_large' then return 9007199254740992 end
      cycle=cycle+17
      return cycle
    end}
  else
    debugger=nil
  end
  rom={gethash=function(alg)
    assert(alg=='md5');return string.rep('a',32)
  end}
  emu={
    framecount=function()
      if frame_mode=='error' then error('synthetic frame counter failure') end
      if frame_mode=='nil' then return nil end
      if frame_mode=='too_large' then return 2147483648 end
      return frame
    end,
    registerafter=function(fn)after=fn end,
    registerexit=function(fn)exit=fn end,
    message=function()end,
  }
  dofile('tools/capture_fceux_ppu.lua')
  assert(type(mwrite)=='function' and type(ppuwrite)=='function')
  assert(type(statusread)=='function' and type(after)=='function'
         and type(exit)=='function')
  -- Valid event before any failed callback.
  ppuwrite(0x200D,1,0x11)
  local errors=0
  if with_clock then
    for _,mode in ipairs({'error','nil','negative','fraction','nan','infinite','too_large'}) do
      cycle_mode=mode
      local ok,why=pcall(mwrite,0x8002,1,0x80)
      assert(not ok and tostring(why):find('invalid CPU cycle counter',1,true),
             mode..': '..tostring(why))
      errors=errors+1
    end
    cycle_mode='good'
  end
  for _,mode in ipairs({'error','nil','too_large'}) do
    frame_mode=mode
    local ok,why=pcall(ppuwrite,0x200D,1,0x15)
    assert(not ok and tostring(why):find('invalid frame counter',1,true),
           mode..': '..tostring(why))
    errors=errors+1
  end
  frame_mode='good'
  -- Must succeed after exceptions and still append one event to each stream.
  statusread(0x3FFA,1,0)
  after()
  local snapshot=read(dir..'/frame_000001.meta.txt')
  assert(snapshot:find('callback_errors='..errors,1,true))
  assert(snapshot:find('logged_register_writes=2',1,true))
  assert(snapshot:find('register_log_complete=no',1,true))
  exit()
  local manifest=read(dir..'/ppu_capture_session.meta.txt')
  assert(manifest:find('complete=no',1,true))
  assert(manifest:find('events_recorded=2',1,true))
  assert(manifest:find('callback_errors='..errors,1,true))
  assert(manifest:find('capture_failures=0',1,true))
  local frame_log=read(dir..'/mmc3_video_writes.tsv')
  assert(count_rows(frame_log)==2,frame_log)
  assert(frame_log:find('200D\t11',1,true))
  assert(frame_log:find('3FFA\t00',1,true))
  assert(not frame_log:find('8002\t80',1,true))
  if with_clock then
    local cycle_log=read(dir..'/mmc3_ppu_cycles.tsv')
    assert(count_rows(cycle_log)==2,cycle_log)
    assert(cycle_log:find('\t200D\t11\tW',1,true))
    assert(cycle_log:find('\t3FFA\t00\tR',1,true))
    assert(not cycle_log:find('\t8002\t80\tW',1,true))
    assert(os.remove(dir..'/mmc3_ppu_cycles.tsv'))
  end
  for _,name in ipairs({
    'frame_000001.meta.txt','frame_000001.ppu.bin',
    'frame_000001.ram.bin','mmc3_video_writes.tsv',
    'ppu_capture_session.meta.txt'
  }) do assert(os.remove(dir..'/'..name),name) end
  assert(os.execute('rmdir "'..dir..'"'))
end
run(true)
run(false)
print('Stage80 atomic frame/cycle events and callback errors PASS')
