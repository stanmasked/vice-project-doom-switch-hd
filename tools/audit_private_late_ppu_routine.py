#!/usr/bin/env python3
"""ROM-free verifier of PRIVATE original FCEUX instruction and register traces.

No source game content is embedded or copied to public GitHub. Matched CPU
writes are not evidence of the PPU scanline when they become visible.
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

HEADER=["frame","cycle","type","address","value","a","x","y","p"]
PCS=[("E367",0),("E369",4),("E36C",8),("E36F",10),("E371",12),
     ("E373",16),("E376",20),("E379",22),("E37B",24),("E37D",28),
     ("E380",32),("E383",34),("E384",38),("E387",42),("E38A",45),("E38E",51)]
WRITES=[("E369","2005",0,"x"),("E36C","2005",0,"x"),
        ("E373","2006",15,"a"),("E376","2006",0,"x"),
        ("E37D","8000",0,"x"),("E380","8001",0,"x"),
        ("E384","8000",1,"x"),("E387","8001",2,"a"),
        ("E38E","2001",14,"a")]


def private_file(path,max_size):
    p=Path(path)
    if p.is_symlink() or not p.is_file() or not 0<p.stat().st_size<=max_size:
        raise ValueError("private input missing, linked or oversized")
    return p


def decimal(value,name):
    if not isinstance(value,str) or not value.isascii() or not value.isdecimal() or value!=str(int(value)):
        raise ValueError("invalid decimal "+name)
    return int(value)


def hexnum(value,name,digits):
    if (not isinstance(value,str) or len(value)!=digits or
        any(ch not in "0123456789abcdefABCDEF" for ch in value)):
        raise ValueError("invalid hexadecimal "+name)
    return int(value,16)


def witness_check(path,stop,observed):
    metadata={}
    for line in private_file(path,4096).read_text(encoding="ascii").splitlines():
        if "=" not in line:raise ValueError("malformed private completion marker")
        key,val=line.split("=",1)
        if key in metadata:raise ValueError("duplicate completion metadata")
        metadata[key]=val
    needed={"format","first_observed_frame","last_observed_frame","frame_gaps",
            "callback_events","rom_identity_verified","movie_readonly_verified"}
    if metadata.keys()!=needed or metadata["format"]!="private_stage155_cpu_sequence_v1":
        raise ValueError("private completion schema mismatch")
    if (metadata["rom_identity_verified"]!="yes" or
        metadata["movie_readonly_verified"]!="yes" or
        decimal(metadata["first_observed_frame"],"first frame") not in (0,1) or
        decimal(metadata["last_observed_frame"],"last frame")!=stop or
        decimal(metadata["frame_gaps"],"frame gaps")!=0 or
        decimal(metadata["callback_events"],"event count")!=observed):
        raise ValueError("original ROM/FM2 playback provenance incomplete")


def audit(trace,witness,*,start=600,stop=920):
    if type(start)is not int or type(stop)is not int or start<1 or stop<start or stop-start>1200:
        raise ValueError("invalid target frame window")
    entries=defaultdict(list)
    previous_frame,previous_cycle=-1,-1
    count=0
    with private_file(trace,16*1024*1024).open("r",encoding="ascii",newline="") as f:
        rows=csv.DictReader(f,delimiter="\t")
        if rows.fieldnames!=HEADER:raise ValueError("private CPU event schema mismatch")
        for row in rows:
            count+=1
            if count>250000 or set(row)!=set(HEADER) or any(v is None for v in row.values()):
                raise ValueError("malformed or oversized private event stream")
            frame=decimal(row["frame"],"frame")
            cycle=decimal(row["cycle"],"CPU cycle")
            if frame<previous_frame or cycle<previous_cycle:
                raise ValueError("CPU callbacks unordered or cycle epoch changed")
            previous_frame,previous_cycle=frame,cycle
            kind=row["type"]
            if kind not in ("PC","WR"):raise ValueError("invalid CPU callback kind")
            address=row["address"].upper()
            hexnum(address,"address",4)
            value=hexnum(row["value"],"value",2)
            regs={k:hexnum(row[k],"CPU register "+k,2) for k in ("a","x","y","p")}
            if start<=frame<=stop:
                entries[frame].append((cycle,kind,address,value,regs))
    witness_check(witness,stop,count)
    if len(entries)!=stop-start+1:
        raise ValueError("private PC trace contains missing frames")
    for frame in range(start,stop+1):
        pcs=defaultdict(list)
        register_writes=defaultdict(list)
        for entry in entries[frame]:
            if entry[1]=="PC":pcs[entry[2]].append(entry)
            else:register_writes[(entry[0],entry[2],entry[3])].append(entry)
        if any(len(pcs[pc])!=1 for pc,_ in PCS):
            raise ValueError("missing or duplicated original late-handler instruction")
        base=pcs["E367"][0][0]
        for pc,offset in PCS:
            if pcs[pc][0][0]-base!=offset:
                raise ValueError("original late-handler instruction cycle offset differs")
        for pc,port,value,reg in WRITES:
            seen=pcs[pc][0]
            if seen[4][reg]!=value:
                raise ValueError("CPU register changed at original writer instruction")
            if len(register_writes[(seen[0],port,value)])!=1:
                raise ValueError("CPU instruction and actual PPU/MMC3 write differ")
    frames=stop-start+1
    return {
      "schema":"vpd_private_late_ppu_routine_audit_v1",
      "classification":"Original CPU instruction/write evidence, not PPU scanline proof",
      "start_frame":start,"stop_frame":stop,"frames_verified":frames,
      "executed_instructions_per_frame":len(PCS),
      "exact_instruction_pc_cycle_matches":len(PCS)*frames,
      "writes_per_frame_from_late_routine":len(WRITES),
      "exact_instruction_to_register_write_matches":len(WRITES)*frames,
      "late_scroll_reset_values":["00","00"],
      "ppuaddr_pair":["0F","00"],
      "mmc3_chr_register_sequence":["8000=00","8001=00","8000=01","8001=02"],
      "ppumask_value":"0E",
      "ppumask_background_enabled":True,
      "ppumask_sprite_rendering_enabled":False,
      "visible_scanline_origin_verified":False,
      "irq_origin_verified":False,
      "camera_velocity_verified":False,
      "source_game_bytes_in_report":False
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("private_cpu_trace",type=Path)
    p.add_argument("private_completion_witness",type=Path)
    p.add_argument("--start",type=int,default=600)
    p.add_argument("--stop",type=int,default=920)
    args=p.parse_args()
    try:
        result=audit(args.private_cpu_trace,args.private_completion_witness,
                     start=args.start,stop=args.stop)
    except (OSError,ValueError,UnicodeError) as error:
        p.exit(1,"PRIVATE_LATE_PPU_ROUTINE_INCONCLUSIVE: "+str(error)+"\n")
    print("PRIVATE_LATE_PPU_ROUTINE_PROVENANCE_PASS")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
