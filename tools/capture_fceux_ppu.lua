-- FCEUX 2.3+ Lua: capture original-game PPU/RAM strictly to private local files.
-- Run with the owner's own ROM; do not commit generated captures or log.
-- Documented APIs: ppu.readbyterange, memory.readbyterange/registerwrite,
-- emu.framecount/registerafter/registerexit, rom.gethash.
local OUTPUT_DIRECTORY = rawget(_G, 'VPD_CAPTURE_DIRECTORY') or 'private'
local FRAME_INTERVAL = 120
local MAX_CAPTURES = 24
local MAX_EVENTS_PER_FRAME = 12000
local MAX_TOTAL_EVENTS = 250000

local frames_captured = 0
local last_frame = -1
local writes_this_frame, total_writes = 0, 0
local dropped_writes = 0
local buffered = {}
local chr_reg = {}
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

local function on_write(address, size, value)
    if address == 0x2000 then ppuctrl = value end
    if address == 0x2001 then ppumask = value end
    if address == 0x8000 then mmc3_select = value end
    if address == 0x8001 and mmc3_select ~= nil then
        local register = mmc3_select % 8
        if register <= 5 then chr_reg[register] = value end
    end
    if writes_this_frame < MAX_EVENTS_PER_FRAME and total_writes < MAX_TOTAL_EVENTS then
        buffered[#buffered+1] = string.format('%d\t%04X\t%02X\n',
                                              emu.framecount(), address, value)
        writes_this_frame = writes_this_frame + 1
        total_writes = total_writes + 1
    else
        dropped_writes = dropped_writes + 1
    end
end

for _, addr in ipairs({0x2000,0x2001,0x2005,0x2006,0x2007,
                       0x8000,0x8001,0xA000,0xC000,0xC001,0xE000,0xE001}) do
    memory.registerwrite(addr, on_write)
end

local function flush()
    if #buffered > 0 then
        assert(log:write(table.concat(buffered)), 'Failed writing register log')
        assert(log:flush(), 'Failed flushing register log')
        buffered = {}
    end
    writes_this_frame = 0
end

local function capture_metadata(frame)
    local result = {
        'format=fceux_ppu_snapshot_v2',
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
    write_binary(prefix..'.meta.txt', capture_metadata(frame))
    frames_captured = frames_captured + 1
    emu.message('Private PPU/RAM capture '..frames_captured..'/'..MAX_CAPTURES)
end

emu.registerafter(capture_frame)
emu.registerexit(function() flush(); log:close() end)
