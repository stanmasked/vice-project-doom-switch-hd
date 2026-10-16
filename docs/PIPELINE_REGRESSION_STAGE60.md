# Stage 60 — integration regression and chronological PRG read grouping

This stage fixes a structural issue in `tools/group_prg_read_ranges.py`.
Previously it grouped only the filtered READ list, so an intervening MMC3
SELECT/DATA callback could disappear from the chronology and two adjacent
physical addresses could be incorrectly interpreted as an uninterrupted
read run. Grouping now walks the original **validated event stream** and
closes a run whenever any non-READ event occurs. A ROM-free regression
covers a fixed-bank address pair with an intervening MMC3 SELECT.

`tests/test_stage60_integration.py` also exercises an entirely synthetic
stage53 trace plus headerless fake PRG through stage54 validation, stage57
bank-byte lookup, stage55/56 address calculation and candidate comparison,
and stage59 SHA-256 pinning. It checks that a matching address remains
noncausal, a wrong digest yields no candidates, and an intervening mapper
event blocks the candidate.

Run the Python regression suite:

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
```

No private ROM content is committed. Passing CI has not yet been observed;
live FCEUX callback conventions, ROM provenance and game-level geometry
remain unverified.
