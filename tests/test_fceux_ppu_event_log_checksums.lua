-- Stage83 synthetic FCEUX collector: full TSV and per-frame prefix checksums.
-- Never opens or embeds original game ROM / graphics.
local saved_io=io
local function read(path)
    local file=assert(saved_io.open(path,'rb'))
    local bytes=assert(file:read('*a'))
    assert(file:close())
    return bytes
end
local function adler(bytes)
    local a,b=1,0
    for i=1,#bytes do
        a=(a+bytes:byte(i))%65521
        b=(b+a)%65521
    end
    return string.format('%08X',b*65536+a)
end
local function value(meta,key)
    return assert(meta:match('\n'..key..'=([^\n]*)')
        or meta:match('^'..key..'=([^\n]*)'))
end
local function run(clock_enabled,corrupt_final)
    local dir=os.tmpname()
    os.remove(dir)
    assert(os.execute('mkdir -p "'..dir..'"'))
    VPD_CAPTURE_DIRECTORY=dir
    VPD_CAPTURE_INTERVAL=1
    VPD_CAPTURE_LIMIT=2
    VPD_CAPTURE_SCREEN=false
    local frame=1
    local next_cycle=100
    local write_ppu,read_ppu,write_mmc3,after,exit
    memory={
        registerwrite=function(addr,size,fn)
            if addr==0x2000 then
                assert(size==0x2000);write_ppu=fn
            else
                assert(addr==0x8000 and size==0x8000)
                write_mmc3=fn
            end
        end,
        registerread=function(addr,size,fn)
            assert(addr==0x2000 and size==0x2000)
            read_ppu=fn
        end,
        readbyte=function()return 0 end,
        readbyterange=function(addr,size)
            assert(addr==0 and size==0x800)
            return string.rep('r',0x800)
        end,
    }
    ppu={readbyterange=function(addr,size)
        assert(addr==0 and size==0x4000)
        return string.rep('p',0x4000)
    end}
    debugger=clock_enabled and {getcyclescount=function()
        next_cycle=next_cycle+10
        return next_cycle
    end} or nil
    rom={gethash=function(alg)
        assert(alg=='md5');return string.rep('a',32)
    end}
    emu={
        framecount=function()return frame end,
        registerafter=function(fn)after=fn end,
        registerexit=function(fn)exit=fn end,
        message=function()end,
    }
    dofile('tools/capture_fceux_ppu.lua')
    local log=dir..'/mmc3_video_writes.tsv'
    local timed=dir..'/mmc3_ppu_cycles.tsv'
    local metadata=dir..'/ppu_capture_session.meta.txt'
    local frame_prefixes={}
    local cycle_prefixes={}
    local logged_reads={frame=0,cycle=0}
    local tampered=false
    -- Observe reads done by the real collector. Reads made by this
    -- test use saved_io and therefore do not affect the counters.
    io={open=function(path,mode)
        if mode=='rb' and path==log then
            logged_reads.frame=logged_reads.frame+1
        elseif mode=='rb' and path==timed then
            logged_reads.cycle=logged_reads.cycle+1
        end
        local handle,error_message=saved_io.open(path,mode)
        if not handle then return handle,error_message end
        if corrupt_final and path==log and mode=='rb' and not tampered then
            return {
                read=function(_,amount)
                    local bytes=handle:read(amount)
                    if bytes and bytes:find('8002',1,true) then
                        tampered=true
                        return (bytes:gsub('8002','8003',1))
                    end
                    return bytes
                end,
                close=function()return handle:close() end,
            }
        end
        return handle
    end}
    for n=1,2 do
        frame=n
        write_mmc3(0x8002,1,0x80)
        read_ppu(0x3FFA,1,0)
        after()
        local prefix=string.format('%s/frame_%06d',dir,n)
        local m=read(prefix..'.meta.txt')
        assert(value(m,'event_checksum')=='adler32_v1')
        frame_prefixes[n]=adler(read(log))
        assert(value(m,'frame_log_prefix_adler32')==frame_prefixes[n])
        if clock_enabled then
            cycle_prefixes[n]=adler(read(timed))
            assert(value(m,'cycle_log_prefix_adler32')==cycle_prefixes[n])
        else
            assert(value(m,'cycle_log_prefix_adler32')=='not_captured')
        end
        assert(read(metadata)=='capture_in_progress=yes\n')
        assert(logged_reads.frame==0,'Repeated on-frame TSV readback')
        assert(logged_reads.cycle==0,'Repeated on-frame CPU-cycle readback')
    end
    local ok,why=pcall(exit)
    assert(logged_reads.frame==1,'Final TSV must be read exactly once')
    assert(logged_reads.cycle==(clock_enabled and 1 or 0),
           'Final CPU-cycle TSV must be read exactly once, if present')
    if corrupt_final then
        assert(not ok and tostring(why):find('readback differs from flushed bytes',1,true),
               tostring(why))
        assert(tampered,'Test did not inject changed TSV bytes')
        assert(read(metadata)=='capture_in_progress=yes\n')
    else
        assert(ok,tostring(why))
    end
    local final=corrupt_final and nil or read(metadata)
    if not corrupt_final then
        assert(value(final,'complete')=='yes')
        assert(value(final,'events_recorded')=='4')
        assert(value(final,'event_checksum')=='adler32_v1')
        assert(value(final,'frame_log_adler32')==frame_prefixes[2])
        if clock_enabled then
            assert(value(final,'cycle_log_adler32')==cycle_prefixes[2])
        else
            assert(value(final,'cycle_log_adler32')=='not_captured')
        end
    end
    for n=1,2 do
        local prefix=string.format('%s/frame_%06d',dir,n)
        for _,ext in ipairs({'.meta.txt','.ppu.bin','.ram.bin'}) do
            assert(os.remove(prefix..ext))
        end
    end
    -- No collector callbacks remain active beyond this point.
    io=saved_io
    assert(os.remove(log))
    if clock_enabled then assert(os.remove(timed)) end
    assert(os.remove(metadata))
    assert(os.execute('rmdir "'..dir..'"'))
end
run(true,false)
run(false,false)
run(true,true)
print('Stage84 rolling PPU event digests, final readback and corruption rejection PASS')
