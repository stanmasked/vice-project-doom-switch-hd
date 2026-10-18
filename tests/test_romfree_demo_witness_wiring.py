"""Static wiring guards; not a substitute for actual emulator execution."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class WitnessWiringTests(unittest.TestCase):
    def test_both_nro_frontends_use_the_same_bounded_sink(self):
        for source, makefile in (
            ("switch_graphical/source/main.cpp","switch_graphical/Makefile"),
            ("switch_probe/source/main.cpp","switch_probe/Makefile"),
        ):
            with self.subTest(source=source):
                text=(ROOT/source).read_text(encoding="utf-8")
                rules=(ROOT/makefile).read_text(encoding="utf-8")
                self.assertEqual(text.count('#include "demo_witness_sd.hpp"'),1)
                self.assertEqual(text.count("vpd::demoCheckpointReached(demo,game)"),1)
                self.assertEqual(text.count("vpd::persistDemoWitness("),1)
                self.assertIn("witness_cycles<vpd::kDemoWitnessMaxRecords",text)
                self.assertIn("has_sd",text)
                self.assertLess(text.index("demoCheckpointReached(demo,game)"),
                                text.index("persistDemoWitness("))
                self.assertIn("../game_core/demo_witness.hpp",rules)
                self.assertIn("../game_core/demo_witness_sd.hpp",rules)

    def test_witness_has_strict_golden_state_and_fail_records(self):
        body=(ROOT/"game_core/demo_witness.hpp").read_text(encoding="utf-8")
        sd=(ROOT/"game_core/demo_witness_sd.hpp").read_text(encoding="utf-8")
        self.assertIn("5947277116621119566ULL",body)
        self.assertIn("game.shotsFired()==11U",body)
        self.assertIn("game.trainingTarget().hits==3U",body)
        self.assertIn("game.trainingTarget().health==0U",body)
        self.assertIn("cycle>kDemoWitnessMaxRecords",body)
        self.assertIn('demoCheckpointMatches(game)?"yes":"no"',body)
        self.assertIn("std::fflush(output)==0",body)
        self.assertIn("if(!has_sd",sd)
        self.assertIn('demo_witness.txt',sd)
        self.assertIn('std::fclose(file)',sd)

    def test_graphical_checkpoint_does_not_precede_frame_submission(self):
        graphics=(ROOT/"switch_graphical/source/main.cpp").read_text(
            encoding="utf-8")
        ascii_scene=(ROOT/"switch_probe/source/main.cpp").read_text(
            encoding="utf-8")
        self.assertLess(graphics.index("framebufferEnd(&fb);"),
                        graphics.index("demoCheckpointReached(demo,game)"))
        self.assertLess(graphics.index("if(!drawn)break;"),
                        graphics.index("demoCheckpointReached(demo,game)"))
        self.assertLess(ascii_scene.index("consoleUpdate(nullptr);"),
                        ascii_scene.index("demoCheckpointReached(demo,game)"))
        self.assertIn("view.demo_checkpoint_ok=checkpoint_ok",graphics)
        renderer=(ROOT/"graphics_core/scene_renderer.cpp").read_text(
            encoding="utf-8")
        self.assertIn('if(view.replay_demo && view.demo_checkpoint_ok)',renderer)

if __name__=="__main__":
    unittest.main()
