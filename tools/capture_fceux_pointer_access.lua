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
local file=assert(io.open(DIR..'/stage41_pointer_access.tsv','wb'))
assert(file:write('frame\tseq\tkind\taddress\tvalue\taa\tab\ta8\ta9\n'))
local seq,count,dropped=0,0,0
local function bytehex(v)
  assert(type(v)=='number' and v>=0 and v<=255 and v==math.floor(v),
         'Callback did not expose a byte')
  return string.format('%02X',v)
end
local function record(kind,addr,value)
  seq=seq+1
  if count>=MAX then dropped=dropped+1;return end
  local row={tostring(emu.framecount()),tostring(seq),kind,
             string.format('%04X',addr),bytehex(value)}
  for _,p in ipairs({0xAA,0xAB,0xA8,0xA9}) do
    row[#row+1]=bytehex(memory.readbyte(p))
  end
  assert(file:write(table.concat(row,'\t')..'\n'))
  count=count+1
end
for _,p in ipairs({0xAA,0xAB,0xA8,0xA9}) do
  local address=p
  memory.registerread(address,function(a,size,value)
    -- API callback byte may be unavailable; reject instead of fabricating reads.
    record('READ',address,value)
  end)
  memory.registerwrite(address,function(a,size,value)
    record('WRITE',address,value)
  end)
end
emu.registerexit(function()
  assert(file:close())
  local out=assert(io.open(DIR..'/stage41_pointer_access.meta.txt','wb'))
  assert(out:write(table.concat({
    'format=vice_stage41_pointer_access_v1','rom_md5='..hash,
    'events_recorded='..count,'events_dropped='..dropped,
    'complete='..(dropped==0 and 'yes' or 'no'),
    'execution_pc=not_instrumented',
    'meaning=pointer_byte_access_not_dereference'
  },'\n')..'\n'))
  assert(out:close())
end)
