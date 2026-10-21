-- Private FCEUX-rendered storyboard, no commercial ROM or FM2 in GitHub.
local DIRECTORY=rawget(_G,'VPD_STORYBOARD_DIRECTORY') or 'private/storyboard'
local function bounded(name,fallback,lo,hi)
  local v=rawget(_G,name)
  if v==nil then return fallback end
  assert(type(v)=='number' and v==math.floor(v) and v>=lo and v<=hi,
         name..' out of bounds')
  return v
end
local START=bounded('VPD_STORYBOARD_START_FRAME',0,0,999999999)
local STOP=bounded('VPD_STORYBOARD_STOP_FRAME',999999999,0,999999999)
local INTERVAL=bounded('VPD_STORYBOARD_INTERVAL',1803,1,120000)
local LIMIT=bounded('VPD_STORYBOARD_LIMIT',48,1,64)
assert(STOP>=START,'stop frame precedes start')
assert(type(emu)=='table' and type(emu.registerafter)=='function' and
       type(emu.framecount)=='function' and type(emu.getscreenpixel)=='function',
       'FCEUX screen API missing')
assert(type(rom)=='table' and type(rom.gethash)=='function','FCEUX ROM API missing')
local rom_hash=rom.gethash('md5')
assert(type(rom_hash)=='string' and #rom_hash==32 and
       not rom_hash:find('[^0-9a-fA-F]'),'ROM hash invalid')
local count,last_frame=0,-1
local function save(path,content)
  local old=io.open(path,'rb')
  if old then old:close();error('refusing overwrite of private screenshot') end
  local f,err=io.open(path,'wb')
  assert(f,'private storyboard directory must exist: '..tostring(err))
  assert(f:write(content),'storyboard write failed')
  assert(f:close(),'storyboard close failed')
end
local function record(frame)
  local pixels,palette={},{}
  local unavailable=0
  for y=0,239 do
    local rgbrow,palrow={},{}
    for x=0,255 do
      local r,g,b,idx=emu.getscreenpixel(x,y,true)
      for _,component in ipairs({r,g,b}) do
        assert(type(component)=='number' and component==math.floor(component)
               and component>=0 and component<=255,'invalid FCEUX RGB')
      end
      assert(type(idx)=='number' and idx==math.floor(idx) and
             ((idx>=0 and idx<=63) or idx==254),'invalid NES palette index')
      if idx==254 then unavailable=unavailable+1 end
      rgbrow[#rgbrow+1]=string.char(r,g,b)
      palrow[#palrow+1]=string.char(idx)
    end
    pixels[#pixels+1]=table.concat(rgbrow)
    palette[#palette+1]=table.concat(palrow)
  end
  local prefix=DIRECTORY..'/frame_'..string.format('%06d',frame)
  save(prefix..'.ppm','P6\n256 240\n255\n'..table.concat(pixels))
  save(prefix..'.pal.bin',table.concat(palette))
  save(prefix..'.meta.txt',table.concat({
    'format=private_fceux_storyboard_v1','frame='..frame,
    'rom_md5='..rom_hash,'interval='..INTERVAL,
    'start_frame='..START,'stop_frame='..STOP,
    'capture_limit='..LIMIT,'invalid_palette_values='..unavailable,
    'screen_size=256x240','source=emu.getscreenpixel',''
  },'\n'))
end
emu.registerafter(function()
  local frame=emu.framecount()
  if frame==last_frame then return end
  last_frame=frame
  local terminal=frame==STOP
  -- Frame 0 may have elapsed before this after-frame hook is registered.
  -- Never plan or emit it as a reliable storyboard sample.
  if frame==0 or count>=LIMIT or frame<START or frame>STOP or
     (frame%INTERVAL~=0 and not terminal) then return end
  record(frame)
  count=count+1
  if type(emu.message)=='function' then
    emu.message('Private storyboard '..count..'/'..LIMIT)
  end
end)
