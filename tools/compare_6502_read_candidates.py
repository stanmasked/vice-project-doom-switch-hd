#!/usr/bin/env python3
"""Stage56: compare user-supplied 6502 operands to verified joint-trace reads.

A matching address is only a hypothesis, NEVER instruction/read causality.
"""
import argparse
import csv
import importlib.util
import json
from pathlib import Path
from validate_joint_cpu_context import validate

def _calculator():
    spec=importlib.util.spec_from_file_location(
        "stage55_address", Path(__file__).with_name("6502_read_address.py"))
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.calculate

def compare(trace, meta, *, exec_seq, opcode_hex, max_gap=3,
            zp_low=None, zp_high=None):
    if type(exec_seq) is not int or exec_seq<1:
        raise ValueError("exec_seq must be positive")
    if type(max_gap) is not int or not 1<=max_gap<=100:
        raise ValueError("max_gap outside 1..100")
    if not isinstance(opcode_hex,str) or len(opcode_hex)%2:
        raise ValueError("Invalid opcode encoding")
    try:
        instruction=bytes.fromhex(opcode_hex)
    except ValueError as e:
        raise ValueError("Invalid opcode encoding") from e
    audited=validate(trace,meta)
    with Path(trace).open(newline="",encoding="utf8") as f:
        events=list(csv.DictReader(f,delimiter="\t"))
    if exec_seq>len(events) or events[exec_seq-1]["kind"]!="EXEC":
        raise ValueError("exec_seq must name an EXEC event")
    origin=events[exec_seq-1]
    def reg(name):
        v=origin[name]
        return None if v=="unknown" else int(v,16)
    calculated=_calculator()(instruction,x=reg("x"),y=reg("y"),
                              zp_low=zp_low,zp_high=zp_high)
    candidates=[]
    barrier=None
    for row in events[exec_seq:]:
        gap=int(row["seq"])-exec_seq
        if gap>max_gap:break
        if row["frame"]!=origin["frame"]:
            barrier="frame_boundary"
            break
        if row["kind"] in ("EXEC","SELECT","DATA"):
            barrier="execution_or_mapper_event"
            break
        if row["kind"]=="READ" and calculated.get("effective_address") is not None:
            addr=int(row["address"],16)
            if addr==calculated["effective_address"]:
                candidates.append({
                    "seq":int(row["seq"]),"cpu_address":row["address"],
                    "bank":row["bank"],"classification":"address_match_only",
                    "instruction_caused_read_proven":False})
    return {
        "schema":1,"capture_complete":audited["complete"],
        "origin_exec_seq":exec_seq,"origin_pc":origin["address"],
        "instruction_bytes_provenance":"supplied_externally_not_verified_against_ROM",
        "calculation":calculated,"candidate_reads":candidates,
        "search_stopped_by":barrier,"causality_proven":False,
        "stage_data_proven":False,"read_values_proven":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("trace",type=Path)
    p.add_argument("--meta",type=Path)
    p.add_argument("--exec-seq",type=int,required=True)
    p.add_argument("--opcode-hex",required=True)
    p.add_argument("--max-gap",type=int,default=3)
    p.add_argument("--zp-low",type=lambda s:int(s,16))
    p.add_argument("--zp-high",type=lambda s:int(s,16))
    p.add_argument("--out",type=Path)
    a=p.parse_args()
    result=compare(a.trace,a.meta or a.trace.with_suffix(".meta.txt"),
                   exec_seq=a.exec_seq,opcode_hex=a.opcode_hex,
                   max_gap=a.max_gap,zp_low=a.zp_low,zp_high=a.zp_high)
    if a.out:
        a.out.parent.mkdir(parents=True,exist_ok=True)
        a.out.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps(result,indent=2))
if __name__=="__main__":main()
