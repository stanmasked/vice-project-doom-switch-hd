-- Stage79: ROM-free continuous vs skipped-frame PPU session finalization.
local function read(path)
  local f=assert(io.open(path,'rb'))
  local s=assert(f:read('*a'))
  assert(f:close())
  return s
end
local function check(frames,should_complete,clock_pattern)
  local dir=os.tmpname()
  os.remove(dir)
  assert(os.execute('mkdir -p "'..dir..'"'))
  VPD_CAPTURE_DIRECTORY=dir
  VPD_CAPTURE_INTERVAL=1
  VPD_CAPTURE_LIMIT=2
  VPD_CAPTURE_SCREEN=false
  local write_ppu,read_ppu,write_mmc3,after,exit
  local current_frame=0
  local cycle=0
  memory={
    registerwrite=function(address,size,fn)
      assert(size==0x2000 or size==0x8000)
      if address==0x2000 then write_ppu=fn
      elseif address==0x8000 then write_mmc3=fn
      else error('Unexpected write hook') end
    end,
    registerread=function(address,size,fn)
      assert(address==0x2000 and size==0x2000)
      read_ppu=fn
    end,
    readbyte=function()return 0 end,
    readbyterange=function(addr,size)
      assert(addr==0 and size==0x800)
      return string.rep('r',size)
    end,
  }
  ppu={readbyterange=function(addr,size)
    assert(addr==0 and size==0x4000)
    return string.rep('p',size)
  end}
  local cycle_calls=0
  debugger={getcyclescount=function()
    cycle_calls=cycle_calls+1
    cycle=cycle+7
    if clock_pattern=='within' and cycle_calls==2 then return 0 end
    if clock_pattern=='boundary' and cycle_calls==4 then return 0 end
    if clock_pattern=='equal' and cycle_calls==2 then return 7 end
    return cycle
  end}
  rom={gethash=function(hash)
    assert(hash=='md5')
    return string.rep('a',32)
  end}
  emu={
    framecount=function()return current_frame end,
    registerafter=function(fn)after=fn end,
    registerexit=function(fn)exit=fn end,
    message=function()end,
  }
  dofile('tools/capture_fceux_ppu.lua')
  assert(type(after)=='function' and type(exit)=='function')
  assert(type(write_ppu)=='function' and type(read_ppu)=='function')
  assert(type(write_mmc3)=='function')
  local manifest=dir..'/ppu_capture_session.meta.txt'
  assert(read(manifest)=='capture_in_progress=yes\n')
  for i,frame in ipairs(frames) do
    current_frame=frame
    write_mmc3(0x8002,1,0x80)
    write_ppu(0x200D,1,0x14+i)
    read_ppu(0x3FFA,1,0)
    after()
    local prefix=string.format('%s/frame_%06d',dir,frame)
    local meta=read(prefix..'.meta.txt')
    assert(meta:find('capture_scope=frame_prefix_only',1,true))
    assert(meta:find('session_snapshot_index='..i,1,true))
    assert(meta:find('register_log_complete=yes',1,true))
    assert(read(manifest)=='capture_in_progress=yes\n')
  end
  exit()
  local m=read(manifest)
  assert(m:find('complete='..(should_complete and 'yes' or 'no'),1,true),m)
  assert(m:find('frames_captured=2',1,true))
  assert(m:find('events_recorded=6',1,true))
  assert(m:find('capture_frames='..table.concat(frames,','),1,true))
  assert(m:find('frame_callback_gaps='..
    ((frames[2]>frames[1]+1) and 1 or 0),1,true))
  assert(m:find('cycle_order_policy=nondecreasing_v1',1,true))
  local regress=(clock_pattern=='within' or clock_pattern=='boundary') and 1 or 0
  local equals=(clock_pattern=='equal') and 1 or 0
  assert(m:find('cycle_regressions='..regress,1,true))
  assert(m:find('cycle_equal_adjacent='..equals,1,true))
  assert(m:find('cycle_regressions_same_frame='..
    ((clock_pattern=='within') and 1 or 0),1,true))
  assert(m:find('cycle_regressions_between_frames='..
    ((clock_pattern=='boundary') and 1 or 0),1,true))
  local log=read(dir..'/mmc3_video_writes.tsv')
  assert(log:find('3FFA\t00',1,true))
  local cycle_log=read(dir..'/mmc3_ppu_cycles.tsv')
  assert(cycle_log:find('\t3FFA\t00\tR',1,true))
  for _,frame in ipairs(frames) do
    local prefix=string.format('%s/frame_%06d',dir,frame)
    assert(os.remove(prefix..'.meta.txt'))
    assert(os.remove(prefix..'.ppu.bin'))
    assert(os.remove(prefix..'.ram.bin'))
  end
  for _,name in ipairs({'ppu_capture_session.meta.txt',
    'mmc3_video_writes.tsv','mmc3_ppu_cycles.tsv'}) do
    assert(os.remove(dir..'/'..name))
  end
  assert(os.execute('rmdir "'..dir..'"'))
end
check({1,2},true)
check({1,3},false)
check({1,2},false,'within')
check({1,2},false,'boundary')
check({1,2},true,'equal')
print('Stage85 PPU continuity / counter regressions / equality PASS')
