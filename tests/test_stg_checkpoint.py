"""Exercise metadata selection with small synthetic checkpoints, without CUDA."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "checkpoint", Path(__file__).resolve().parents[1] / "scripts/resolve-stg-checkpoint.py")
checkpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpoint)


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.model = self.root / "download with spaces" / "scene"
        self.model.mkdir(parents=True)
        (self.model / "cfg_args").write_text(
            "Namespace(source_path='/old/location/colmap_12', duration=50, resolution=2)")
        (self.model / "cameras.json").write_text("[]")
        self.profile = self.root / "profile.json"
        self.profile.write_text(json.dumps({"duration": 25, "resolution": 4}))
        self.add_ply(9000)
        self.add_ply(25000)

    def add_ply(self, iteration):
        path = self.model / "point_cloud" / ("iteration_" + str(iteration)) / "point_cloud.ply"
        path.parent.mkdir(parents=True)
        fields = ["motion_0", "motion_8", "omega_0", "omega_3", "trbf_center", "trbf_scale"]
        path.write_text("ply\nformat ascii 1.0\nelement vertex 0\n" +
                        "".join("property float " + field + "\n" for field in fields) +
                        "end_header\n")

    def test_saved_window_and_numeric_iteration_selection(self):
        values = checkpoint.resolve(self.root, self.profile)
        self.assertEqual(values["STG_ITERATION"], 25000)
        self.assertEqual(values["STG_START"], 12)
        self.assertEqual(values["STG_END"], 62)
        self.assertEqual(values["STG_DURATION"], 50)
        self.assertEqual(values["STG_RESOLUTION"], 2)
        self.assertEqual(values["STG_MODEL"], str(self.model))

    def test_profile_fallback_and_windows_saved_path(self):
        (self.model / "cfg_args").write_text("Namespace(source_path='C:\\\\data\\\\colmap_0')")
        values = checkpoint.resolve(self.root, self.profile)
        self.assertEqual(values["STG_START"], 0)
        self.assertEqual(values["STG_DURATION"], 25)

    def test_rejects_executable_saved_settings(self):
        (self.model / "cfg_args").write_text("Namespace(duration=__import__('os').getcwd())")
        with self.assertRaises(ValueError):
            checkpoint.resolve(self.root, self.profile)

    def test_rejects_ambiguous_models(self):
        other = self.root / "another"
        other.mkdir()
        (other / "cfg_args").write_text("Namespace()")
        with self.assertRaisesRegex(ValueError, "exactly one"):
            checkpoint.resolve(self.root, self.profile)

    def test_rejects_missing_temporal_fields(self):
        ply = self.model / "point_cloud/iteration_25000/point_cloud.ply"
        ply.write_text("ply\nformat ascii 1.0\nelement vertex 0\nend_header\n")
        with self.assertRaisesRegex(ValueError, "temporal PLY"):
            checkpoint.resolve(self.root, self.profile)

    def test_rejects_unknown_or_out_of_range_time_window(self):
        for source in ["/old/scene", "/old/colmap_299"]:
            (self.model / "cfg_args").write_text(
                "Namespace(source_path=" + repr(source) + ", duration=50, resolution=2)")
            with self.assertRaises(ValueError):
                checkpoint.resolve(self.root, self.profile)


if __name__ == "__main__":
    unittest.main()
