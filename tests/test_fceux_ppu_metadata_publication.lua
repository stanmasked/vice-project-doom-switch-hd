-- Stage81: execute the REAL production publish_metadata body with injected
-- filesystem failures. ROM-free; no original game or emulator required.
local real_io,real_os=io,os
local source=assert(real_io.open('tools/capture_fceux_ppu.lua','rb'))
local body=assert(source:read('*a'))
assert(source:close())
local start=assert(body:find('local function publish_metadata(',1,true))
local stop=assert(body:find('\n-- Invalidate a prior completed session',start,true))
local code=body:sub(start,stop-1):gsub('^local function publish_metadata','function publish_metadata',1)
local tempdir=os.tmpname()
os.remove(tempdir)
assert(os.execute('mkdir -p "'..tempdir..'"'))
local target=tempdir..'/frame_000001.meta.txt'
local session=tempdir..'/ppu_capture_session.meta.txt'
local pending='capture_in_progress=yes\n'
local final='format=fceux_ppu_snapshot_v4\ncomplete=yes\nsession_id=0011223344556677\n'
local session_final='format=fceux_ppu_session_v1\ncomplete=yes\nsession_id=0011223344556677\n'
local function write(path,bytes)
  local f=assert(real_io.open(path,'wb'))
  assert(f:write(bytes))
  assert(f:close())
end
local function read(path)
  local f=real_io.open(path,'rb')
  if not f then return nil end
  local data=f:read('*a')
  assert(f:close())
  return data
end
local checked=0
local function try_publish(mode,path,payload)
  local proxy_io={
    open=function(filename,permission)
      if filename==path..'.tmp' and permission=='wb' then
        if mode=='open_failure' then return nil,'injected open failure' end
        if mode=='write_failure' or mode=='close_failure' then
          local handle=assert(real_io.open(filename,permission))
          if mode=='write_failure' then
            return {write=function()return nil,'injected write failure' end,
                    close=function()return handle:close() end}
          end
          return {write=function(_,bytes)return handle:write(bytes) end,
                  close=function()
                    assert(handle:close())
                    return nil,'injected close failure'
                  end}
        end
      end
      if filename==path..'.tmp' and permission=='rb' then
        if mode=='readback_failure' then
          local handle=assert(real_io.open(filename,permission))
          return {read=function()return 'tampered bytes' end,
                  close=function()return handle:close() end}
        elseif mode=='readback_close_failure' then
          local handle=assert(real_io.open(filename,permission))
          return {read=function(_,format)return handle:read(format) end,
                  close=function()
                    assert(handle:close())
                    return nil,'injected verification close failure'
                  end}
        end
      end
      return real_io.open(filename,permission)
    end
  }
  local proxy_os={
    remove=function(filename)
      if mode=='remove_failure' and filename==path then
        return nil,'injected remove failure'
      end
      return real_os.remove(filename)
    end,
    rename=function(from,to)
      if mode=='rename_failure' then return nil,'injected rename failure' end
      return real_os.rename(from,to)
    end,
  }
  local environment={io=proxy_io,os=proxy_os}
  setmetatable(environment,{__index=_G})
  local fn=assert(load(code,'stage81-production-publish_metadata','t',environment))
  fn()
  assert(type(environment.publish_metadata)=='function')
  local success,error_message=pcall(environment.publish_metadata,path,payload)
  if mode=='success' then
    assert(success,tostring(error_message))
    assert(read(path)==payload)
  else
    assert(not success,mode..' unexpectedly succeeded')
    if mode=='rename_failure' then
      assert(read(path)==nil,'failed rename left valid-looking metadata')
    elseif mode=='not_pending' then
      assert(read(path)=='complete=yes\n')
    else
      assert(read(path)==pending,mode..' destroyed incomplete marker')
    end
  end
  assert(read(path..'.tmp')==nil,mode..' retained a temporary file')
  checked=checked+1
end

for _,mode in ipairs({'open_failure','write_failure','close_failure',
                       'readback_failure','readback_close_failure',
                       'remove_failure','rename_failure','success'}) do
  write(target,pending)
  try_publish(mode,target,final)
end
write(target,'complete=yes\n')
try_publish('not_pending',target,final)
write(session,pending)
try_publish('success',session,session_final)
assert(real_os.remove(target))
assert(real_os.remove(session))
assert(real_os.execute('rmdir "'..tempdir..'"'))
print('Stage81 production metadata publish: '..checked..' filesystem cases PASS')
