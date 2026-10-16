-- Stage53: single-session sparse CPU register samples + PRG reads + MMC3 writes.
-- Observation order is not instruction/read causality.
local DIR=rawget(_G,'VPD_STAGE53_DIRECTORY') or 'private'
local MAX=rawget(_G,'VPD_STAGE53_MAX_EVENTS') or 20000
assert(type(MAX)=='number' and MAX==math.floor(MAX) and MAX>=1 and MAX<=500000)
assert(memory and memory.registerexec and memory.registerread and memory.registerwrite)
assert(emu and emu.framecount and emu.registerexit)
local file=assert(io.open(DIR..'/stage53_joint_context.tsv','wb'))
assert(file:write('frame\tseq\tkind\taddress\tvalue\tbank\ta\tx\ty\ts\tp\n'))
local selected,r6,r7=nil,nil,nil
local count,dropped=0,0
local function register(name)
  if type(emu.getregister)~='function' then return 'unknown' end
  local ok,v=pcall(emu.getregister,name)
  if not ok or type(v)~='number' or v~=math.floor(v) or v<0 or v>255 then return 'unknown' end
  return string.format('%02X',v)
end
local function bank(addr)
  if addr>=0xE000 then return 15 end
  if selected==nil then return nil end
  local mode=math.floor(selected/64)%2
  if addr>=0xC000 then return mode==0 and 14 or (r6 and r6%16 or nil) end
  if addr>=0xA000 then return r7 and r7%16 or nil end
  if addr>=0x8000 then return mode==1 and 14 or (r6 and r6%16 or nil) end
  return nil
end
local function record(kind,addr,val)
  assert(type(addr)=='number' and addr==math.floor(addr) and addr>=0x8000 and addr<=0xFFFF)
  if val~=nil then assert(type(val)=='number' and val==math.floor(val) and val>=0 and val<=255) end
  if kind=='SELECT' then selected=val
  elseif kind=='DATA' and selected~=nil then
    if selected%8==6 then r6=val end
    if selected%8==7 then r7=val end
  end
  if count>=MAX then dropped=dropped+1;return end
  count=count+1
  local b=bank(addr)
  local regs={register('A'),register('X'),register('Y'),register('S'),register('P')}
  assert(file:write(table.concat({tostring(emu.framecount()),tostring(count),kind,
    string.format('%04X',addr),val and string.format('%02X',val) or 'unknown',
    b and tostring(b) or 'unknown',regs[1],regs[2],regs[3],regs[4],regs[5]},'\t')..'\n'))
end
for _,pc in ipairs({0xE479,0xE4E6,0xE4F3,0x835B,0xC906}) do
  local address=pc
  memory.registerexec(address,function()record('EXEC',address,nil)end)
end
memory.registerread(0x8000,0x8000,function(addr,size,value)record('READ',addr,value)end)
memory.registerwrite(0x8000,function(a,size,v)record('SELECT',0x8000,v)end)
memory.registerwrite(0x8001,function(a,size,v)record('DATA',0x8001,v)end)
emu.registerexit(function()
  assert(file:close())
  local m=assert(io.open(DIR..'/stage53_joint_context.meta.txt','wb'))
  assert(m:write(table.concat({
    'format=vice_stage53_joint_context_v1',
    'events_recorded='..count,'events_dropped='..dropped,
    'complete='..(dropped==0 and 'yes' or 'no'),
    'initial_mmc3_mode=unknown',
    'register_provenance=callback_time_optional_samples',
    'effective_address=not_proven',
    'read_causality=not_proven'
  },'\n')..'\n'))
  assert(m:close())
end)
