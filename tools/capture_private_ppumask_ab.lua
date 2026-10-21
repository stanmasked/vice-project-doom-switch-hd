-- PRIVATE original ROM+FM2 PPUMASK single-write intervention experiment.
-- Use TWO fresh local dirs: original and probe_bg_off. No original data in Git.
-- This is a modified emulator execution, not unmodified-game reproduction.
local function required(key)
  local val=os.getenv(key)
  assert(type(val)=='string' and #val>0,key..' required')
  return val
end
local directory=required('VPD_PRIVATE_AB_DIR')
local mode=required('VPD_PRIVATE_AB_MODE')
local target=tonumber(required('VPD_PRIVATE_AB_FRAME'))
local frames=tonumber(required('VPD_PRIVATE_FRAME_COUNT'))
local fm2=required('VPD_PRIVATE_FM2_PATH')
local identity=required('VPD_PRIVATE_ROM_PAYLOAD_MD5'):lower()
assert(mode=='original' or mode=='probe_bg_off')
assert(target and frames and target==math.floor(target) and
       frames==math.floor(frames) and target>=300 and target+2<frames)
assert(#identity==32 and not identity:find('[^0-9a-f]'))
assert(type(memory.registerexec)=='function' and
       type(memory.getregister)=='function' and
       type(memory.setregister)=='function')
assert(type(emu.getscreenpixel)=='function' and type(emu.registerafter)=='function')
assert(rom.gethash('md5'):lower()==identity)
assert(movie.play(fm2,true) and movie.readonly() and movie.length()==frames)
if type(emu.speedmode)=='function' then pcall(emu.speedmode,'turbo') end
local first,last,hit,restore_hits,done=nil,nil,0,0,false

local function new_file(name,bytes)
  local path=directory..'/'..name
  local existing=io.open(path,'rb')
  if existing then existing:close();error('refusing overwrite of private capture') end
  local out=assert(io.open(path,'wb'))
  assert(out:write(bytes) and out:close())
end

memory.registerexec(0xE38E,function()
  if emu.framecount()~=target then return end
  hit=hit+1
  assert(hit==1,'CPU instruction unexpectedly repeated')
  assert(memory.getregister('a')==0x0E,'original PPUMASK source not as expected')
  if mode=='probe_bg_off' then
    -- Local counterfactual: only the imminent STA $2001 receives A=0x06.
    -- No ROM/FM2 bytes are changed; downstream CPU state may differ.
    memory.setregister('a',0x06)
  end
end)

-- The original next instruction is RTS at $E391. Restore A before the
-- return so the diagnostic branch differs solely in the earlier STA $2001.
memory.registerexec(0xE391,function()
  if emu.framecount()~=target then return end
  assert(hit==1,'PPUMASK writer must precede RTS')
  if mode=='probe_bg_off' then
    assert(memory.getregister('a')==0x06,'intervention unexpectedly altered')
    memory.setregister('a',0x0E)
    restore_hits=restore_hits+1
  else
    assert(memory.getregister('a')==0x0E,'original A unexpectedly changed')
  end
end)

local function capture(frame)
  local rgb,palette={},{}
  for y=0,239 do
    local rgbrow,palrow={},{}
    for x=0,255 do
      local r,g,b,idx=emu.getscreenpixel(x,y,true)
      for _,value in ipairs({r,g,b}) do
        assert(type(value)=='number' and value==math.floor(value) and
               value>=0 and value<=255,'invalid private RGB')
      end
      assert(type(idx)=='number' and idx==math.floor(idx) and
             ((idx>=0 and idx<=63) or idx==254),'invalid NES palette index')
      rgbrow[#rgbrow+1]=string.char(r,g,b)
      palrow[#palrow+1]=string.char(idx)
    end
    rgb[#rgb+1]=table.concat(rgbrow)
    palette[#palette+1]=table.concat(palrow)
  end
  local prefix=string.format('frame_%06d',frame)
  new_file(prefix..'.ppm','P6\n256 240\n255\n'..table.concat(rgb))
  new_file(prefix..'.pal.bin',table.concat(palette))
end

emu.registerafter(function()
  if done then return end
  local frame=emu.framecount()
  if frame==last then return end
  assert(type(frame)=='number' and frame==math.floor(frame)
         and frame>=0 and frame<frames)
  if first==nil then assert(frame<=1,'movie callback attached late');first=frame
  else assert(frame==last+1,'noncontiguous original FM2 callbacks') end
  last=frame
  if frame>=target-1 and frame<=target+2 then capture(frame) end
  if frame==target+2 then
    assert(hit==1,'target original CPU instruction not observed once')
    assert(restore_hits==(mode=='probe_bg_off' and 1 or 0),
           'CPU accumulator was not restored before RTS')
    assert(movie.readonly() and movie.length()==frames and
           rom.gethash('md5'):lower()==identity,'ROM or FM2 changed')
    new_file('COMPLETE.txt','format=private_ppumask_one_write_ab_v1\n'..
      'mode='..mode..'\nframe='..target..'\n'..
      'first_observed_frame='..first..'\n'..
      'last_observed_frame='..frame..'\nframe_gaps=0\n'..
      'target_instruction_hits='..hit..'\n'..
      'accumulator_restored_before_rts='..(mode=='probe_bg_off' and 'yes' or 'not_needed')..'\n'..
      'source_rom_unchanged=yes\nfm2_readonly=yes\n')
    done=true
    if type(emu.exit)=='function' then emu.exit() end
  end
end)
