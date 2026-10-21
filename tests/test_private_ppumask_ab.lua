-- Entirely synthetic PPUMASK A/B FCEUX API regression, no original pixels.
local original_getenv=os.getenv
local root=os.tmpname()..'_ppumask_ab_mock'
assert(os.execute('mkdir -p '..root))
local function run(mode)
  local directory=root..'/'..mode
  assert(os.execute('mkdir -p '..directory))
  local env={
    VPD_PRIVATE_AB_DIR=directory,
    VPD_PRIVATE_AB_MODE=mode,
    VPD_PRIVATE_AB_FRAME='600',
    VPD_PRIVATE_FRAME_COUNT='604',
    VPD_PRIVATE_FM2_PATH='/tmp/synthetic_invented.fm2',
    VPD_PRIVATE_ROM_PAYLOAD_MD5=string.rep('f',32)
  }
  os.getenv=function(key)return env[key] or original_getenv(key)end
  local frame,after,accumulator,mutated=0,nil,0,false
  local handlers={}
  rom={gethash=function(key)assert(key=='md5');return string.rep('f',32)end}
  movie={
    play=function(file,readonly)
      assert(file==env.VPD_PRIVATE_FM2_PATH and readonly);return true
    end,
    readonly=function()return true end,
    length=function()return 604 end
  }
  memory={
    registerexec=function(pc,cb)
      assert(pc==0xE38E or pc==0xE391)
      assert(handlers[pc]==nil);handlers[pc]=cb
    end,
    getregister=function(key)assert(key=='a');return accumulator end,
    setregister=function(key,val)
      assert(key=='a' and val==0x06)
      accumulator=val;mutated=true
    end
  }
  emu={
    framecount=function()return frame end,
    registerafter=function(cb)assert(after==nil);after=cb end,
    getscreenpixel=function(x,y,raw)
      assert(raw==true and x>=0 and x<256 and y>=0 and y<240)
      if mutated and frame==601 and x==100 and y==202 then
        return 200,18,10,31
      end
      return 36,36,36,9
    end
  }
  dofile('tools/capture_private_ppumask_ab.lua')
  assert(type(handlers[0xE38E])=='function' and
         type(handlers[0xE391])=='function' and type(after)=='function')
  for value=0,602 do
    frame=value
    if frame==600 then
      accumulator=14
      handlers[0xE38E]()
      handlers[0xE391]()
      assert(accumulator==14,'accumulator not restored before RTS')
    end
    after()
  end
  local function read(name)
    local file=assert(io.open(directory..'/'..name,'rb'))
    local body=assert(file:read('*a'));assert(file:close());return body
  end
  local witness=read('COMPLETE.txt')
  assert(witness:find('mode='..mode,1,true))
  assert(witness:find('target_instruction_hits=1',1,true))
  assert(witness:find('accumulator_restored_before_rts='..
         (mode=='probe_bg_off' and 'yes' or 'not_needed'),1,true))
  assert(witness:find('frame_gaps=0',1,true))
  assert(witness:find('source_rom_unchanged=yes',1,true))
  assert(witness:find('fm2_readonly=yes',1,true))
  assert(mutated==(mode=='probe_bg_off'))
  return read
end
local baseline=run('original')
local changed=run('probe_bg_off')
for _,frame in ipairs({599,600,602}) do
  local name=string.format('frame_%06d',frame)
  assert(baseline(name..'.ppm')==changed(name..'.ppm'))
  assert(baseline(name..'.pal.bin')==changed(name..'.pal.bin'))
end
assert(baseline('frame_000601.ppm')~=changed('frame_000601.ppm'))
assert(baseline('frame_000601.pal.bin')~=changed('frame_000601.pal.bin'))
print('PRIVATE_PPUMASK_AB_SYNTHETIC_CALLBACK_PASS target=600 affected_frame=601')
assert(os.execute('rm -rf '..root))
os.getenv=original_getenv
