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
local first_frame = nil
local callback_frames = 0
local callback_gaps = 0
local capture_failures = 0
local captured_frame_list = {}
-- Correlation token only, not a cryptographic signature of original game data.
local session_id = string.format('%08x%08x', os.time()%4294967296,
                                 math.floor(os.clock()*1000000)%4294967296)
local session_path = OUTPUT_DIRECTORY..'/ppu_capture_session.meta.txt'
local writes_this_frame, total_writes = 0, 0
local dropped_writes = 0
local callback_errors = 0
-- Counter discontinuities are not proof of an actual emulator reset.
-- They invalidate continuous-cycle verification of this session.
local previous_cycle, previous_cycle_frame = nil,nil
local cycle_regressions, cycle_equal_adjacent = 0,0
local cycle_regressions_same_frame, cycle_regressions_between_frames = 0,0
local function checked(ok,reason)
    if not ok then
        callback_errors = callback_errors + 1
        error('Unsupported FCEUX video callback contract: '..reason,2)
    end
end
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
    local wrote, write_error = f:write(value)
    if not wrote then
        pcall(function() f:close() end)
        error('Failed writing '..path..': '..tostring(write_error),2)
    end
    local closed, close_error = f:close()
    assert(closed, 'Failed closing '..path..': '..tostring(close_error))
end

-- Adler-32 is used for accidental corruption detection, NOT security.
-- The Python verifier independently recalculates it from each saved blob.
local function adler32_update(bytes,a,b)
    for i=1,#bytes do
        a=(a+string.byte(bytes,i))%65521
        b=(b+a)%65521
    end
    return a,b
end
local function adler32_state_hex(a,b)
    return string.format('%08X',b*65536+a)
end
local function adler32_hex(bytes)
    local a,b=adler32_update(bytes,1,0)
    return adler32_state_hex(a,b)
end

-- Inspect exact bytes on disk before writing the frame's metadata.
-- This also rejects corruption that preserves the file size.
local function write_verified_blob(path,bytes)
    write_binary(path,bytes)
    local file,open_error=io.open(path,'rb')
    assert(file,'Cannot reread snapshot '..path..': '..tostring(open_error))
    local actual=file:read('*a')
    local closed,close_error=file:close()
    assert(closed,'Failed closing snapshot readback '..path..': '..tostring(close_error))
    assert(actual==bytes,'Snapshot readback mismatch '..path)
    return adler32_hex(bytes)
end

-- Readback of flushed event logs. Adler-32 is an accidental-damage
-- detector, never an authenticity or anti-tampering signature.
local function event_log_checksum(path)
    local source,reason=io.open(path,'rb')
    assert(source,'Cannot read event log '..path..': '..tostring(reason))
    -- Read once at shutdown in fixed-size chunks, never at every frame.
    local a,b=1,0
    local seen,last_byte=false,nil
    while true do
        local part=source:read(65536)
        if part==nil then break end
        assert(type(part)=='string' and #part>0,
               'Invalid event log readback '..path)
        a,b=adler32_update(part,a,b)
        last_byte=part:sub(-1)
        seen=true
    end
    local closed,close_error=source:close()
    assert(closed,'Failed closing event-log readback '..path..': '..tostring(close_error))
    assert(seen and last_byte=='\n','Incomplete event log '..path)
    return adler32_state_hex(a,b)
end

-- A finalized metadata file is the publication boundary for private
-- captures. First write/close a sibling temporary file and compare the
-- exact bytes, then replace the pending marker. On systems where renaming
-- over an existing file is unsupported, removing the pending marker
-- before rename is safe: missing metadata is *not* valid evidence.
local function publish_metadata(path, contents)
    local pending='capture_in_progress=yes\n'
    local previous, previous_error=io.open(path,'rb')
    assert(previous,'Missing pending metadata '..path..': '..tostring(previous_error))
    local existing=previous:read('*a')
    assert(previous:close(),'Failed closing pending metadata '..path)
    assert(existing==pending,'Metadata not pending before finalize: '..path)

    local temp=path..'.tmp'
    local out,open_error=io.open(temp,'wb')
    assert(out,'Cannot open metadata temporary file '..temp..': '..tostring(open_error))
    local wrote,write_error=out:write(contents)
    if not wrote then
        pcall(function() out:close() end)
        os.remove(temp)
        error('Metadata temporary write failed: '..tostring(write_error),2)
    end
    local closed,close_error=out:close()
    if not closed then
        os.remove(temp)
        error('Metadata temporary close failed: '..tostring(close_error),2)
    end
    local verify,verify_error=io.open(temp,'rb')
    if not verify then
        os.remove(temp)
        error('Cannot verify metadata temporary file: '..tostring(verify_error),2)
    end
    local actual=verify:read('*a')
    local verify_closed=verify:close()
    if not verify_closed or actual~=contents then
        os.remove(temp)
        error('Metadata readback mismatch or close failure: '..temp,2)
    end
    -- Remove the pending marker *only after* the temporary file has
    -- been independently verified. Failure here leaves a pending or
    -- missing metadata file; either one is rejected by validators.
    local removed,remove_error=os.remove(path)
    if not removed then
        os.remove(temp)
        error('Cannot remove pending metadata: '..tostring(remove_error),2)
    end
    local renamed,rename_error=os.rename(temp,path)
    if not renamed then
        os.remove(temp)
        error('Cannot publish metadata: '..tostring(rename_error),2)
    end
end

-- Invalidate a prior completed session before replacing either event stream.
-- Per-frame metadata must NOT be treated as session-wide completeness.
write_binary(session_path,'capture_in_progress=yes\n')
local log_path = OUTPUT_DIRECTORY..'/mmc3_video_writes.tsv'
local timed_path = OUTPUT_DIRECTORY..'/mmc3_ppu_cycles.tsv'
local log, open_error = io.open(log_path, 'wb')
assert(log, 'Create a writable private capture directory: '..log_path..' ('..tostring(open_error)..')')
local frame_header='frame\taddress\tvalue\n'
local cycle_header='frame\tcpu_cycle\taddress\tvalue\tkind\n'
assert(log:write(frame_header))
local frame_log_a,frame_log_b=adler32_update(frame_header,1,0)
local cycle_log_a,cycle_log_b=nil,nil
-- Separate backwards-compatible subframe trace. Timestamps are CPU cycles,
-- not PPU scanlines: cycle-counter reset can change their epoch.
local timed_log = nil
if clock_available then
    timed_log = assert(io.open(timed_path,'wb'))
    assert(timed_log:write(cycle_header))
    cycle_log_a,cycle_log_b=adler32_update(cycle_header,1,0)
end

local function record_event(address, value, kind)
    kind = kind or 'W'
    if writes_this_frame < MAX_EVENTS_PER_FRAME and total_writes < MAX_TOTAL_EVENTS then
        -- Build both records BEFORE mutating either buffer. If a debugger
        -- callback fails, neither TSV is allowed to gain a partial event.
        local ok_frame,frame=pcall(emu.framecount)
        checked(ok_frame and type(frame)=='number' and frame==frame
            and frame>=0 and frame<=2147483647 and frame==math.floor(frame),
            'invalid frame counter')
        local frame_line=string.format('%d\t%04X\t%02X\n',frame,address,value)
        local timed_line=nil
        if clock_available then
            local ok_cycle,cycles=pcall(debugger.getcyclescount)
            checked(ok_cycle and type(cycles)=='number' and cycles==cycles
                and cycles>=0 and cycles<=9007199254740991
                and cycles==math.floor(cycles),
                'invalid CPU cycle counter')
            timed_line=string.format('%.0f\t%.0f\t%04X\t%02X\t%s\n',
                                     frame,cycles,address,value,kind)
            if previous_cycle~=nil then
                if cycles<previous_cycle then
                    cycle_regressions=cycle_regressions+1
                    if frame==previous_cycle_frame then
                        cycle_regressions_same_frame=cycle_regressions_same_frame+1
                    else
                        cycle_regressions_between_frames=cycle_regressions_between_frames+1
                    end
                elseif cycles==previous_cycle then
                    cycle_equal_adjacent=cycle_equal_adjacent+1
                end
            end
            previous_cycle,previous_cycle_frame=cycles,frame
        end
        buffered[#buffered+1]=frame_line
        if timed_line then timed_buffered[#timed_buffered+1]=timed_line end
        writes_this_frame = writes_this_frame + 1
        total_writes = total_writes + 1
    else
        dropped_writes = dropped_writes + 1
    end
end

local function on_write(address, size, value)
    checked(type(address)=='number' and address==math.floor(address)
        and ((address>=0x8000 and address<=0xFFFF)
             or (address>=0x2000 and address<=0x3FFF))
        and size==1 and type(value)=='number' and value==math.floor(value)
        and value>=0 and value<=255,
        'write address/size/byte')
    if address>=0x2000 and address<=0x3FFF then
        local port=0x2000+(address-0x2000)%8
        if port==0x2000 then ppuctrl=value end
        if port==0x2001 then ppumask=value end
        -- PPUSTATUS ($2002 mirrors) is read-only: do not accidentally
        -- encode a write as a status-read reset in the legacy 3-column log.
        if port==0x2000 or port==0x2001 or port==0x2005
           or port==0x2006 or port==0x2007 then
            record_event(address,value)
        end
        return
    end
    if address>=0x8000 and address<=0x9FFF then
        if address%2==0 then
            mmc3_select = value
        elseif mmc3_select~=nil then
            local register=mmc3_select%8
            if register<=5 then chr_reg[register]=value end
        end
    end
    record_event(address, value)
end

local function on_status_read(address, size, value)
    checked(type(address)=='number' and address==math.floor(address)
        and address>=0x2000 and address<=0x3FFF
        and size==1 and value==0,
        'PPU read address/size/zero sentinel')
    -- Registerread covers all eight mirrored ports, but only PPUSTATUS
    -- reads (offset 2) reset the shared $2005/$2006 write latch.
    -- Preserve the actual CPU address and distinguish READ in cycle logs.
    if (address-0x2000)%8==2 then
        record_event(address,0,'R')
    end
end

-- CPU-visible PPU ports mirror every 8 bytes throughout $2000-$3FFF.
-- Use range hooks and classify by address mod 8, recording original address.
memory.registerwrite(0x2000,0x2000,on_write)
memory.registerread(0x2000,0x2000,on_status_read)
-- MMC3 retains independent mirrored write decoding across $8000-$FFFF.
memory.registerwrite(0x8000,0x8000,on_write)

local function flush()
    checked(not clock_available or #buffered==#timed_buffered,
            'frame/cycle event buffer mismatch')
    if #buffered > 0 then
        local frame_batch=table.concat(buffered)
        local cycle_batch=timed_log and table.concat(timed_buffered) or nil
        assert(log:write(frame_batch), 'Failed writing register log')
        assert(log:flush(), 'Failed flushing register log')
        if timed_log then
            assert(timed_log:write(cycle_batch), 'Failed cycle log write')
            assert(timed_log:flush(), 'Failed cycle log flush')
        end
        -- Advance both rolling checksums only when all writes/flushes
        -- succeeded. Failed sessions remain unverified by the manifest.
        frame_log_a,frame_log_b=adler32_update(frame_batch,frame_log_a,frame_log_b)
        if timed_log then
            cycle_log_a,cycle_log_b=adler32_update(cycle_batch,cycle_log_a,cycle_log_b)
        end
        buffered={}
        timed_buffered={}
    end
    writes_this_frame = 0
end

local function capture_metadata(frame, checksums)
    local result = {
        'format=fceux_ppu_snapshot_v4',
        'session_id='..session_id,
        'session_snapshot_index='..tostring(frames_captured+1),
        'capture_scope=frame_prefix_only',
        'cycle_trace_available='..(clock_available and 'yes' or 'no'),
        'cycle_trace_counter_epoch=debugger_since_reset',
        'screen_reference='..(CAPTURE_SCREEN and 'yes' or 'no'),
        'screen_size=256x240',
        'snapshot_checksum=adler32_v1',
        'event_checksum=adler32_v1',
        'frame_log_prefix_adler32='..checksums.frame_log,
        'cycle_log_prefix_adler32='..checksums.cycle_log,
        'ppu_adler32='..checksums.ppu,
        'ram_adler32='..checksums.ram,
        'screen_rgb_adler32='..(checksums.rgb or 'not_captured'),
        'screen_pal_adler32='..(checksums.pal or 'not_captured'),
        'capture_interval='..tostring(FRAME_INTERVAL),
        'capture_limit='..tostring(MAX_CAPTURES),
        'invalid_screen_palette_values='..tostring(invalid_screen_palette_values),
        'frame='..tostring(frame),
        'rom_md5='..tostring(rom.gethash('md5')),
        'ppuctrl='..hx(ppuctrl),
        'ppumask='..hx(ppumask),
        'mmc3_select='..hx(mmc3_select),
        'logged_register_writes='..tostring(total_writes),
        'callback_errors='..tostring(callback_errors),
        'mmc3_write_coverage=full_8000_ffff_even_odd',
        'ppu_register_write_coverage=full_2000_3fff_mod8',
        'ppu_status_read_coverage=full_2000_3fff_mod8',
        'dropped_register_writes='..tostring(dropped_writes),
        'register_log_complete='..(dropped_writes == 0 and callback_errors == 0 and 'yes' or 'no'),
        'scroll_emitter_ram_0b='..hx(memory.readbyte(0x0B)),
        'scroll_emitter_ram_0c='..hx(memory.readbyte(0x0C)),
        'scroll_emitter_ram_0d='..hx(memory.readbyte(0x0D)),
        'scroll_emitter_provenance=static_emitter_e8de_not_confirmed_runtime',
        'stage36_companion_ram_90='..hx(memory.readbyte(0x90)),
        'stage36_companion_ram_91='..hx(memory.readbyte(0x91)),
        'stage36_companion_ram_93='..hx(memory.readbyte(0x93)),
        'stage36_index_context=static_writer_candidates_not_confirmed_executed',
        'stage35_candidate_index_ram_92='..hx(memory.readbyte(0x92)),
        'stage35_candidate_pointer_ram_aa='..hx(memory.readbyte(0xAA)),
        'stage35_candidate_pointer_ram_ab='..hx(memory.readbyte(0xAB)),
        'stage35_candidate_descriptor_ram_a8='..hx(memory.readbyte(0xA8)),
        'stage35_candidate_descriptor_ram_a9='..hx(memory.readbyte(0xA9)),
        'stage35_pointer_provenance=static_bank12_candidate_not_runtime_proven',
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
    if not CAPTURE_SCREEN then return nil,nil end
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
    local rgb=table.concat(rgb_rows)
    local palette=table.concat(pal_rows)
    local rgb_hash=write_verified_blob(prefix..'.screen.rgb.bin',rgb)
    local pal_hash=write_verified_blob(prefix..'.screen.pal.bin',palette)
    return rgb_hash,pal_hash
end

local function capture_frame()
    local frame = emu.framecount()
    if frame == last_frame then return end
    if last_frame >= 0 and (frame < last_frame or frame > last_frame+1) then
        callback_gaps = callback_gaps + 1
    end
    last_frame = frame
    if first_frame == nil then first_frame = frame end
    callback_frames = callback_frames + 1
    -- Flush every frame: bound memory use during graphics-heavy scenes.
    flush()
    if frames_captured >= MAX_CAPTURES or frame % FRAME_INTERVAL ~= 0 then return end

    -- Invalidate stale frame metadata before updating any image/RAM assets.
    -- If the frame capture fails mid-write, old complete metadata cannot
    -- certify a partial replacement of the same frame_NNNNNN.* files.
    local prefix = OUTPUT_DIRECTORY..'/frame_'..string.format('%06d', frame)
    write_binary(prefix..'.meta.txt','capture_in_progress=yes\n')
    local ppu_bytes = ppu.readbyterange(0, 0x4000)
    local ram_bytes = memory.readbyterange(0, 0x0800)
    assert(type(ppu_bytes) == 'string' and #ppu_bytes == 0x4000,
           'FCEUX ppu.readbyterange must return a 16384-byte string')
    assert(type(ram_bytes) == 'string' and #ram_bytes == 0x0800,
           'FCEUX memory.readbyterange must return a 2048-byte string')
    local checksums={
        ppu=write_verified_blob(prefix..'.ppu.bin',ppu_bytes),
        ram=write_verified_blob(prefix..'.ram.bin',ram_bytes),
        -- Constant work per snapshot: use the checksum of successfully
        -- flushed bytes instead of repeatedly rereading the growing TSV.
        frame_log=adler32_state_hex(frame_log_a,frame_log_b),
        cycle_log=(timed_log and adler32_state_hex(cycle_log_a,cycle_log_b)
                   or 'not_captured'),
    }
    checksums.rgb,checksums.pal=capture_rendered_screen(prefix)
    publish_metadata(prefix..'.meta.txt', capture_metadata(frame,checksums))
    frames_captured = frames_captured + 1
    captured_frame_list[#captured_frame_list+1] = frame
    emu.message('Private PPU/RAM capture '..frames_captured..'/'..MAX_CAPTURES)
end

emu.registerafter(function()
    local ok,reason=pcall(capture_frame)
    if not ok then
        capture_failures=capture_failures+1
        error(reason,2)
    end
end)
emu.registerexit(function()
    -- Do not finalize anything if an event stream failed to flush/close.
    flush()
    assert(log:close(),'Failed closing frame event log')
    if timed_log then assert(timed_log:close(),'Failed closing CPU-cycle log') end
    -- Final checksum is calculated from the exact bytes on disk,
    -- independently of in-memory event counts or snapshot metadata.
    local frame_log_hash=event_log_checksum(log_path)
    local cycle_log_hash=timed_log and event_log_checksum(timed_path)
                         or 'not_captured'
    -- Independent single-pass readback is mandatory before publishing
    -- the final session; a lost or altered TSV byte is not certified.
    assert(frame_log_hash==adler32_state_hex(frame_log_a,frame_log_b),
           'Frame event log readback differs from flushed bytes')
    if timed_log then
        assert(cycle_log_hash==adler32_state_hex(cycle_log_a,cycle_log_b),
               'CPU-cycle log readback differs from flushed bytes')
    end
    local complete = frames_captured>0 and dropped_writes==0
        and callback_errors==0 and capture_failures==0 and callback_gaps==0
        and cycle_regressions==0
    local report={
        'format=fceux_ppu_session_v1',
        'session_id='..session_id,
        'complete='..(complete and 'yes' or 'no'),
        'first_callback_frame='..tostring(first_frame or -1),
        'last_callback_frame='..tostring(last_frame),
        'frame_callbacks='..tostring(callback_frames),
        'frame_callback_gaps='..tostring(callback_gaps),
        'frames_captured='..tostring(frames_captured),
        'capture_frames='..table.concat(captured_frame_list,','),
        'events_recorded='..tostring(total_writes),
        'event_checksum=adler32_v1',
        'cycle_order_policy=nondecreasing_v1',
        'cycle_regressions='..tostring(cycle_regressions),
        'cycle_equal_adjacent='..tostring(cycle_equal_adjacent),
        'cycle_regressions_same_frame='..tostring(cycle_regressions_same_frame),
        'cycle_regressions_between_frames='..tostring(cycle_regressions_between_frames),
        'frame_log_adler32='..frame_log_hash,
        'cycle_log_adler32='..cycle_log_hash,
        'events_dropped='..tostring(dropped_writes),
        'callback_errors='..tostring(callback_errors),
        'capture_failures='..tostring(capture_failures),
        'cycle_trace_available='..(clock_available and 'yes' or 'no'),
        'mmc3_write_coverage=full_8000_ffff_even_odd',
        'ppu_register_write_coverage=full_2000_3fff_mod8',
        'ppu_status_read_coverage=full_2000_3fff_mod8',
    }
    publish_metadata(session_path,table.concat(report,'\n')..'\n')
end)
