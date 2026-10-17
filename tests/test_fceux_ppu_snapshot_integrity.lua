-- Stage82: verify real collector writes checksums and rejects SAME-SIZE
-- snapshot readback corruption. All bytes are invented, no ROM data.
local real_io=io
local function read(path)
  local f=assert(real_io.open(path,'rb'))
  local data=assert(f:read('*a'))
  assert(f:close())
  return data
end
local function run(case, screen)
  local dir=os.tmpname()
  os.remove(dir)
  assert(os.execute('mkdir -p "'..dir..'"'))
  VPD_CAPTURE_DIRECTORY=dir
  VPD_CAPTURE_INTERVAL=1
  VPD_CAPTURE_LIMIT=1
  VPD_CAPTURE_SCREEN=screen
  local after, exit, frame= nil,nil,1
  rom={gethash=function(which)
    assert(which=='md5')
    return string.rep('a',32)
  end}
  debugger=nil
  memory={
    registerwrite=function(addr,size,fn)
      assert(type(fn)=='function')
      assert((addr==0x2000 and size==0x2000) or
             (addr==0x8000 and size==0x8000))
    end,
    registerread=function(addr,size,fn)
      assert(addr==0x2000 and size==0x2000 and type(fn)=='function')
    end,
    readbyte=function()return 0 end,
    readbyterange=function(addr,size)
      assert(addr==0 and size==0x800)
      return string.rep(string.char(0x11),0x800)
    end,
  }
  ppu={readbyterange=function(addr,size)
    assert(addr==0 and size==0x4000)
    return string.rep(string.char(0x55),0x4000)
  end}
  emu={
    framecount=function()return frame end,
    registerafter=function(fn)after=fn end,
    registerexit=function(fn)exit=fn end,
    message=function()end,
    getscreenpixel=function(x,y,nes)
      assert(nes==true and x>=0 and x<256 and y>=0 and y<240)
      return 0,1,2,3
    end,
  }
  io={
    open=function(path,mode)
      local f,err=real_io.open(path,mode)
      if not f then return f,err end
      if case=='corrupt_ppu_readback'
          and path==dir..'/frame_000001.ppu.bin' and mode=='rb' then
        return {
          read=function(_,format)
            local bytes=f:read(format)
            if bytes and #bytes>0 then
              return string.char((bytes:byte(1)+1)%256)..bytes:sub(2)
            end
            return bytes
          end,
          close=function()return f:close() end
        }
      end
      return f
    end,
  }
  local ok,err=pcall(dofile,'tools/capture_fceux_ppu.lua')
  assert(ok,err)
  assert(type(after)=='function' and type(exit)=='function')
  ok,err=pcall(after)
  local prefix=dir..'/frame_000001'
  if case=='corrupt_ppu_readback' then
    assert(not ok and tostring(err):find('Snapshot readback mismatch',1,true),
           tostring(err))
    assert(read(prefix..'.meta.txt')=='capture_in_progress=yes\n')
  else
    assert(ok,tostring(err))
    local meta=read(prefix..'.meta.txt')
    assert(meta:find('snapshot_checksum=adler32_v1',1,true))
    assert(meta:find('ppu_adler32=BAEE413C',1,true))
    assert(meta:find('ram_adler32=6BE08801',1,true))
    assert(read(prefix..'.ppu.bin')==string.rep(string.char(0x55),0x4000))
    assert(read(prefix..'.ram.bin')==string.rep(string.char(0x11),0x800))
    if screen then
      assert(meta:find('screen_rgb_adler32=AF13D01F',1,true))
      assert(meta:find('screen_pal_adler32=1FCAD01F',1,true))
    else
      assert(meta:find('screen_rgb_adler32=not_captured',1,true))
      assert(meta:find('screen_pal_adler32=not_captured',1,true))
    end
  end
  ok,err=pcall(exit)
  assert(ok,err)
  local manifest=read(dir..'/ppu_capture_session.meta.txt')
  assert(manifest:find('complete='..
     (case=='corrupt_ppu_readback' and 'no' or 'yes'),1,true))
  -- Restore native io only AFTER exit; temporary wrappers must exercise
  -- the collector's disk I/O and readback.
  io=real_io
  local files={'ppu_capture_session.meta.txt','mmc3_video_writes.tsv',
               'frame_000001.meta.txt','frame_000001.ppu.bin'}
  if case~='corrupt_ppu_readback' then
    files[#files+1]='frame_000001.ram.bin'
  end
  if screen then
    files[#files+1]='frame_000001.screen.rgb.bin'
    files[#files+1]='frame_000001.screen.pal.bin'
  end
  for _,name in ipairs(files) do
    assert(os.remove(dir..'/'..name),name)
  end
  assert(os.execute('rmdir "'..dir..'"'))
end
run('normal',false)
run('normal',true)
run('corrupt_ppu_readback',false)
print('Stage82 snapshot checksums and same-size readback corruption PASS')
