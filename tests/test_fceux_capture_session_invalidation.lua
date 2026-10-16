-- Stage76: every collector invalidates successful metadata from an old session
-- before its new TSV is written, then finalizes metadata on registerexit.
-- No original ROM, actual FCEUX run, or source art is required.
local dir=os.tmpname()
os.remove(dir)
assert(os.execute('mkdir -p "'..dir..'"'))
local md5=string.rep('a',32)
local header={[0]=0x4E,[1]=0x45,[2]=0x53,[3]=0x1A,
              [4]=8,[5]=16,[6]=0x40,[7]=0}
rom={
  gethash=function(alg)assert(alg=='md5');return md5 end,
  readbyteunsigned=function(i)return header[i] or 0 end,
}
local exit_hook
memory={
  registerexec=function(addr,fn)assert(type(fn)=='function') end,
  registerread=function(addr,n_or_fn,fn)
    assert(type(fn or n_or_fn)=='function')
  end,
  registerwrite=function(addr,n_or_fn,fn)
    assert(type(fn or n_or_fn)=='function')
  end,
  readbyte=function()return 0 end,
  getregister=function()return 0 end,
}
emu={
  framecount=function()return 1 end,
  registerexit=function(fn) assert(exit_hook==nil);exit_hook=fn end,
}
local function write(path,content)
  local f=assert(io.open(path,'wb'))
  assert(f:write(content))
  assert(f:close())
end
local function read(path)
  local f=assert(io.open(path,'rb'))
  local content=f:read('*a')
  assert(f:close())
  return content
end
local sessions={
  {'tools/capture_fceux_dispatch.lua','VPD_TRACE_DIRECTORY','stage38_dispatch_exec'},
  {'tools/capture_fceux_pointer_access.lua','VPD_POINTER_DIRECTORY','stage41_pointer_access'},
  {'tools/capture_fceux_prg_reads.lua','VPD_PRG_DIRECTORY','stage45_prg_reads'},
  {'tools/capture_fceux_joint_exec_reads.lua','VPD_JOINT_DIRECTORY','stage49_joint'},
  {'tools/capture_fceux_cpu_context.lua','VPD_CPU_CONTEXT_DIRECTORY','stage52_cpu_context'},
  {'tools/capture_fceux_joint_cpu_context.lua','VPD_STAGE53_DIRECTORY','stage53_joint_context'},
}
for _,entry in ipairs(sessions) do
  local script,variable,basename=entry[1],entry[2],entry[3]
  _G[variable]=dir
  exit_hook=nil
  local metadata=dir..'/'..basename..'.meta.txt'
  local trace=dir..'/'..basename..'.tsv'
  write(metadata,'format=stale\ncomplete=yes\nevents_recorded=1\n')
  write(trace,'old-session-tsv\n')
  dofile(script)
  assert(type(exit_hook)=='function',script..' did not register exit hook')
  assert(read(metadata)=='capture_in_progress=yes\n',
         script..' left old complete metadata during capture')
  assert(read(trace):find('old-session-tsv',1,true)==nil,
         script..' did not replace previous trace')
  -- No callbacks are fired: a valid exit must replace the pending marker.
  exit_hook()
  local finished=read(metadata)
  assert(finished:find('complete=yes',1,true) or
         finished:find('trace_complete=yes',1,true),
         script..' did not finalize metadata')
  assert(not finished:find('capture_in_progress=yes',1,true),
         script..' did not clear the pending marker')
  os.remove(trace)
  os.remove(metadata)
end
-- A failed preflight occurs before stage53 starts: old files must be intact.
VPD_STAGE53_DIRECTORY=dir
VPD_STAGE53_EXPECTED_ROM_MD5=string.rep('b',32)
local trace=dir..'/stage53_joint_context.tsv'
local metadata=dir..'/stage53_joint_context.meta.txt'
write(trace,'previous-validated-trace\n')
write(metadata,'previous-validated-metadata\n')
exit_hook=nil
local ok,err=pcall(dofile,'tools/capture_fceux_joint_cpu_context.lua')
assert(not ok and tostring(err):find('MD5',1,true))
assert(exit_hook==nil)
assert(read(trace)=='previous-validated-trace\n')
assert(read(metadata)=='previous-validated-metadata\n')
VPD_STAGE53_EXPECTED_ROM_MD5=nil
os.remove(trace)
os.remove(metadata)
assert(os.execute('rmdir "'..dir..'"'))
print('Stage76 FCEUX stale metadata invalidation: six collectors PASS')
