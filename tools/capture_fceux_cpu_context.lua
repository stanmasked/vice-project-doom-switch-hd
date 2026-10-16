-- Stage52 optional CPU register probe. Separate session from joint tracer.
-- Registers are sampled at sparse execution hooks, not per-instruction attribution.
local DIR=rawget(_G,'VPD_CPU_CONTEXT_DIRECTORY') or 'private'
local MAX=rawget(_G,'VPD_CPU_CONTEXT_MAX_EVENTS') or 10000
assert(type(MAX)=='number' and MAX==math.floor(MAX) and MAX>=1 and MAX<=500000)
assert(type(memory)=='table' and type(memory.registerexec)=='function')
assert(type(emu)=='table' and type(emu.framecount)=='function' and type(emu.registerexit)=='function')
-- Invalidate metadata from an earlier session BEFORE replacing its TSV.
-- A crash or callback exception must never reuse an old complete=yes.
local meta_path=DIR..'/stage52_cpu_context.meta.txt'
local pending=assert(io.open(meta_path,'wb'))
assert(pending:write('capture_in_progress=yes\n'))
assert(pending:close())
local file=assert(io.open(DIR..'/stage52_cpu_context.tsv','wb'))
assert(file:write('frame\tseq\tpc\ta\tx\ty\ts\tp\tregister_status\n'))
local count,dropped=0,0
local function sample(name)
  if type(memory.getregister)~='function' then return 'unknown' end
  local ok,value=pcall(memory.getregister,name:lower())
  if not ok or type(value)~='number' or value~=math.floor(value)
    or value<0 or value>255 then return 'unknown' end
  return string.format('%02X',value)
end
for _,pc in ipairs({0xE479,0xE4E6,0xE4F3,0x835B,0xC906}) do
  local address=pc
  memory.registerexec(address,function()
    if count>=MAX then dropped=dropped+1;return end
    count=count+1
    local values={sample('A'),sample('X'),sample('Y'),sample('S'),sample('P')}
    local complete=true
    for _,v in ipairs(values) do if v=='unknown' then complete=false end end
    assert(file:write(table.concat({tostring(emu.framecount()),tostring(count),
      string.format('%04X',address),values[1],values[2],values[3],
      values[4],values[5],complete and 'sampled' or 'partial_unknown'},'\t')..'\n'))
  end)
end
emu.registerexit(function()
  assert(file:close())
  local m=assert(io.open(meta_path,'wb'))
  assert(m:write(table.concat({
    'format=vice_stage52_cpu_context_v1',
    'events_recorded='..count,'events_dropped='..dropped,
    'complete='..(dropped==0 and 'yes' or 'no'),
    'provenance=sparse_registerexec_samples',
    'register_api=memory.getregister',
    'effective_address=not_recorded',
    'instruction_opcode=not_recorded'
  },'\n')..'\n'))
  assert(m:close())
end)
