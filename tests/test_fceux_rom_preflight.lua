-- Stage68: ROM-free iNES profile and optional private MD5 pin tests.
local inspect=dofile('tools/fceux_rom_preflight.lua').inspect
local md5=string.rep('a',32)
local h={[0]=0x4e,[1]=0x45,[2]=0x53,[3]=0x1a,
         [4]=8,[5]=8,[6]=0x40,[7]=0}
local hash_calls=0
local api={
 readbyteunsigned=function(i) return h[i] or 0 end,
 gethash=function(kind) assert(kind=='md5');hash_calls=hash_calls+1;return md5 end
}
local function rejects(label, fn)
 local ok,err=pcall(fn)
 assert(not ok, 'Expected rejection: '..label)
 assert(type(err)=='string','Expected error message: '..label)
end
local ok=inspect(nil,api)
assert(ok.profile=='ines_mapper4_prg128k')
assert(ok.prg_bytes==131072 and not ok.trainer)
assert(ok.md5_pin=='not_supplied' and ok.identity_authenticated==false)
assert(hash_calls==0,'MD5 should be read only when independently pinned')
assert(inspect(md5:upper(),api).md5_pin=='matched')
assert(hash_calls==1)
rejects('wrong MD5',function() inspect(string.rep('b',32),api) end)
rejects('bad MD5 syntax',function() inspect('1234',api) end)
h[6]=0x44 -- trainer changes offset but not mapper
assert(inspect(nil,api).trainer)
h[6]=0x00
rejects('wrong mapper',function() inspect(nil,api) end)
h[6]=0x40;h[4]=4
rejects('wrong PRG count',function() inspect(nil,api) end)
h[4]=8;h[7]=8
rejects('NES 2.0',function() inspect(nil,api) end)
h[7]=0;h[0]=0
rejects('bad header',function() inspect(nil,api) end)
h[0]=0x4e;api.readbyteunsigned=function(i) if i==7 then return nil end return h[i] or 0 end
rejects('missing header byte',function() inspect(nil,api) end)
print('Stage68 private-ROM FCEUX preflight synthetic tests passed')
