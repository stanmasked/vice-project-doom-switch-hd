"""Source-level guard: host combat raster CTest and libnx share one adapter.

Do not confuse this static check with an emulator/runtime NRO test.
"""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWITCH = ROOT / "switch_graphical/source/main.cpp"
HOST = ROOT / "tests/test_graphics_combat_integration.cpp"
BRIDGE = ROOT / "graphics_core/combat_scene_bridge.hpp"
MAKEFILE = ROOT / "switch_graphical/Makefile"


class CombatSceneBridgeTests(unittest.TestCase):
    def test_native_switch_and_host_use_one_identical_adapter(self):
        switch = SWITCH.read_text(encoding="utf-8")
        host = HOST.read_text(encoding="utf-8")
        for filename, text in ((SWITCH, switch), (HOST, host)):
            with self.subTest(path=filename.name):
                self.assertEqual(text.count('#include "combat_scene_bridge.hpp"'), 1)
                self.assertEqual(text.count("vpd::applyCombatOverlay("), 1)
                self.assertNotIn("view.projectiles[i]=", text)
                self.assertNotIn("view.training_target_health=", text)
        self.assertLess(switch.index("vpd::applyCombatOverlay("),
                        switch.index("vpd::drawScene("))
        self.assertLess(host.index("vpd::applyCombatOverlay("),
                        host.index("vpd::drawScene("))
        self.assertIn("combat_scene_bridge.hpp", MAKEFILE.read_text(encoding="utf-8"))

    def test_bridge_copies_actual_game_source_with_bounded_slots(self):
        source = BRIDGE.read_text(encoding="utf-8")
        self.assertEqual(source.count("inline void applyCombatOverlay("), 1)
        self.assertIn("std::tuple_size<decltype(SceneView{}.projectiles)>::value", source)
        self.assertIn("kMaxProjectiles", source)
        self.assertIn("game.trainingTarget()", source)
        self.assertIn("game.projectiles()", source)
        self.assertIn("shots[i].active", source)
        self.assertIn("target.health", source)
        self.assertIn("shots[i].x/kFixed", source)
        self.assertIn("shots[i].y/kFixed", source)
        self.assertEqual(source.count("view.projectiles[i]"), 1)


if __name__ == "__main__":
    unittest.main()
