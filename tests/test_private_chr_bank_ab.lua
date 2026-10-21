-- Entirely synthetic API mock: NEVER references original ROM, FM2 or pixel assets.
local root=os.tmpname()..'_chr_ab_mock'
assert(os.execute('mkdir -p '..root))
local prior_getenv=os.getenv
local outputs={}
for _,mode in ipairs({'original','probe_chr1_zero'}) do
  local dir=root..'/'..mode
  assert(os.execute('mkdir -p '..dir))
  local env={
    VPD_PRIVATE_CHR_AB_DIR=dir,
    VPD_PRIVATE_CHR_AB_MODE=mode,
    VPD_PRIVATE_CHR_AB_FRAME='600',
    VPD_PRIVATE_FRAME_COUNT='604',
    VPD_PRIVATE_FM2_PATH='/tmp/invented.fm2',
    VPD_PRIVATE_ROM_PAYLOAD_MD5=string.rep('e',32)
  }
  os.getenv=function(key)return env[key] or prior_getenv(key)end
  local frame,callback,accumulator,mutated=0,nil,0,false
  local hook={}
  rom={gethash=function(k)assert(k=='md5');return string.rep('e',32)end}
  movie={
    play=function(path,readonly)
      assert(path==env.VPD_PRIVATE_FM2_PATH and readonly);return true
    end,
    readonly=function()return true end,
    length=function()return 604 end
  }
  memory={
    registerexec=function(pc,fn)assert(hook[pc]==nil);hook[pc]=fn end,
    getregister=function(k)assert(k=='a');return accumulator end,
    setregister=function(k,val)
      assert(k=='a' and (val==0 or val==2))
      accumulator=val
      if val==0 then mutated=true end
    end
  }
  emu={
    framecount=function()return frame end,
    registerafter=function(fn)assert(callback==nil);callback=fn end,
    getscreenpixel=function(x,y,indexed)
      assert(indexed and x>=0 and x<=255 and y>=0 and y<=239)
      if mutated and frame==601 and x==100 and y==150 then
        return 213,5,56,31
      end
      return 32,32,32,9
    end
  }
  dofile('tools/capture_private_chr_bank_ab.lua')
  assert(type(hook[0xE387])=='function' and type(hook[0xE38A])=='function')
  for n=0,602 do
    frame=n
    if frame==600 then
      accumulator=2
      hook[0xE387]()
      hook[0xE38A]()
      assert(accumulator==2,'CPU A not restored by next original instruction')
    end
    callback()
  end
  local function read(name)
    local f=assert(io.open(dir..'/'..name,'rb'))
    local content=assert(f:read('*a'));assert(f:close());return content
  end
  local witness=read('COMPLETE.txt')
  assert(witness:find('mode='..mode,1,true))
  assert(witness:find('accumulator_restored_before_e38a='..
      (mode=='probe_chr1_zero' and 'yes' or 'not_needed'),1,true))
  assert(witness:find('target_frame=600',1,true))
  assert(witness:find('rom_payload_md5='..string.rep('e',32),1,true))
  assert(witness:find('fm2_readonly=yes',1,true))
  assert(mutated==(mode=='probe_chr1_zero'))
  outputs[mode]=read
end
local a,b=outputs.original,outputs.probe_chr1_zero
for _,n in ipairs({599,600,602}) do
  local name=string.format('frame_%06d',n)
  assert(a(name..'.ppm')==b(name..'.ppm'))
  assert(a(name..'.pal.bin')==b(name..'.pal.bin'))
end
assert(a('frame_000601.ppm')~=b('frame_000601.ppm'))
assert(a('frame_000601.pal.bin')~=b('frame_000601.pal.bin'))
print('PRIVATE_CHR_BANK_SYNTHETIC_CALLBACKS_PASS frame=600 one_write_and_restore')
assert(os.execute('rm -rf '..root))
os.getenv=prior_getenv
