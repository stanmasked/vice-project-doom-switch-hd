-- FCEUX 2.3+ Lua: capture original-game PPU/RAM strictly to private local files.
-- Run with the owner's own ROM; do not commit generated captures or log.
-- Documented APIs: ppu.readbyterange, memory.readbyterange/registerwrite,
-- emu.framecount/registerafter/registerexit, rom.gethash.
local OUTPUT_DIRECTORY = rawget(_G, 'VPD_CAPTURE_DIRECTORY') or 'private'
-- Default remains backwards-compatible; use smaller intervals for
-- overlapping first-stage samples, without changing the script on disk.
local function bounded_integer(global_name, fallback, limit)
    local value = rawget(_G, global_name)
    if value == nil then return fallback end
    assert(type(value)=='number' and value==math.floor(value)
           and value>=1 and value<=limit,
           global_name..' must be an integer from 1 to '..limit)
    return value
end
local FRAME_INTERVAL = bounded_integer('VPD_CAPTURE_INTERVAL',120,1200)
local MAX_CAPTURES = bounded_integer('VPD_CAPTURE_LIMIT',24,512)
-- Default-on renderer reference. Disable by setting VPD_CAPTURE_SCREEN=false.
local CAPTURE_SCREEN = rawget(_G, 'VPD_CAPTURE_SCREEN') ~= false
local MAX_EVENTS_PER_FRAME = 12000
local MAX_TOTAL_EVENTS = 250000

local frames_captured = 0
local last_frame = -1
local writes_this_frame, total_writes = 0, 0
local dropped_writes = 0
local buffered = {}
local timed_buffered = {}
local clock_available = type(debugger)=='table' and type(debugger.getcyclescount)=='function'
local chr_reg = {}
local invalid_screen_palette_values = 0
local mmc3_select, ppuctrl, ppumask = nil, nil, nil

local function hx(value)
    if value == nil then return 'unknown' end
    return string.format('%02X', value)
end
local function write_binary(path, value)
    local f, error_message = io.open(path, 'wb')
    assert(f, 'Cannot write '..path..': '..tostring(error_message))
    assert(f:write(value), 'Failed writing '..path)
    f:close()
end

local log_path = OUTPUT_DIRECTORY..'/mmc3_video_writes.tsv'
local log, open_error = io.open(log_path, 'wb')
assert(log, 'Create a writable private capture directory: '..log_path..' ('..tostring(open_error)..')')
assert(log:write('frame\taddress\tvalue\n'))
-- Separate backwards-compatible subframe trace. Timestamps are CPU cycles,
-- not PPU scanlines: cycle-counter reset can change their epoch.
local timed_log = nil
if clock_available then
    local path = OUTPUT_DIRECTORY..'/mmc3_ppu_cycles.tsv'
    timed_log = assert(io.open(path,'wb'))
    assert(timed_log:write('frame\tcpu_cycle\taddress\tvalue\tkind\n'))
end

local function record_event(address, value, kind)
    kind = kind or 'W'
    if writes_this_frame < MAX_EVENTS_PER_FRAME and total_writes < MAX_TOTAL_EVENTS then
        local frame = emu.framecount()
        buffered[#buffered+1] = string.format('%d\t%04X\t%02X\n',
                                              frame, address, value)
        if clock_available then
            local cycles = debugger.getcyclescount()
            assert(type(cycles)=='number' and cycles>=0 and cycles==math.floor(cycles),
                   'Invalid debugger CPU cycle counter')
            timed_buffered[#timed_buffered+1] = string.format('%.0f\t%.0f\t%04X\t%02X\t%s\n',
                                                frame, cycles, address, value, kind)
        end
        writes_this_frame = writes_this_frame + 1
        total_writes = total_writes + 1
    else
        dropped_writes = dropped_writes + 1
    end
end

local function on_write(address, size, value)
    if address == 0x2000 then ppuctrl = value end
    if address == 0x2001 then ppumask = value end
    if address == 0x8000 then mmc3_select = value end
    if address == 0x8001 and mmc3_select ~= nil then
        local register = mmc3_select % 8
        if register <= 5 then chr_reg[register] = value end
    end
    record_event(address, value)
end

local function on_status_read(address, size, value)
    -- One synthetic address 2002/value 00 marker represents a real
    -- PPUSTATUS read. The PPU $2005/$2006 shared toggle resets on this read.
    -- This is not a PPUSTATUS write.
    record_event(0x2002, 0, 'R')
end

for _, addr in ipairs({0x2000,0x2001,0x2005,0x2006,0x2007,
                       0x8000,0x8001,0xA000,0xC000,0xC001,0xE000,0xE001}) do
    memory.registerwrite(addr, on_write)
end
-- Reads of $2002 reset the $2005/$2006 shared PPU write latch.
-- Capture these as address=2002/value=00 markers in the event TSV.
memory.registerread(0x2002, on_status_read)

local function flush()
    if #buffered > 0 then
        assert(log:write(table.concat(buffered)), 'Failed writing register log')
        assert(log:flush(), 'Failed flushing register log')
        buffered = {}
        if timed_log then
            assert(timed_log:write(table.concat(timed_buffered)), 'Failed cycle log write')
            assert(timed_log:flush(), 'Failed cycle log flush')
            timed_buffered = {}
        end
    end
    writes_this_frame = 0
end

local function capture_metadata(frame)
    local result = {
        'format=fceux_ppu_snapshot_v4',
        'cycle_trace_available='..(clock_available and 'yes' or 'no'),
        'cycle_trace_counter_epoch=debugger_since_reset',
        'screen_reference='..(CAPTURE_SCREEN and 'yes' or 'no'),
        'screen_size=256x240',
        'capture_interval='..tostring(FRAME_INTERVAL),
        'capture_limit='..tostring(MAX_CAPTURES),
        'invalid_screen_palette_values='..tostring(invalid_screen_palette_values),
        'frame='..tostring(frame),
        'rom_md5='..tostring(rom.gethash('md5')),
        'ppuctrl='..hx(ppuctrl),
        'ppumask='..hx(ppumask),
        'mmc3_select='..hx(mmc3_select),
        'logged_register_writes='..tostring(total_writes),
        'dropped_register_writes='..tostring(dropped_writes),
        'register_log_complete='..(dropped_writes == 0 and 'yes' or 'no'),
        'queue_index_16='..hx(memory.readbyte(0x16)),
    }
    for r=0,5 do
        result[#result+1] = 'chr_r'..r..'='..hx(chr_reg[r])
        result[#result+1] = 'chr_ram_'..r..'='..hx(memory.readbyte(0x3D+r))
    end
    return table.concat(result, '\n')..'\n'
end

local function capture_rendered_screen(prefix)
    -- The fourth result from emu.getscreenpixel is the NES palette
    -- index (0-63) or FCEUX's unavailable sentinel (254).
    if not CAPTURE_SCREEN then return end
    assert(type(emu.getscreenpixel) == 'function',
           'FCEUX emu.getscreenpixel required for reference capture')
    local rgb_rows, pal_rows = {}, {}
    invalid_screen_palette_values = 0
    for y=0,239 do
        local rgb_row, pal_row = {}, {}
        for x=0,255 do
            local r,g,b,pal = emu.getscreenpixel(x,y,true)
            assert(type(r)=='number' and type(g)=='number' and
                   type(b)=='number' and type(pal)=='number',
                   'Invalid emu.getscreenpixel return')
            assert(r>=0 and r<=255 and g>=0 and g<=255 and b>=0 and b<=255,
                   'Invalid emulated RGB component')
            assert((pal>=0 and pal<=63) or pal==254,
                   'Invalid NES palette value from FCEUX')
            if pal==254 then
                invalid_screen_palette_values=invalid_screen_palette_values+1
            end
            rgb_row[#rgb_row+1]=string.char(r,g,b)
            pal_row[#pal_row+1]=string.char(pal)
        end
        rgb_rows[#rgb_rows+1]=table.concat(rgb_row)
        pal_rows[#pal_rows+1]=table.concat(pal_row)
    end
    write_binary(prefix..'.screen.rgb.bin',table.concat(rgb_rows))
    write_binary(prefix..'.screen.pal.bin',table.concat(pal_rows))
end

local function capture_frame()
    local frame = emu.framecount()
    if frame == last_frame then return end
    last_frame = frame
    -- Flush every frame: bound memory use during graphics-heavy scenes.
    flush()
    if frames_captured >= MAX_CAPTURES or frame % FRAME_INTERVAL ~= 0 then return end

    local ppu_bytes = ppu.readbyterange(0, 0x4000)
    local ram_bytes = memory.readbyterange(0, 0x0800)
    assert(type(ppu_bytes) == 'string' and #ppu_bytes == 0x4000,
           'FCEUX ppu.readbyterange must return a 16384-byte string')
    assert(type(ram_bytes) == 'string' and #ram_bytes == 0x0800,
           'FCEUX memory.readbyterange must return a 2048-byte string')
    local prefix = OUTPUT_DIRECTORY..'/frame_'..string.format('%06d', frame)
    write_binary(prefix..'.ppu.bin', ppu_bytes)
    write_binary(prefix..'.ram.bin', ram_bytes)
    capture_rendered_screen(prefix)
    write_binary(prefix..'.meta.txt', capture_metadata(frame))
    frames_captured = frames_captured + 1
    emu.message('Private PPU/RAM capture '..frames_captured..'/'..MAX_CAPTURES)
end

emu.registerafter(capture_frame)
emu.registerexit(function() flush(); log:close(); if timed_log then timed_log:close() end end)
