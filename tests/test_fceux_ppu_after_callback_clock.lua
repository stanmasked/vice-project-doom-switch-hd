-- Stage87: synthetic frame-callback clock samples, distinct from PPU frame starts.
local function get(path)
  local file=assert(io.open(path,'rb'))
  local s=assert(file:read('*a'))
  assert(file:close())
  return s
end
local function check(enabled,invalid_second)
  local dir=os.tmpname()
  os.remove(dir)
  assert(os.execute('mkdir -p "'..dir..'"'))
  VPD_CAPTURE_DIRECTORY=dir
  VPD_CAPTURE_INTERVAL=1
  VPD_CAPTURE_LIMIT=2
  VPD_CAPTURE_SCREEN=false
  VPD_CAPTURE_AFTER_CALLBACK_CLOCK=enabled
  local current_frame,cycle,override=1,0,false
  local onwrite,after,exit
  local inc=10
  memory={
    registerwrite=function(a,sz,fn)
      assert(type(fn)=='function')
      assert((a==0x2000 and sz==0x2000)
          or (a==0x8000 and sz==0x8000))
      if a==0x8000 then onwrite=fn end
    end,
    registerread=function(a,sz,fn)
      assert(a==0x2000 and sz==0x2000 and type(fn)=='function')
    end,
    readbyte=function()return 0 end,
    readbyterange=function(a,sz)
      assert(a==0 and sz==0x800)
      return string.rep('r',sz)
    end,
  }
  ppu={readbyterange=function(a,sz)
    assert(a==0 and sz==0x4000)
    return string.rep('p',sz)
  end}
  debugger={getcyclescount=function()
    if override then return 1 end
    cycle=cycle+inc
    return cycle
  end}
  rom={gethash=function(kind)
    assert(kind=='md5')
    return string.rep('a',32)
  end}
  emu={
    framecount=function()return current_frame end,
    registerafter=function(fn)after=fn end,
    registerexit=function(fn)exit=fn end,
    message=function()end,
  }
  dofile('tools/capture_fceux_ppu.lua')
  assert(type(onwrite)=='function' and type(after)=='function'
         and type(exit)=='function')
  onwrite(0x8002,1,0x80)
  after()
  local one=get(dir..'/frame_000001.meta.txt')
  assert(one:find('frame_callback_clock_scope='..
        (enabled and 'captured_frame_sample' or 'disabled'),1,true))
  assert(one:find('frame_callback_cpu_cycle='..
        (enabled and '20' or 'not_captured'),1,true))
  current_frame=2
  onwrite(0x8002,1,0x85)
  override=invalid_second
  local ok,err=pcall(after)
  if invalid_second then
    assert(not ok and tostring(err):find('registerafter sample precedes',1,true),
           tostring(err))
  else
    assert(ok,tostring(err))
    local two=get(dir..'/frame_000002.meta.txt')
    assert(two:find('frame_callback_cpu_cycle='..
        (enabled and '40' or 'not_captured'),1,true))
  end
  assert(pcall(exit))
  local m=get(dir..'/ppu_capture_session.meta.txt')
  assert(m:find('frame_callback_clock_mode='..
        (enabled and 'sampled_snapshots_v1' or 'disabled'),1,true))
  assert(m:find('frame_callback_clock_samples='..
        (enabled and (invalid_second and '1' or '2') or '0'),1,true))
  assert(m:find('frame_callback_clock_boundary_proven=no',1,true))
  assert(m:find('complete='..(invalid_second and 'no' or 'yes'),1,true))
  local files={'ppu_capture_session.meta.txt','mmc3_video_writes.tsv',
    'mmc3_ppu_cycles.tsv','frame_000001.meta.txt',
    'frame_000001.ppu.bin','frame_000001.ram.bin'}
  if not invalid_second then
    files[#files+1]='frame_000002.meta.txt'
    files[#files+1]='frame_000002.ppu.bin'
    files[#files+1]='frame_000002.ram.bin'
  end
  for _,name in ipairs(files) do
    assert(os.remove(dir..'/'..name),name)
  end
  assert(os.execute('rmdir "'..dir..'"'))
  VPD_CAPTURE_AFTER_CALLBACK_CLOCK=nil
end
check(false,false)
check(true,false)
check(true,true)
print('Stage87 sampled registerafter clocks: disabled, valid, invalid PASS')
