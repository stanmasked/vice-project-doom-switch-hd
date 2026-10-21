-- Private, bounded MMC3 CHR mapper-selection witness.
-- Observe CPU $8000/$8001 selection only. This does NOT prove PPU rendering.
local function required(name)
  local result=os.getenv(name)
  assert(type(result)=='string' and #result>0,name..' is required')
  return result
end
local path=required('VPD_PRIVATE_MMC3_TRACE_PATH')
local summary_path=required('VPD_PRIVATE_MMC3_SUMMARY_PATH')
local target_last_frame=tonumber(required('VPD_PRIVATE_FRAME_COUNT'))-1
assert(target_last_frame>=1 and target_last_frame==math.floor(target_last_frame),
       'invalid private terminal frame for MMC3 trace')
local targets=required('VPD_PRIVATE_MMC3_TARGETS')
local count=tonumber(required('VPD_PRIVATE_MMC3_BANK_COUNT'))
local interval=tonumber(required('VPD_PRIVATE_CAPTURE_INTERVAL'))
assert(count and count==math.floor(count) and count>=2 and count<=4096,
       'invalid MMC3 CHR bank count')
assert(interval and interval==math.floor(interval) and interval>=1 and interval<=120000,
       'invalid mapper trace frame interval')
assert(type(emu)=='table' and type(emu.framecount)=='function' and
       type(memory)=='table' and type(memory.registerwrite)=='function',
       'real FCEUX register write API required')
local focus={}
local focus_count=0
for item in string.gmatch(targets,'[^,]+') do
  local number=tonumber(item)
  assert(number and number==math.floor(number) and number>=0 and number<count,
         'MMC3 focus bank invalid or outside ROM')
  if not focus[number] then focus[number]=true;focus_count=focus_count+1 end
end
assert(focus_count>=1 and focus_count<=64,'MMC3 focus requires 1..64 banks')
local prior=io.open(path,'rb')
if prior then prior:close();error('refusing to overwrite private MMC3 trace') end
local trace=assert(io.open(path,'wb'))
assert(trace:write('frame\taddress\tvalue\n'))
assert(trace:flush())
local select_value=nil
local logged=0
local raw_relevant=0
local repeats=0
local trace_finalized=false
local seen={}
local MAX_PAIR_COUNT=80000
local function write_select(address,size,value)
  assert(type(value)=='number' and value>=0 and value<=255,
         'invalid FCEUX mapper select value')
  select_value=value
end
local function write_data(address,size,value)
  if select_value==nil then return end
  local register=select_value % 8
  if register>5 then return end
  local bank=value
  assert(type(bank)=='number' and bank>=0 and bank<=255,
         'invalid FCEUX mapper data value')
  local relevant=false
  if register<2 then
    local low=bank-(bank%2)
    relevant=focus[low%count] or focus[(low+1)%count]
  else
    relevant=focus[bank%count]
  end
  if not relevant then return end
  local frame=emu.framecount()
  assert(type(frame)=='number' and frame>=0 and frame==math.floor(frame),
         'invalid FCEUX mapper event frame')
  local bucket=math.floor(frame/interval)
  local key=bucket..':'..select_value..':'..bank
  assert(not trace_finalized,'MMC3 mapping after trace finalization')
  raw_relevant=raw_relevant+1
  if seen[key] then
    repeats=repeats+1
    return
  end
  seen[key]=true
  logged=logged+1
  assert(logged<=MAX_PAIR_COUNT,'private MMC3 trace exceeded event budget')
  -- Emit actual matching selection/data write pair, not proprietary payload.
  assert(trace:write(string.format('%d\t8000\t%02X\n%d\t8001\t%02X\n',
                                   frame,select_value,frame,bank)))
  assert(trace:flush(),'cannot flush private MMC3 trace')
end
memory.registerwrite(0x8000,write_select)
memory.registerwrite(0x8001,write_data)

-- This function is invoked by the private full-FM2 runner BEFORE its
-- terminal witness, never by an independent background callback. A
-- successful full-run witness therefore requires a closed mapper trace.
VPD_FINALIZE_PRIVATE_MMC3_TRACE=function(frame)
  assert(not trace_finalized,'MMC3 trace finalized more than once')
  assert(frame==target_last_frame,'MMC3 trace ended before terminal FM2 frame')
  assert(raw_relevant==logged+repeats,'MMC3 deduplication totals inconsistent')
  assert(trace:flush(),'private MMC3 trace could not flush')
  assert(trace:close(),'private MMC3 trace could not close')
  trace_finalized=true
  local old=io.open(summary_path,'rb')
  if old then old:close();error('private MMC3 summary already exists') end
  local file=assert(io.open(summary_path,'wb'))
  assert(file:write(
    'format=private_mmc3_chr_trace_witness_v1\n'..
    'movie_terminal_frame='..frame..'\n'..
    'raw_matching_mapping_writes='..raw_relevant..'\n'..
    'retained_deduplicated_mapping_pairs='..logged..'\n'..
    'suppressed_repeated_mapping_writes='..repeats..'\n'..
    'trace_closed=yes\n'..
    'ppu_rendering_proven=no\n'
  ))
  assert(file:close(),'cannot close private MMC3 summary')
end
