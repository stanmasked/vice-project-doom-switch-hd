"""Stage374 ROM-free confidence-tier and register-correlation guard.

Pure synthetic numeric testing only. Does not authenticate or consume NES files,
FCEUX RGB captures, movie streams, raw native PPU events or private source hashes.
"""
from __future__ import annotations
from collections import Counter
import math

FIRST, LAST = 641, 655
BANDS = {
    'left_environment': (0, 52, 20, 175),
    'right_environment': (195, 255, 20, 175),
    'left_marking': (93, 99, 20, 175),
    'right_marking': (157, 163, 20, 175),
}
MIN_SHIFT, MAX_SHIFT = -24, 24
MAX_ERROR = .16
MIN_GAP = .045
TIERS = ('strict_four_of_four', 'qualified_three_of_four', 'mask_conflict', 'flat', 'inconclusive')


def classify(scores: dict[str, tuple[int, float, float, bool]]) -> tuple[str, int | None]:
    """A band record is (signed shift, best RGB mismatch, runner-up gap, flat)."""
    if set(scores) != set(BANDS):
        raise ValueError('four fixed, named Stage344 regions required')
    good = []
    any_flat = False
    for name in BANDS:
        row = scores[name]
        if not isinstance(row, (tuple, list)) or len(row) != 4:
            raise ValueError('malformed source-free band result')
        shift, error, gap, flat = row
        if (type(shift) is not int or shift < MIN_SHIFT or shift > MAX_SHIFT
                or type(flat) is not bool
                or type(error) not in (int, float) or type(gap) not in (int, float)
                or not math.isfinite(error) or not math.isfinite(gap)
                or not 0 <= error <= 1 or not 0 <= gap <= 1):
            raise ValueError('invalid confidence values or signed shift')
        any_flat |= flat
        if not flat and error <= MAX_ERROR and gap >= MIN_GAP:
            good.append(shift)
    if any_flat:
        return 'flat', None
    if len(set(good)) > 1:
        return 'mask_conflict', None
    if len(good) == 4:
        return 'strict_four_of_four', good[0]
    if len(good) == 3:
        return 'qualified_three_of_four', good[0]
    return 'inconclusive', None


def register_comparison(tier: str, shift: int | None,
                        y_before: int | None, y_after: int | None) -> str:
    if tier not in TIERS:
        raise ValueError('unknown confidence tier')
    qualified = tier in TIERS[:2]
    if not qualified:
        if shift is not None:
            raise ValueError('unqualified pair must not impute an image shift')
        return 'unqualified'
    if type(shift) is not int or not MIN_SHIFT <= shift <= MAX_SHIFT:
        raise ValueError('invalid qualified image shift')
    if (type(y_before) is not int or type(y_after) is not int
            or not 0 <= y_before < 240 or not 0 <= y_after < 240):
        return 'unsupported'
    delta = ((y_after - y_before + 120) % 240) - 120
    if delta == -120:
        return 'unsupported'
    return 'match' if shift == -delta else 'contradiction'


def summarize(pairs: list[tuple[int, str, int | None, str]]) -> dict:
    if len(pairs) != 14 or [p[0] for p in pairs] != list(range(FIRST, LAST)):
        raise ValueError('exact consecutive 14-pair holdout required')
    c = Counter()
    for frame, tier, shift, verdict in pairs:
        if tier not in TIERS or verdict not in ('match', 'contradiction', 'unsupported', 'unqualified'):
            raise ValueError('unsupported source-free pair label')
        if tier in TIERS[:2]:
            if type(shift) is not int or verdict == 'unqualified':
                raise ValueError('qualified pair requires an explicit source-register verdict')
        elif shift is not None or verdict != 'unqualified':
            raise ValueError('inconclusive original image may not be promoted')
        c[tier] += 1
        c[verdict] += 1
    return {
        'source_pairs': 14,
        'strict_four_of_four': c['strict_four_of_four'],
        'qualified_three_of_four': c['qualified_three_of_four'],
        'flat': c['flat'],
        'mask_conflict': c['mask_conflict'],
        'inconclusive': c['inconclusive'],
        'source_register_matches': c['match'],
        'source_register_contradictions': c['contradiction'],
        'source_register_unsupported': c['unsupported'],
        'unqualified': c['unqualified'],
        'all_14_original_frame_pairs_proven': c['match'] == 14,
        'source_original_media_authenticated_here': False,
        'camera_vehicle_collision_physics_proven': False,
    }
