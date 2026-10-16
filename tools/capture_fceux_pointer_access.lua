-- Stage 41: OPTIONAL, separate pointer-read probe. No original assets in Git.
-- Run separately from stage38 until concurrent callback interaction is tested.
-- Reading pointer bytes does not prove dereference or reveal an effective address.
local DIR=rawget(_G,'VPD_POINTER_DIRECTORY') or 'private'
local MAX=rawget(_G,'VPD_POINTER_MAX_EVENTS') or 20000
assert(type(MAX)=='number' and MAX==math.floor(MAX) and MAX>=1 and MAX<=500000)
assert(type(memory)=='table' and type(memory.registerread)=='function' and
       type(memory.registerwrite)=='function' and type(memory.readbyte)=='function',
       'FCEUX memory read/write hooks required')
assert(type(emu)=='table' and type(emu.framecount)=='function' and
       type(emu.registerexit)=='function','FCEUX emu hooks required')
local hash=rom.gethash('md5')
assert(type(hash)=='string' and hash:match('^[0-9a-fA-F]+$') and #hash==32,
       'Expected 32-digit ROM MD5')
-- Invalidate metadata from an earlier session BEFORE replacing its TSV.
-- A crash or callback exception must never reuse an old complete=yes.
local meta_path=DIR..'/stage41_pointer_access.meta.txt'
local pending=assert(io.open(meta_path,'wb'))
assert(pending:write('capture_in_progress=yes\\n'))
assert(pending:close())
local file=assert(io.open(DIR..'/stage41_pointer_access.tsv','wb'))
assert(file:write('frame\tseq\tkind\taddress\tvalue\taa\tab\ta8\ta9\n'))
local seq,count,dropped,callback_errors=0,0,0,0
local sampling=false
local function bytehex(v)
  assert(type(v)=='number' and v>=0 and v<=255 and v==math.floor(v),
         'Callback did not expose a byte')
  return string.format('%02X',v)
end
local function record(kind,addr,value)
  if sampling then return end
  seq=seq+1
  if count>=MAX then dropped=dropped+1;return end
  sampling=true
  local row={tostring(emu.framecount()),tostring(seq),kind,
             string.format('%04X',addr),value==nil and 'unknown' or bytehex(value)}
  for _,p in ipairs({0xAA,0xAB,0xA8,0xA9}) do
    row[#row+1]=bytehex(memory.readbyte(p))
  end
  assert(file:write(table.concat(row,'\t')..'\n'))
  count=count+1
  sampling=false
end
for _,p in ipairs({0xAA,0xAB,0xA8,0xA9}) do
  local address=p
  memory.registerread(address,function(a,size,value)
    if a~=address or size~=1 or value~=0 then
      callback_errors=callback_errors+1
      error('Unsupported FCEUX READ zero-sentinel callback')
    end
    record('READ',address,nil)
  end)
  memory.registerwrite(address,function(a,size,value)
    if a~=address or size~=1 or type(value)~='number' or
       value~=math.floor(value) or value<0 or value>255 then
      callback_errors=callback_errors+1
      error('Invalid FCEUX RAM write callback')
    end
    record('WRITE',address,value)
  end)
end
emu.registerexit(function()
  assert(file:close())
  local out=assert(io.open(meta_path,'wb'))
  assert(out:write(table.concat({
    'format=vice_stage41_pointer_access_v1','rom_md5='..hash,
    'events_recorded='..count,'events_dropped='..dropped,
    'complete='..(dropped==0 and callback_errors==0 and 'yes' or 'no'),
    'callback_errors='..callback_errors,
    'read_value_provenance=address_only_fceux_zero_sentinel',
    'execution_pc=not_instrumented',
    'meaning=pointer_byte_access_not_dereference'
  },'\n')..'\n'))
  assert(out:close())
end)
