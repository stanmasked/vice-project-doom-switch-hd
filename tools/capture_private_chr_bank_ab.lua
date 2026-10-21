-- PRIVATE owner-held original ROM/FM2 controlled MMC3 CHR-register experiment.
-- Store outputs locally; never upload original screenshots, ROM, FM2 or raw traces.
local function required(name)
  local value=os.getenv(name)
  assert(type(value)=='string' and #value>0,name..' required')
  return value
end
local directory=required('VPD_PRIVATE_CHR_AB_DIR')
local mode=required('VPD_PRIVATE_CHR_AB_MODE')
local target=tonumber(required('VPD_PRIVATE_CHR_AB_FRAME'))
local frames=tonumber(required('VPD_PRIVATE_FRAME_COUNT'))
local fm2=required('VPD_PRIVATE_FM2_PATH')
local identity=required('VPD_PRIVATE_ROM_PAYLOAD_MD5'):lower()
assert(mode=='original' or mode=='probe_chr1_zero','invalid CHR diagnostic mode')
assert(target and frames and target==math.floor(target) and
       frames==math.floor(frames) and target>=300 and
       target+2<frames and frames<=100000000,'invalid private movie window')
assert(#identity==32 and not identity:find('[^a-f0-9]'))
assert(type(memory)=='table' and type(memory.registerexec)=='function' and
       type(memory.getregister)=='function' and type(memory.setregister)=='function')
assert(type(emu)=='table' and type(emu.framecount)=='function' and
       type(emu.getscreenpixel)=='function' and type(emu.registerafter)=='function')
assert(rom.gethash('md5'):lower()==identity,'original ROM identity mismatch')
assert(movie.play(fm2,true) and movie.readonly() and movie.length()==frames,
       'original FM2 read-only playback not confirmed')
if type(emu.speedmode)=='function' then pcall(emu.speedmode,'turbo') end
local first,last,writer_hits,next_hits,restore_hits,done=nil,nil,0,0,0,false
local function save_new(filename,bytes)
  local full=directory..'/'..filename
  local old=io.open(full,'rb')
  if old then old:close();error('refusing to overwrite private game capture') end
  local f=assert(io.open(full,'wb'))
  assert(f:write(bytes) and f:close(),'private capture write failure')
end
memory.registerexec(0xE387,function()
  if emu.framecount()~=target then return end
  writer_hits=writer_hits+1
  assert(writer_hits==1,'MMC3 writer PC repeated')
  assert(memory.getregister('a')==2,'original MMC3 register #1 value changed')
  if mode=='probe_chr1_zero' then
    -- Change ONLY immediate STA $8001 input A=2 to A=0 for one frame.
    memory.setregister('a',0)
  end
end)
memory.registerexec(0xE38A,function()
  if emu.framecount()~=target then return end
  next_hits=next_hits+1
  assert(next_hits==1 and writer_hits==1,'next instruction not unique')
  if mode=='probe_chr1_zero' then
    assert(memory.getregister('a')==0,'CHR probe value no longer active')
    memory.setregister('a',2)
    restore_hits=restore_hits+1
  else
    assert(memory.getregister('a')==2,'unexpected original accumulator value')
  end
end)
local function capture(frame)
  local rgb,pal={},{}
  for y=0,239 do
    local rgbrow,palrow={},{}
    for x=0,255 do
      local r,g,b,index=emu.getscreenpixel(x,y,true)
      for _,part in ipairs({r,g,b}) do
        assert(type(part)=='number' and part==math.floor(part)
               and part>=0 and part<=255,'invalid screen RGB component')
      end
      assert(type(index)=='number' and index==math.floor(index)
             and ((index>=0 and index<=63) or index==254),
             'invalid original screen palette index')
      rgbrow[#rgbrow+1]=string.char(r,g,b)
      palrow[#palrow+1]=string.char(index)
    end
    rgb[#rgb+1]=table.concat(rgbrow)
    pal[#pal+1]=table.concat(palrow)
  end
  local name=string.format('frame_%06d',frame)
  save_new(name..'.ppm','P6\n256 240\n255\n'..table.concat(rgb))
  save_new(name..'.pal.bin',table.concat(pal))
end
emu.registerafter(function()
  if done then return end
  local frame=emu.framecount()
  if frame==last then return end
  assert(type(frame)=='number' and frame==math.floor(frame)
         and frame>=0 and frame<frames,'invalid movie frame counter')
  if first==nil then assert(frame<=1,'playback callback attached late');first=frame
  else assert(frame==last+1,'private FM2 playback gap') end
  last=frame
  if frame>=target-1 and frame<=target+2 then capture(frame) end
  if frame==target+2 then
    assert(writer_hits==1 and next_hits==1,'original CHR instruction missing')
    assert(restore_hits==(mode=='probe_chr1_zero' and 1 or 0),
           'diagnostic CPU A was not restored before E38A')
    assert(rom.gethash('md5'):lower()==identity and
           movie.readonly() and movie.length()==frames,
           'ROM or FM2 identity changed during replay')
    save_new('COMPLETE.txt',
      'format=private_chr_bank1_one_write_ab_v1\n'..
      'mode='..mode..'\n'..
      'target_frame='..target..'\n'..
      'first_observed_frame='..first..'\n'..
      'last_observed_frame='..last..'\n'..
      'frame_gaps=0\n'..
      'writer_pc_hits='..writer_hits..'\n'..
      'next_instruction_hits='..next_hits..'\n'..
      'accumulator_restored_before_e38a='..
         (mode=='probe_chr1_zero' and 'yes' or 'not_needed')..'\n'..
      'rom_payload_md5='..identity..'\n'..
      'fm2_readonly=yes\n')
    done=true
    if type(emu.exit)=='function' then emu.exit() end
  end
end)
