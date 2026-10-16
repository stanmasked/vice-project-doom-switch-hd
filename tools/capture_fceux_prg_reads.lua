-- Stage45: one-session CPU PRG read and MMC3 write observations (experimental).
-- Run only on a private FCEUX session with an existing output directory.
local DIR=rawget(_G,'VPD_PRG_DIRECTORY') or 'private'
local MAX=rawget(_G,'VPD_PRG_MAX_EVENTS') or 50000
assert(type(MAX)=='number' and MAX==math.floor(MAX) and MAX>=1 and MAX<=500000)
assert(type(memory)=='table' and type(memory.registerread)=='function' and
  type(memory.registerwrite)=='function','FCEUX read/write callbacks required')
assert(type(emu)=='table' and type(emu.framecount)=='function' and
  type(emu.registerexit)=='function','FCEUX emu callback API required')
local file=assert(io.open(DIR..'/stage45_prg_reads.tsv','wb'))
assert(file:write('frame\tseq\tkind\tcpu_address\tvalue\tmapped_bank\n'))
local selected,r6,r7=nil,nil,nil
local count,dropped,callback_errors=0,0,0
local function bank(addr)
  if addr>=0xE000 then return 15 end
  if selected==nil then return nil end
  local mode=math.floor(selected/64)%2
  if addr>=0xC000 then return mode==0 and 14 or (r6 and r6%16 or nil) end
  if addr>=0xA000 then return r7 and r7%16 or nil end
  if addr>=0x8000 then return mode==1 and 14 or (r6 and r6%16 or nil) end
  return nil
end
local function log(kind,addr,value)
  if kind=='READ' then
    assert(value==nil,'READ value must not be treated as ROM data')
  else
    assert(type(value)=='number' and value==math.floor(value) and
      value>=0 and value<=255,'FCEUX mapper write byte unavailable')
  end
  if kind=='SELECT' then selected=value
  elseif kind=='DATA' and selected~=nil then
    if selected%8==6 then r6=value end
    if selected%8==7 then r7=value end
  end
  if count>=MAX then dropped=dropped+1;return end
  count=count+1
  local b=bank(addr)
  assert(file:write(table.concat({tostring(emu.framecount()),tostring(count),
    kind,string.format('%04X',addr),value and string.format('%02X',value) or 'unknown',
    b and tostring(b) or 'unknown'},'\t')..'\n'))
end
memory.registerwrite(0x8000,function(a,size,value) log('SELECT',0x8000,value) end)
memory.registerwrite(0x8001,function(a,size,value) log('DATA',0x8001,value) end)
-- Record all cartridge CPU-window reads, not just pointer-byte RAM reads.
-- Hardware/ROM identity and real callback semantics require live FCEUX checks.
memory.registerread(0x8000,0x8000,function(addr,size,value)
  assert(type(addr)=='number' and addr>=0x8000 and addr<=0xFFFF,
    'Invalid PRG CPU read address')
  if size~=1 or value~=0 then
    callback_errors=callback_errors+1
    error('Unsupported FCEUX READ callback zero sentinel')
  end
  log('READ',addr,nil)
end)
emu.registerexit(function()
  assert(file:close())
  local meta=assert(io.open(DIR..'/stage45_prg_reads.meta.txt','wb'))
  assert(meta:write(table.concat({
    'format=vice_stage45_prg_reads_v1',
    'events_recorded='..count,
    'events_dropped='..dropped,
    'complete='..(dropped==0 and callback_errors==0 and 'yes' or 'no'),
    'callback_errors='..callback_errors,
    'initial_mmc3_mode=unknown',
    'read_provenance=registerread_callback_no_pc_proof',
    'read_value_provenance=address_only_fceux_zero_sentinel'
  },'\n')..'\n'))
  assert(meta:close())
end)
