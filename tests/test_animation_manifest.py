"""ROM-free checks for animation JSON schema and generated C++ header."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
from build_animation_manifest import generate_cpp,validate

MANIFEST=Path(__file__).resolve().parents[1]/"assets"/"demo_animation.json"

class AnimationManifestTests(unittest.TestCase):
    def setUp(self):
        self.data=json.loads(MANIFEST.read_text(encoding="utf-8"))
    def test_four_states(self):
        validate(self.data)
        header=generate_cpp(self.data)
        self.assertIn("inline constexpr vpd::AnimationBank kAnimationBank",header)
        self.assertIn("vpd::AnimationFrame{1, 6}",header)
        self.assertIn("vpd::AnimationFrame{2, 8}",header)
        self.assertIn("k_fall",header)
    def test_invalid_state_set(self):
        bad=copy.deepcopy(self.data)
        del bad["states"]["fall"]
        with self.assertRaisesRegex(ValueError,"Exactly"):validate(bad)
    def test_reject_missing_data_and_non_boolean(self):
        bad=copy.deepcopy(self.data);bad["states"]["run"]["loop"]=1
        with self.assertRaisesRegex(ValueError,"boolean"):validate(bad)
        bad=copy.deepcopy(self.data);bad["states"]["rise"]["frames"]=[]
        with self.assertRaisesRegex(ValueError,"number"):validate(bad)
        bad=copy.deepcopy(self.data);bad["unexpected"]="value"
        with self.assertRaisesRegex(ValueError,"properties"):validate(bad)
    def test_reject_out_of_range(self):
        for field,value in (("frame",4),("frame",-1),("ticks",0),("ticks",601),("ticks",True)):
            bad=copy.deepcopy(self.data)
            bad["states"]["run"]["frames"][0][field]=value
            with self.assertRaisesRegex(ValueError,"range"):validate(bad)
    def test_reject_invalid_atlas(self):
        bad=copy.deepcopy(self.data);bad["atlas_frame_count"]=0
        with self.assertRaisesRegex(ValueError,"frame count"):validate(bad)
        bad=copy.deepcopy(self.data);bad["schema"]=2
        with self.assertRaisesRegex(ValueError,"schema"):validate(bad)

if __name__=="__main__":unittest.main()
