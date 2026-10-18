-- Stage85: exercise the exact production event callback under a mocked clock.
-- No ROM, real graphics, or FCEUX emulator is required.
local source=assert(io.open('tools/capture_fceux_ppu.lua','rb'))
local body=assert(source:read('*a'))
assert(source:close())
local start=assert(body:find('local function record_event(',1,true))
local finish=assert(body:find('\nlocal function on_write(',start,true))
local snippet=body:sub(start,finish-1):gsub('^local function record_event','function record_event',1)
local function simulate(events,clock)
  local current_frame,current_cycle
  local context={
    writes_this_frame=0,total_writes=0,dropped_writes=0,
    MAX_EVENTS_PER_FRAME=12000,MAX_TOTAL_EVENTS=250000,
    buffered={},timed_buffered={},clock_available=clock,
    previous_cycle=nil,previous_cycle_frame=nil,
    cycle_regressions=0,cycle_equal_adjacent=0,
    cycle_regressions_same_frame=0,cycle_regressions_between_frames=0,
    checked=function(ok,reason)assert(ok,reason)end,
    emu={framecount=function()return current_frame end},
    debugger={getcyclescount=function()return current_cycle end},
  }
  setmetatable(context,{__index=_G})
  assert(load(snippet,'production-record-event','t',context))()
  assert(type(context.record_event)=='function')
  for _,event in ipairs(events) do
    current_frame,current_cycle=event[1],event[2]
    context.record_event(0x8002,0x80,'W')
  end
  assert(#context.buffered==#events)
  assert(#context.timed_buffered==(clock and #events or 0))
  assert(context.total_writes==#events)
  return context
end
local function verify(events,within,between,equal)
  local c=simulate(events,true)
  assert(c.cycle_regressions_same_frame==within)
  assert(c.cycle_regressions_between_frames==between)
  assert(c.cycle_regressions==within+between)
  assert(c.cycle_equal_adjacent==equal)
end
verify({{1,10},{1,20},{2,30}},0,0,0)
verify({{1,10},{1,10},{2,30}},0,0,1)
verify({{1,10},{1,5},{2,30}},1,0,0)
verify({{1,10},{2,5},{2,7}},0,1,0)
verify({{1,10},{1,5},{2,3},{2,3}},1,1,1)
local without_clock=simulate({{1,10},{2,1}},false)
assert(without_clock.cycle_regressions==0)
assert(without_clock.cycle_equal_adjacent==0)
print('Stage85 production callback cycle-order accounting: six scenarios PASS')
