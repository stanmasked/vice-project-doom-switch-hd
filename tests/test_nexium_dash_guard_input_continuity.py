"""Guard against the dash/alert host-input race observed in NeXium.

Native guest evidence (not this source-level guard) remains the sole PASS
condition for enemy detection and manual combat.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
HOST=ROOT/"tools/nexium_visual_probe.sh"


def verify_continuous_right(script):
    begin=script.find("    xdotool keydown --clearmodifiers t\n")
    end=script.find("    saw_strike=no\n",begin)
    if begin<0 or end<0:
        raise ValueError("ZR-to-contact control sequence not found")
    handoff=script[begin:end]
    if "    xdotool keyup t\n" not in handoff:
        raise ValueError("ZR never released after dash test")
    if "    xdotool keyup d\n" in handoff:
        raise ValueError("Right was released before first guard alert")
    if "    xdotool keydown --clearmodifiers d\n" in handoff:
        raise ValueError("Second Right keydown replaced seamless hold")
    if "    sleep 0.25\n" in handoff:
        raise ValueError("Long idle dash-to-guard input gap restored")
    next_release=script.find("    xdotool keyup d\n",end)
    if next_release<0:
        raise ValueError("No Right release after guard first-strike trial")
    poll=script[end:next_release]
    if ("seq=2 event=strike" not in poll or
        "for (( attempt=0; attempt<165; ++attempt ))" not in poll):
        raise ValueError("Guard first strike no longer gates release")
    return True


class NeXiumDashGuardInputContinuity(unittest.TestCase):
    def test_host_keeps_real_right_input_during_alert_transition(self):
        self.assertTrue(verify_continuous_right(HOST.read_text(encoding="utf8")))

    def test_reject_previous_idle_gap_and_restart_regression(self):
        source=HOST.read_text(encoding="utf8")
        self.assertTrue(verify_continuous_right(source))
        release=source.replace("    xdotool keyup t\n",
                               "    xdotool keyup t\n    xdotool keyup d\n",1)
        with self.assertRaisesRegex(ValueError,"Right was released"):
            verify_continuous_right(release)
        restart=source.replace('    saw_strike=no\n',
                               '    xdotool keydown --clearmodifiers d\n'
                               '    saw_strike=no\n',1)
        with self.assertRaisesRegex(ValueError,"Second Right"):
            verify_continuous_right(restart)
        missing=source.replace('    xdotool keyup t\n',"",1)
        with self.assertRaisesRegex(ValueError,"ZR never released"):
            verify_continuous_right(missing)


if __name__=="__main__":
    unittest.main()
