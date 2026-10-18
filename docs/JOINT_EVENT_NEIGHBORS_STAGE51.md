# Stage 51 — temporal neighbors of CPU execution hooks and PRG reads

The new `tools/joint_event_neighbors.py` first invokes the strict
stage50 joint-trace validator. Within the same emulator frame, it emits
candidate pairs between the latest *instrumented* EXEC hook and a READ
callback only when at most `--max-gap` events separate them and no
MMC3 mapper write intervened. Any frame change blocks a pair.

```sh
python3 tools/joint_event_neighbors.py private/first_level/stage49_joint.tsv --meta private/first_level/stage49_joint.meta.txt --max-gap 3 --out private/first_level/stage51_neighbors.json
```

**Every emitted pair is explicitly `temporal_neighbor_only`.** A sparse
EXEC hook cannot prove the instruction responsible for a read; missing
CPU registers, actual opcode decoding, effective-address computation
and possible instruction-fetch reads prevent causal attribution. The
tool never labels a pair as verified gameplay data, camera, collision
or level geometry.

ROM-free unit tests cover valid proximity, mapper intervention, invalid
event-gap settings and refusal of incomplete captures. The test run and
any actual FCEUX session remain unverified until executed.
