rom={
 readbyteunsigned=function(i)
   local header={[0]=0x4e,[1]=0x45,[2]=0x53,[3]=0x1a,
     [4]=8,[5]=16,[6]=0x40,[7]=0}
   return header[i] or 0
 end
}
-- End-to-end synthetic regression for documented FCEUX memory.getregister API.
-- This test intentionally exposes no emu.getregister implementation.
local dir=os.tmpname();os.remove(dir)
assert(os.execute('mkdir -p "'..dir..'"'))
local regs={a=0x11,x=0x22,y=0x33,s=0x44,p=0x55}
local getter_calls={}
local function getregister(name)
  assert(type(name)=='string' and name==name:lower())
  assert(regs[name]~=nil,'unexpected CPU register name')
  getter_calls[name]=(getter_calls[name] or 0)+1
  return regs[name]
end
local function read_rows(filename)
  local file=assert(io.open(filename,'rb'))
  local rows={}
  for line in file:lines() do rows[#rows+1]=line end
  file:close()
  return rows
end
local function cleanup(filename,meta)
  os.remove(dir..'/'..filename)
  os.remove(dir..'/'..meta)
end

-- Stage52: all registers known => sampled, not partial_unknown.
VPD_CPU_CONTEXT_DIRECTORY=dir
VPD_CPU_CONTEXT_MAX_EVENTS=4
local exec52,exit52={},nil
memory={
 registerexec=function(a,fn)exec52[a]=fn end,
 getregister=getregister
}
emu={
 framecount=function()return 20 end,
 registerexit=function(fn)exit52=fn end
}
dofile('tools/capture_fceux_cpu_context.lua')
exec52[0x835B]()
exit52()
local rows=read_rows(dir..'/stage52_cpu_context.tsv')
assert(#rows==2)
assert(rows[2]=='20\t1\t835B\t11\t22\t33\t44\t55\tsampled')
cleanup('stage52_cpu_context.tsv','stage52_cpu_context.meta.txt')

-- Stage53: same documented getter with mapper select and PRG read callbacks.
VPD_STAGE53_DIRECTORY=dir
VPD_STAGE53_MAX_EVENTS=4
local exec53,writes53,read53={}, {},nil
local exit53
memory={
 registerexec=function(a,fn)exec53[a]=fn end,
 registerread=function(a,size,fn)
   assert(a==0x8000 and size==0x8000)
   read53=fn
 end,
 registerwrite=function(a,size,fn)
   assert(a==0x8000 and size==0x2000)
   writes53[0x8000]=fn;writes53[0x8001]=fn
 end,
 getregister=getregister
}
emu={
 framecount=function()return 21 end,
 registerexit=function(fn)exit53=fn end
}
dofile('tools/capture_fceux_joint_cpu_context.lua')
writes53[0x8000](0x8002,1,0x06)
writes53[0x8001](0x8003,1,0x0C)
exec53[0x835B](0x835B,1,0)
read53(0x835C,1,0)
exit53()
rows=read_rows(dir..'/stage53_joint_context.tsv')
assert(#rows==5)
assert(rows[4]=='21\t3\tEXEC\t835B\tunknown\t12\t11\t22\t33\t44\t55')
assert(rows[5]=='21\t4\tREAD\t835C\tunknown\t12\t11\t22\t33\t44\t55')
for name,_ in pairs(regs) do
  assert(getter_calls[name]==5,'expected one stage52 and four stage53 samples')
end
cleanup('stage53_joint_context.tsv','stage53_joint_context.meta.txt')
assert(os.execute('rmdir "'..dir..'"'))
print('FCEUX memory.getregister complete-context stage52+53 mocks passed')
