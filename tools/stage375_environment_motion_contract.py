#!/usr/bin/env python3
"""Stage375 ROM-free numerical contract, using only fabricated test values.

Scientific source authentication is a SEPARATE, private FCEUX process. This module
neither reads original NES data nor authenticates external numerical inputs.
"""
from __future__ import annotations
from collections import Counter
import math

FIRST, LAST = 656, 670
FRAMES = tuple(range(FIRST, LAST + 1))
PALETTE_FRAMES = (656, 663, 670)
# Frozen Stage352/359 environment masks (x0, x1, y0, y1), half-open.
REGIONS = {
    'left_env_upper': (0, 52, 20, 98),
    'left_env_lower': (0, 52, 98, 175),
    'right_env_upper': (195, 255, 20, 98),
    'right_env_lower': (195, 255, 98, 175),
}
MIN_SHIFT, MAX_SHIFT = -24, 24
MAX_ERROR, MIN_GAP = 0.16, 0.045
TIERS = ('strict_four_of_four', 'qualified_three_of_four',
         'mask_conflict', 'flat', 'inconclusive')


def classify(scores: dict[str, tuple[int, float, float, bool]]) -> tuple[str, int | None]:
    """Each record: (best signed shift, best RGB mismatch, runner-up gap, flat)."""
    if set(scores) != set(REGIONS):
        raise ValueError('four frozen original environment ROI labels required')
    confident = []
    any_flat = False
    for name in REGIONS:
        row = scores[name]
        if not isinstance(row, (tuple, list)) or len(row) != 4:
            raise ValueError('malformed ROI score')
        shift, error, gap, flat = row
        if (type(shift) is not int or not MIN_SHIFT <= shift <= MAX_SHIFT
                or type(flat) is not bool
                or type(error) not in (int, float) or type(gap) not in (int, float)
                or not math.isfinite(error) or not math.isfinite(gap)
                or not 0 <= error <= 1 or not 0 <= gap <= 1):
            raise ValueError('invalid source-free numeric confidence')
        any_flat |= flat
        if not flat and error <= MAX_ERROR and gap >= MIN_GAP:
            confident.append(shift)
    if any_flat:
        return 'flat', None
    if len(set(confident)) > 1:
        return 'mask_conflict', None
    if len(confident) == 4:
        return 'strict_four_of_four', confident[0]
    if len(confident) == 3:
        return 'qualified_three_of_four', confident[0]
    return 'inconclusive', None


def register_verdict(tier: str, image_shift: int | None,
                     first_y_before: int | None, first_y_after: int | None) -> str:
    if tier not in TIERS:
        raise ValueError('unknown image confidence tier')
    qualified = tier in TIERS[:2]
    if not qualified:
        if image_shift is not None:
            raise ValueError('unqualified image shift cannot be inferred from registers')
        return 'unqualified'
    if type(image_shift) is not int or not MIN_SHIFT <= image_shift <= MAX_SHIFT:
        raise ValueError('missing/bad qualified image displacement')
    if (type(first_y_before) is not int or type(first_y_after) is not int or
            not 0 <= first_y_before < 240 or not 0 <= first_y_after < 240):
        return 'unsupported'
    source_delta = ((first_y_after - first_y_before + 120) % 240) - 120
    if source_delta == -120:
        return 'unsupported'
    return 'match' if image_shift == -source_delta else 'contradiction'


def summarize(records: list[tuple[int, str, int | None, str]]) -> dict:
    if len(records) != 14 or [rec[0] for rec in records] != list(range(FIRST, LAST)):
        raise ValueError('exact original 14-pair interval is mandatory')
    count = Counter()
    for start, tier, image_shift, verdict in records:
        if tier not in TIERS or verdict not in ('match', 'contradiction', 'unsupported', 'unqualified'):
            raise ValueError('unsupported evidence label')
        if tier in TIERS[:2]:
            if type(image_shift) is not int or not MIN_SHIFT <= image_shift <= MAX_SHIFT or verdict == 'unqualified':
                raise ValueError('qualified image needs qualified source-register verdict')
        elif image_shift is not None or verdict != 'unqualified':
            raise ValueError('never promote inconclusive image with a known register value')
        count[tier] += 1
        count[verdict] += 1
    return {
        'format': 'vpd_stage375_numeric_classification_only_v1',
        'source_frame_window': [FIRST, LAST],
        'adjacent_pairs': 14,
        'strict_four_of_four': count['strict_four_of_four'],
        'qualified_three_of_four': count['qualified_three_of_four'],
        'mask_conflict': count['mask_conflict'],
        'flat': count['flat'],
        'inconclusive': count['inconclusive'],
        'register_matches': count['match'],
        'register_contradictions': count['contradiction'],
        'register_unsupported': count['unsupported'],
        'unqualified': count['unqualified'],
        # Numerical fixtures alone are NEVER original-media provenance.
        'original_media_authentication_by_this_module': False,
        'original_game_camera_vehicle_collision_physics_proven': False,
    }
