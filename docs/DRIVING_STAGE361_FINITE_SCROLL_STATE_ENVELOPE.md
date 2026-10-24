# Vice: Project Doom HD Remake — Stage361 finite scroll-mode evidence envelope

## Status and source boundary

Stage361 is a **source-safe engineering classifier, not a new original FCEUX experiment and not a game camera physics implementation**. The tool `tools/stage361_scroll_mode_envelope.py` consumes **only** existing public numerical summaries from Stage360 and Stage359. It does not load any original NES ROM, FM2 input recording, 256×240 RGB frames, original palette planes, full CPU/PPU trace rows, or owner-private hashes. The underlying original source provenance, completeness and owner-only Google Drive SHA readback were established by Stage359 and Stage360, and are **not freshly verified** by Stage361.

The precise original source finite witness is limited to **41 consecutive adjacent image pairs 519→520 through 559→560**, assembled exclusively from source-safe archived results:

| Source of previously measured evidence | Source pair starts | Number of pairs | Shift selected by source ROI evidence | Frame-local first second-phase $2005 Y difference |
| --- | --- | ---: | ---: | ---: |
| Stage360 first separately archived join | 519 | 1 | +3 px | −3 mod 240 |
| Stage350 original aggregate, reported at Stage360 | 520–526 | 7 | +3 px | −3 mod 240 |
| Stage350 original aggregate, reported at Stage360 | 527–543 | 17 | +4 px | −4 mod 240 |
| Stage360 second join | 544 | 1 | +4 px | −4 mod 240 |
| Stage359 independently preregistered original holdout | 545–558 | 14 | +4 px | −4 mod 240 |
| Stage360 third separately archived join | 559 | 1 | +5 px | −5 mod 240 |
| **Finite total** | **519–559** | **41** | **8×+3, 32×+4, 1×+5** | All previously qualified and matched |

All 41 pair-start frame numbers are consecutive; the documented modes and transitions are **observations only**, with two adjacent qualified changes in this finite record:
- The first +4 image displacement is at original pair **527→528**, immediately after last +3 pair 526→527.
- The first +5 image displacement **in this bounded window** is pair **559→560**, immediately after prior +4 pair 558→559.

The model does not assert that these are the first +4/+5 events anywhere in the game, or that the observed mode changes are deterministic physics rules. It does not extrapolate to frames 561+, other levels, other input movies, alternate PPU render modes, NES dot timing, road collision, acceleration, or car movement.

## Fail-closed witness classifier

Each input record must provide exact adjacent frame pair start, observed RGB displacement, evidence strength, independently measured first `$2005` Y signed modulo-240 step or an explicit missing value, source-provenance status, and whether the image was flat/identical. These are separate fields rather than a single presumed camera value.

Allowed evidence strengths: `strict_four_of_four`, `qualified_three_of_four`, `image_inconclusive`, `mask_conflict`. The special `archived_qualified_unpartitioned` exists **only** for Stage350 and Stage359 numeric aggregate input, because their public summaries give confidence counts but not the original per-frame tier map. It cannot be used for new independently scored frame pairs. Neither invented confidence tiers nor reconstruction of original raw source is permitted.

The classifier returns `confirmed_finite_mode` **only** if an image shift is confidently sourced, not flat/identical, authenticated as evidence, within the limited 3/4/5-pixel set, the frame-local source register step is present, and its signed value is exactly the *negative* RGB shift. All other outcomes stay explicit:

| Negative / boundary condition | Result |
| --- | --- |
| Missing original first PPU Y witness | `register_unsupported`, no state interpolation |
| Pixel vs verified first Y disagrees | `image_register_contradiction`, no forced agreement |
| Confident ROI masks disagree | `confident_mask_conflict`, not a valid mode |
| Non-discriminating/flat/byte-identical image | `image_inconclusive`, no “stationary camera” conclusion |
| Original provenance absent or unverified | `source_unverified` |
| Valid shift outside this finite 3/4/5 envelope (e.g. Stage357 0) | `verified_out_of_scope_shift`, not a contradiction to prior evidence |
| Missing, duplicate, or reordered pair start | Fail closed; no missing-frame fill or transition inference |

An unqualified/unsupported/conflicting pair breaks the observed mode run. A transition is recorded only when two **adjacent qualified pair** observations have different supported shifts. The tool reports the observed shift and pairs; it never outputs an estimated car speed.

## Reproducibility

Run from project root with Python standard library only:

```bash
python3 tools/stage361_scroll_mode_envelope.py \
  --stage360 docs/stage360_public_aggregate.json \
  --stage359 docs/stage359_public_aggregate.json \
  --output /tmp/stage361_bounded_model.json

python3 -m unittest discover -s tests -p test_stage361_scroll_mode_envelope.py -v
```

A published result is tracked as `docs/stage361_public_bounded_envelope.json`. The synthetic/public-safe test suite regenerates it from both pre-existing Stage359 and Stage360 summaries and compares the exact parsed JSON; any earlier source summary mutation invalidates the model rather than silently rewriting the source record.

## Original source integrity and evidence archival

- The original owner-private Stage359 capture and Stage360 cross-archive SHA source ledger remain immutable and separate on private Google Drive; Stage361 does **not** reupload original media or claim to reacquire it.
- Owner-only Stage361 derived source-safe diagnostics and handoff must be archived under `Project Evidence Archive — Private/Vice Project Doom HD Remake` and independently recovered with full SHA-256, ZIP CRC and per-member hashes before claiming archive completion.
- Public GitHub includes only the library, regression tests, this document, safe JSON and non-copyrighted source-free derived results. No ROM, FM2, copyrighted graphics, private original manifest source hashes, raw PPU/CPU traces, original capture Lua or new original media.
- Prior Stage355 **FAILED/INCONCLUSIVE** RGB-motion test and Stage357's **five still-inconclusive** RGB pairs remain unchanged.

## Future verification gate

A later test of broader physical behavior requires **new prospectively preregistered original** samples and independent separate game control/vehicle/road measures. The Stage361 envelope must not be used as a drop-in global camera, scroll, or vehicle simulation. Keep PR #99 **Draft** and `main` untouched.
