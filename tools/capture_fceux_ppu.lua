-- FCEUX private PPU and CPU RAM capture. Use a personally obtained NES ROM.
-- Create the directory in advance and set the path below.
-- DO NOT add any captured files to Git!
local OUTPUT_DIRECTORY = "private"
local FRAME_INTERVAL = 120
local MAX_CAPTURES = 24
local MAX_EVENTS = 12000

local n = 0
local last_frame = -1
local event_count = 0
local events = {}
local chr = {}
local mmc3_select = nil
local ppuctrl, ppumask = nil,nil

local function hx(v)
    if v == nil then return "unknown" end
    return string.format("%02X",v)
end

local function on_write(address,size,value)
    if address==0x2000 then ppuctrl=value end
    if address==0x2001 then ppumask=value end
    if address==0x8000 then mmc3_select=value end
    if address==0x8001 and mmc3_select~=nil then
        local r=mmc3_select%8
        if r<=5 then chr[r]=value end
    end
    if event_count<MAX_EVENTS then
        table.insert(events,string.format("%d\t%04X\t%02X\n",emu.framecount(),address,value))
        event_count=event_count+1
    end
end

for _,addr in ipairs({0x2000,0x2001,0x2005,0x2006,0x2007,
                      0x8000,0x8001,0xA000,0xC000,0xC001,0xE000,0xE001}) do
    memory.registerwrite(addr,on_write)
end

local log=assert(io.open(OUTPUT_DIRECTORY.."/mmc3_video_writes.tsv","wb"))
log:write("frame\taddress\tvalue\n")
local function flush()
    if #events>0 then log:write(table.concat(events));log:flush();events={} end
end
local function write(path,value)
    local f=assert(io.open(path,"wb"))
    f:write(value);f:close()
end
local function meta(frame)
    local lines={
        "format=fceux_ppu_snapshot_v1",
        "frame="..tostring(frame),
        "rom_md5="..tostring(rom.gethash("md5")),
        "ppuctrl="..hx(ppuctrl),
        "ppumask="..hx(ppumask),
        "mmc3_select="..hx(mmc3_select),
        "register_write_events="..tostring(event_count),
        "queue_index_16="..hx(memory.readbyte(0x16))
    }
    for i=0,5 do
        table.insert(lines,"chr_r"..i.."="..hx(chr[i]))
        table.insert(lines,"chr_ram_"..i.."="..hx(memory.readbyte(0x3d+i)))
    end
    return table.concat(lines,"\n").."\n"
end
local function capture_frame()
    local frame=emu.framecount()
    if frame==last_frame or frame%FRAME_INTERVAL~=0 or n>=MAX_CAPTURES then
        flush()
        return
    end
    last_frame=frame
    local ppu_data=ppu.readbyterange(0,0x4000)
    local ram_data=memory.readbyterange(0,0x0800)
    assert(type(ppu_data)=="string" and #ppu_data==0x4000,"PPU snapshot length mismatch")
    assert(type(ram_data)=="string" and #ram_data==0x0800,"RAM snapshot length mismatch")
    local prefix=OUTPUT_DIRECTORY.."/frame_"..string.format("%06d",frame)
    write(prefix..".ppu.bin",ppu_data)
    write(prefix..".ram.bin",ram_data)
    write(prefix..".meta.txt",meta(frame))
    n=n+1
    flush()
    emu.message("Private Vice PPU snapshot "..n.."/"..MAX_CAPTURES)
end
emu.registerafter(capture_frame)
emu.registerexit(function()flush();log:close()end)
