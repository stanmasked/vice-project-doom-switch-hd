"""Enforce one shared 200-frame combat demo for both Switch prototypes.

These are source-structure checks; native execution is covered by CTest.
"""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SharedCombatDemoTests(unittest.TestCase):
    def test_shared_script_in_all_runtime_consumers(self):
        uses={
            "game_core/combat_replay.cpp":"vpd::combatDemoInput(frame)",
            "tests/test_graphics_combat_integration.cpp":"vpd::combatDemoInput(frame)",
            "switch_graphical/source/main.cpp":"demo.tick(game)",
            "switch_probe/source/main.cpp":"demo.tick(game)",
        }
        for name,call in uses.items():
            with self.subTest(file=name):
                source=(ROOT/name).read_text(encoding="utf-8")
                self.assertIn('#include "combat_demo.hpp"',source)
                self.assertIn(call,source)
                self.assertNotIn("vpd::Input inputAt(unsigned frame)",source)
        for name in ("switch_graphical/Makefile","switch_probe/Makefile"):
            with self.subTest(makefile=name):
                self.assertIn("../game_core/combat_demo.hpp",
                              (ROOT/name).read_text(encoding="utf-8"))

    def test_manual_toggle_does_not_disable_plus_exit(self):
        for name in ("switch_graphical/source/main.cpp",
                     "switch_probe/source/main.cpp"):
            source=(ROOT/name).read_text(encoding="utf-8")
            with self.subTest(file=name):
                self.assertIn("demo.toggle(game)",source)
                self.assertIn("demo.enabled()",source)
                self.assertIn("HidNpadButton_Plus",source)
        source=(ROOT/"switch_graphical/source/main.cpp").read_text(encoding="utf-8")
        self.assertIn("HidNpadButton_StickL",source)
        self.assertIn("view.replay_demo=demo.enabled()",source)
        self.assertIn("animation.reset()",source)

    def test_label_is_opt_in_to_keep_original_golden_frame(self):
        header=(ROOT/"graphics_core/scene_renderer.hpp").read_text(encoding="utf-8")
        impl=(ROOT/"graphics_core/scene_renderer.cpp").read_text(encoding="utf-8")
        self.assertIn("bool replay_demo=false",header)
        self.assertIn('s.text(760,18,"REPLAY DEMO"',impl)
        self.assertIn("if(view.replay_demo)",impl)

if __name__=="__main__":
    unittest.main()
