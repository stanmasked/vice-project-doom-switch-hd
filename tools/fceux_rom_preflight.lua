-- Stage68: iNES header-only identity gate for the expected mapper4, 128KiB PRG.
-- Reads at most the 16 header bytes through FCEUX ROM APIs, never dumps ROM data.
local M={}
local function byte(rom_api,offset)
  local getter=rom_api.readbyteunsigned or rom_api.readbyte
  assert(type(getter)=='function','FCEUX ROM header reader unavailable')
  local v=getter(offset)
  assert(type(v)=='number' and v==math.floor(v) and v>=0 and v<=255,
         'FCEUX returned invalid ROM header byte')
  return v
end
function M.inspect(expected_md5, rom_api)
  assert(expected_md5==nil or type(expected_md5)=='string',
         'Expected ROM MD5 must be a string or nil')
  if expected_md5~=nil then
    assert(#expected_md5==32 and expected_md5:match('^[0-9a-fA-F]+$'),
           'Expected ROM MD5 must be 32 hex digits')
  end
  local api=rom_api or rom
  assert(type(api)=='table','FCEUX ROM interface unavailable')
  local h={}
  for i=0,15 do h[i]=byte(api,i) end
  assert(h[0]==0x4E and h[1]==0x45 and h[2]==0x53 and h[3]==0x1A,
         'Loaded file is not an iNES ROM')
  local format_bits=math.floor(h[7]/4)%4
  assert(format_bits==0,'Unrecognized iNES header version / NES 2.0')
  local mapper=math.floor(h[6]/16)+(h[7]-h[7]%16)
  assert(mapper==4,'Expected MMC3 mapper 4 ROM')
  assert(h[4]==8,'Expected 128 KiB PRG (eight 16 KiB banks)')
  -- A mapper+PRG match alone cannot identify the game. Optional locally pinned
  -- MD5 detects switching ROM images without copying the hash into reports.
  local pinned=false
  if expected_md5~=nil then
    assert(type(api.gethash)=='function','FCEUX rom.gethash unavailable')
    local actual=api.gethash('md5')
    assert(type(actual)=='string' and #actual==32 and
           actual:match('^[0-9a-fA-F]+$'), 'Invalid FCEUX ROM MD5')
    assert(actual:lower()==expected_md5:lower(),
           'Loaded FCEUX ROM does not match expected private MD5')
    pinned=true
  end
  return {profile='ines_mapper4_prg128k',
          trainer=(math.floor(h[6]/4)%2==1),
          prg_bytes=131072,
          md5_pin=pinned and 'matched' or 'not_supplied',
          identity_authenticated=false}
end
return M
