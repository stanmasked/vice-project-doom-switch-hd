-- Stage 38: opt-in *execution* trace, not postframe-only RAM sampling.
-- Run on user's local FCEUX; all outputs private. No original ROM data in Git.
-- Mapper mapping is unknown until the needed $8000/$8001 writes were observed.
local DIR=rawget(_G,'VPD_TRACE_DIRECTORY') or 'private'
local MAX=rawget(_G,'VPD_TRACE_MAX_EVENTS') or 20000
local LABEL=rawget(_G,'VPD_TRACE_SESSION_LABEL') or 'unverified_session'
assert(type(LABEL)=='string' and #LABEL<=120 and not LABEL:find('[\r\n=]'),
       'Session label must be one line without =, at most 120 bytes')
assert(type(MAX)=='number' and MAX==math.floor(MAX) and MAX>=1 and MAX<=500000,
       'VPD_TRACE_MAX_EVENTS must be an integer from 1 to 500000')
assert(type(memory)=='table' and type(memory.registerexec)=='function',
       'FCEUX memory.registerexec required for CPU execution tracing')
assert(type(memory.registerwrite)=='function' and type(memory.readbyte)=='function',
       'FCEUX RAM and mapper hooks required')
local clock=type(debugger)=='table' and type(debugger.getcyclescount)=='function'
local rom_md5=rom.gethash('md5')
assert(type(rom_md5)=='string' and #rom_md5>0,'Missing ROM identity')
local file=assert(io.open(DIR..'/stage38_dispatch_exec.tsv','wb'))
local fields={'frame','seq','cpu_cycle','kind','cpu_address','value','mmc3_mode',
              'r6','r7','mapped_bank','mapping_status','ram_07','ram_90','ram_91',
              'ram_92','ram_aa','ram_ab','ram_a8','ram_a9'}
assert(file:write(table.concat(fields,'\t')..'\n'))
local select_value,bank6,bank7=nil,nil,nil
local count,dropped,seq=0,0,0
local captured,frames={},{}
local function hex2(x) return x==nil and 'unknown' or string.format('%02X',x) end
local function hex4(x) return string.format('%04X',x) end
local function mode()
  if select_value==nil then return nil end
  return math.floor(select_value/64)%2
end
local function mapper_status(pc)
  if pc>=0xE000 then return 15,'fixed_last_bank' end
  local m=mode()
  if m==nil then return nil,'unknown_mode' end
  if pc>=0xC000 then
    if m==0 then return 14,'fixed_second_last_bank' end
    if bank6==nil then return nil,'unknown_r6' end
    return bank6%16,'mapped_r6'
  end
  if pc>=0xA000 then
    if bank7==nil then return nil,'unknown_r7' end
    return bank7%16,'mapped_r7'
  end
  if pc>=0x8000 then
    if m==1 then return 14,'fixed_second_last_bank' end
    if bank6==nil then return nil,'unknown_r6' end
    return bank6%16,'mapped_r6'
  end
  return nil,'not_prg_rom'
end
local function record(kind,addr,value)
  seq=seq+1
  if count>=MAX then dropped=dropped+1;return end
  local frame=emu.framecount()
  local c='unknown'
  if clock then
    local t=debugger.getcyclescount()
    assert(type(t)=='number' and t>=0 and t==math.floor(t),'Invalid cycle counter')
    c=string.format('%.0f',t)
  end
  local bank,status=mapper_status(addr)
  local ram={0x07,0x90,0x91,0x92,0xAA,0xAB,0xA8,0xA9}
  local row={tostring(frame),tostring(seq),c,kind,hex4(addr),hex2(value),
             mode()==nil and 'unknown' or tostring(mode()),
             hex2(bank6),hex2(bank7),bank==nil and 'unknown' or tostring(bank),status}
  for _,a in ipairs(ram) do row[#row+1]=hex2(memory.readbyte(a)) end
  assert(file:write(table.concat(row,'\t')..'\n'))
  count=count+1
  captured[kind]=(captured[kind] or 0)+1
  frames[frame]=true
end
-- Fixed-bank PC hooks plus bank-dependent candidates. CPU addresses
-- are not automatically physical PRG bank identities.
local pcs={0xE479,0xE4E6,0xE4F3,0xE500,0xE50F,0xE519,0xE522,
           0xE8DE,0xE8EA,0xE8EF,0xE418,
           0x835B,0xC906,0xC138,0xC1C8}
for _,pc in ipairs(pcs) do
  local local_pc=pc
  memory.registerexec(local_pc,function() record('EXEC',local_pc,nil) end)
end
local tracked_ram={0x07,0x90,0x91,0x92,0xAA,0xAB,0xA8,0xA9}
for _,addr in ipairs(tracked_ram) do
  local local_addr=addr
  memory.registerwrite(local_addr,function(a,size,value)
    record('RAM_WRITE',local_addr,value)
  end)
end
memory.registerwrite(0x8000,function(a,size,value)
  assert(type(value)=='number' and value>=0 and value<=255,
         'Mapper $8000 write value unavailable; trace cannot map banks')
  select_value=value
  record('MMC3_SELECT',0x8000,value)
end)
memory.registerwrite(0x8001,function(a,size,value)
  assert(type(value)=='number' and value>=0 and value<=255,
         'Mapper $8001 write value unavailable; trace cannot map banks')
  if select_value~=nil then
    local reg=select_value%8
    if reg==6 then bank6=value end
    if reg==7 then bank7=value end
  end
  record('MMC3_DATA',0x8001,value)
end)
emu.registerexit(function()
  assert(file:flush())
  assert(file:close())
  local meta=assert(io.open(DIR..'/stage38_dispatch_exec.meta.txt','wb'))
  local nframes=0
  for _ in pairs(frames) do nframes=nframes+1 end
  local txt={
    'format=vice_stage38_execution_v1',
    'session_label='..LABEL,
    'session_label_provenance=user_asserted_not_emulator_verified',
    'rom_md5='..rom_md5,
    'execution_hooks_registered='..tostring(#pcs),
    'tracked_ram_write_hooks='..tostring(#tracked_ram),
    'events_recorded='..tostring(count),
    'events_dropped='..tostring(dropped),
    'trace_complete='..(dropped==0 and 'yes' or 'no'),
    'frames_with_events='..tostring(nframes),
    'cycle_trace_available='..(clock and 'yes' or 'no'),
    'initial_mmc3_mode=unknown',
    'initial_prg_r6=unknown',
    'initial_prg_r7=unknown',
    'execution_provenance=registerexec_callbacks_not_source_disassembly',
    'warning=CPU bank is unresolved until mapper writes observed',
  }
  assert(meta:write(table.concat(txt,'\n')..'\n'))
  assert(meta:close())
end)
