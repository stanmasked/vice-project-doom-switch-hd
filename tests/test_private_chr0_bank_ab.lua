-- Entirely synthetic API mock: NEVER references original ROM, FM2 or pixel assets.
local root=os.tmpname()..'_chr0_ab_mock'
assert(os.execute('mkdir -p '..root))
local prior_getenv=os.getenv
local outputs={}
for _,mode in ipairs({'original','probe_chr0_two'}) do
  local dir=root..'/'..mode
  assert(os.execute('mkdir -p '..dir))
  local env={
    VPD_PRIVATE_CHR0_AB_DIR=dir,
    VPD_PRIVATE_CHR0_AB_MODE=mode,
    VPD_PRIVATE_CHR0_AB_FRAME='600',
    VPD_PRIVATE_FRAME_COUNT='604',
    VPD_PRIVATE_FM2_PATH='/tmp/invented.fm2',
    VPD_PRIVATE_ROM_PAYLOAD_MD5=string.rep('e',32)
  }
  os.getenv=function(key)return env[key] or prior_getenv(key)end
  local frame,callback,reg_x,mutated=0,nil,0,false
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
    getregister=function(k)assert(k=='x');return reg_x end,
    setregister=function(k,val)
      assert(k=='x' and (val==0 or val==2))
      reg_x=val
      if val==2 then mutated=true end
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
  dofile('tools/capture_private_chr0_bank_ab.lua')
  assert(type(hook[0xE380])=='function' and type(hook[0xE383])=='function')
  for n=0,602 do
    frame=n
    if frame==600 then
      reg_x=0
      hook[0xE380]()
      hook[0xE383]()
      assert(reg_x==0,'CPU X not restored by next original instruction')
    end
    callback()
  end
  local function read(name)
    local f=assert(io.open(dir..'/'..name,'rb'))
    local content=assert(f:read('*a'));assert(f:close());return content
  end
  local witness=read('COMPLETE.txt')
  assert(witness:find('mode='..mode,1,true))
  assert(witness:find('cpu_x_restored_before_e383='..
      (mode=='probe_chr0_two' and 'yes' or 'not_needed'),1,true))
  assert(witness:find('target_frame=600',1,true))
  assert(witness:find('rom_payload_md5='..string.rep('e',32),1,true))
  assert(witness:find('fm2_readonly=yes',1,true))
  assert(mutated==(mode=='probe_chr0_two'))
  outputs[mode]=read
end
local a,b=outputs.original,outputs.probe_chr0_two
for _,n in ipairs({599,600,602}) do
  local name=string.format('frame_%06d',n)
  assert(a(name..'.ppm')==b(name..'.ppm'))
  assert(a(name..'.pal.bin')==b(name..'.pal.bin'))
end
assert(a('frame_000601.ppm')~=b('frame_000601.ppm'))
assert(a('frame_000601.pal.bin')~=b('frame_000601.pal.bin'))
print('PRIVATE_CHR0_BANK_SYNTHETIC_CALLBACKS_PASS frame=600 one_write_and_restore')
assert(os.execute('rm -rf '..root))
os.getenv=prior_getenv
