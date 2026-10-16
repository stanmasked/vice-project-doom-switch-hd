-- Stage49 opt-in joint event stream: PC execution hooks, CPU PRG reads and MMC3 writes.
-- A preceding EXEC is not proof that it caused a subsequent READ.
local DIR=rawget(_G,'VPD_JOINT_DIRECTORY') or 'private'
local MAX=rawget(_G,'VPD_JOINT_MAX_EVENTS') or 20000
assert(type(MAX)=='number' and MAX==math.floor(MAX) and MAX>=1 and MAX<=500000)
assert(memory and memory.registerexec and memory.registerread and memory.registerwrite)
assert(emu and emu.framecount and emu.registerexit)
local output=assert(io.open(DIR..'/stage49_joint.tsv','wb'))
assert(output:write('frame\tseq\tkind\taddress\tvalue\tphysical_bank\n'))
local selected,r6,r7=nil,nil,nil
local count,dropped,callback_errors=0,0,0
local function bank(pc)
  if pc>=0xE000 then return 15 end
  if selected==nil then return nil end
  local mode=math.floor(selected/64)%2
  if pc>=0xC000 then
    if mode==0 then return 14 else return r6 and r6%16 or nil end
  elseif pc>=0xA000 then return r7 and r7%16 or nil
  elseif pc>=0x8000 then
    if mode==1 then return 14 else return r6 and r6%16 or nil end
  end
  return nil
end
local function log(kind,addr,value)
  assert(type(addr)=='number' and addr==math.floor(addr) and addr>=0x8000 and addr<=0xFFFF)
  if value~=nil then
    assert(type(value)=='number' and value==math.floor(value) and value>=0 and value<=255)
  end
  if kind=='SELECT' then selected=value end
  if kind=='DATA' and selected~=nil then
    if selected%8==6 then r6=value end
    if selected%8==7 then r7=value end
  end
  if count>=MAX then dropped=dropped+1;return end
  count=count+1
  local b=bank(addr)
  assert(output:write(table.concat({tostring(emu.framecount()),tostring(count),
    kind,string.format('%04X',addr),value and string.format('%02X',value) or 'unknown',
    b and tostring(b) or 'unknown'},'\t')..'\n'))
end
for _,pc in ipairs({0xE479,0xE4E6,0xE4F3,0x835B,0xC906}) do
  local p=pc
  memory.registerexec(p,function() log('EXEC',p,nil) end)
end
memory.registerread(0x8000,0x8000,function(a,size,v)
  if size~=1 or v~=0 then
    callback_errors=callback_errors+1
    error('Unsupported FCEUX READ zero-sentinel callback')
  end
  log('READ',a,nil)
end)
memory.registerwrite(0x8000,0x2000,function(a,size,v)
  assert(type(a)=='number' and a==math.floor(a) and a>=0x8000 and a<=0x9FFF
    and size==1, 'Invalid mirrored MMC3 callback')
  log(a%2==0 and 'SELECT' or 'DATA',a,v)
end)
emu.registerexit(function()
  assert(output:close())
  local m=assert(io.open(DIR..'/stage49_joint.meta.txt','wb'))
  assert(m:write(table.concat({
    'format=vice_stage49_joint_v1',
    'events_recorded='..count,
    'events_dropped='..dropped,
    'complete='..(dropped==0 and callback_errors==0 and 'yes' or 'no'),
    'callback_errors='..callback_errors,
    'exec_context=selected_pc_hooks_only',
    'mmc3_write_coverage=full_8000_9fff_even_odd',
    'read_causality=not_proven',
    'read_value_provenance=address_only_fceux_zero_sentinel'
  },'\n')..'\n'))
  assert(m:close())
end)
