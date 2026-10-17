-- Stage84: test the exact production rolling-checksum + chunked-read helpers.
-- Standalone Lua 5.3/5.4 test; no FCEUX or original game data needed.
local system_io=io
local source=assert(system_io.open('tools/capture_fceux_ppu.lua','rb'))
local text=assert(source:read('*a'))
assert(source:close())

local function extract(first,last)
    local a=assert(text:find(first,1,true),first)
    local b=assert(text:find(last,a,true),last)
    return text:sub(a,b-1)
end
local helpers=extract('local function adler32_update(bytes,a,b)',
                      '-- Inspect exact bytes on disk')
local readback=extract('local function event_log_checksum(path)',
                       '-- A finalized metadata file')
local opens,reads,max_request=0,0,0
local target
local environment={
    io={open=function(path,mode)
        local f,err=system_io.open(path,mode)
        if not f then return f,err end
        if path==target and mode=='rb' then
            opens=opens+1
            return {
                read=function(_,size)
                    assert(type(size)=='number' and size<=65536,
                           'Unexpected non-streaming event read')
                    reads=reads+1
                    max_request=math.max(max_request,size)
                    return f:read(size)
                end,
                close=function()return f:close()end,
            }
        end
        return f
    end},
}
setmetatable(environment,{__index=_G})
local chunk=helpers..'\n'..readback..
            '\nreturn adler32_update,adler32_state_hex,adler32_hex,event_log_checksum'
local loader=assert(load(chunk,'stage84-production-rolling-functions','t',environment))
local update,hex,checksum,read_checksum=loader()
assert(checksum('hello')=='062C0215')

local name=os.tmpname()
local out=assert(system_io.open(name,'wb'))
local header='frame\taddress\tvalue\n'
assert(out:write(header))
local a,b=update(header,1,0)
local prefix
for i=1,24000 do
    local row=string.format('%d\t8002\t%02X\n',math.floor(i/400),i%256)
    assert(out:write(row))
    a,b=update(row,a,b)
    if i==12000 then prefix=hex(a,b) end
end
assert(out:close())
assert(prefix~=nil and #prefix==8)
local expected=hex(a,b)
assert(read_checksum(name)==expected)
assert(opens==1 and max_request==65536 and reads>1,
       'Expected one streaming pass with multiple 64 KiB reads')

-- A byte-level mutation with the same length changes the final digest.
local f=assert(system_io.open(name,'r+b'))
assert(f:seek('set',100))
local previous=assert(f:read(1))
assert(f:seek('set',100))
assert(f:write(previous=='0' and '1' or '0'))
assert(f:close())
assert(read_checksum(name)~=expected)
assert(opens==2)
assert(os.remove(name))
print('Stage84 production rolling checksum and one-pass TSV readback PASS')
