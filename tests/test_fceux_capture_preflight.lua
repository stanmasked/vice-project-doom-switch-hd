-- Stage68 end-to-end: invalid ROM cannot start recording stage53 events.
local dir=os.tmpname();os.remove(dir)
assert(os.execute('mkdir -p "'..dir..'"'))
VPD_STAGE53_DIRECTORY=dir
VPD_STAGE53_MAX_EVENTS=4
local header={[0]=0x4E,[1]=0x45,[2]=0x53,[3]=0x1A,
              [4]=8,[5]=8,[6]=0x40,[7]=0}
local md5=string.rep('e',32)
rom={readbyteunsigned=function(i)return header[i] or 0 end,
     gethash=function(t)assert(t=='md5');return md5 end}
local hooks={},nil
local exit_callback=nil
memory={registerexec=function(a,fn)hooks[a]=fn end,
 registerread=function()end,registerwrite=function()end,
 getregister=function(n)return ({a=1,x=2,y=3,s=4,p=5})[n] end}
emu={framecount=function()return 1 end,
 registerexit=function(fn)exit_callback=fn end}
local function fail_no_capture(label)
 local ok=pcall(dofile,'tools/capture_fceux_joint_cpu_context.lua')
 assert(not ok,label..' should reject the session')
 local f=io.open(dir..'/stage53_joint_context.tsv','rb')
 if f then f:close();error(label..' unexpectedly created a trace') end
 assert(exit_callback==nil,label..' registered the exit hook')
end
header[6]=0x00
fail_no_capture('wrong mapper')
header[6]=0x40
VPD_STAGE53_EXPECTED_ROM_MD5=string.rep('f',32)
fail_no_capture('mismatched private hash')
VPD_STAGE53_EXPECTED_ROM_MD5=md5
assert(dofile('tools/capture_fceux_joint_cpu_context.lua')==nil)
assert(type(hooks[0x835B])=='function')
hooks[0x835B](0x835B,1,0)
exit_callback()
local f=assert(io.open(dir..'/stage53_joint_context.meta.txt','rb'))
local meta=f:read('*a');f:close()
assert(meta:find('rom_header_profile=ines_mapper4_prg128k',1,true))
assert(meta:find('rom_md5_pin=matched',1,true))
assert(meta:find('complete=yes',1,true))
os.remove(dir..'/stage53_joint_context.tsv')
os.remove(dir..'/stage53_joint_context.meta.txt')
assert(os.execute('rmdir "'..dir..'"'))
print('Stage68 ROM pin gate starts recording only after passing preflight')
