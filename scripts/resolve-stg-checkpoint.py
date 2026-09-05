"""Resolve one downloaded STG lite run without executing its saved cfg_args.

Print shell-quoted assignments for the experiment guide. No files are modified.
"""
import argparse
import ast
import json
from pathlib import Path
import re
import shlex


def resolve(root, profile_path, start_frame=None):
    configs = sorted(root.rglob("cfg_args"))
    if len(configs) != 1:
        raise ValueError("Expected exactly one cfg_args beneath the extracted archive")
    model = configs[0].parent.resolve()
    expression = ast.parse(configs[0].read_text(), mode="eval").body
    if not (isinstance(expression, ast.Call) and isinstance(expression.func, ast.Name)
            and expression.func.id == "Namespace" and not expression.args):
        raise ValueError("Expected a literal Namespace(...) in cfg_args")
    saved = {}
    for item in expression.keywords:
        if item.arg is None:
            raise ValueError("Expanded keyword arguments are not supported")
        saved[item.arg] = ast.literal_eval(item.value)
    profile = json.loads(profile_path.read_text())
    plys = sorted((model / "point_cloud").glob("iteration_*/point_cloud.ply"))
    if not plys:
        raise ValueError("Missing point_cloud/iteration_*/point_cloud.ply")
    ply = max(plys, key=lambda path: int(path.parent.name.removeprefix("iteration_")))
    with ply.open("rb") as stream:
        header = stream.read(10240).split(b"end_header\n", 1)[0]
    for field in ("motion_0", "motion_8", "omega_0", "omega_3", "trbf_center", "trbf_scale"):
        if not re.search(rb"property\s+\w+\s+" + field.encode() + rb"\r?\n", header):
            raise ValueError("Not the expected STG lite temporal PLY: missing " + field)
    duration = saved.get("duration", profile.get("duration"))
    resolution = saved.get("resolution", profile.get("resolution"))
    if type(duration) is not int or not 1 <= duration <= 300:
        raise ValueError("Missing or invalid capture duration")
    if type(resolution) is not int or (resolution != -1 and resolution <= 0):
        raise ValueError("Missing or invalid saved resolution")
    source = str(saved.get("source_path", "")).replace("\\", "/").rstrip("/")
    offset = re.search(r"(?:^|/)colmap_(\d+)$", source)
    if start_frame is not None and (type(start_frame) is not int or start_frame < 0):
        raise ValueError("Invalid explicit start frame")
    if offset:
        start = int(offset.group(1))
        if start_frame is not None and start_frame != start:
            raise ValueError("Explicit start frame conflicts with saved source_path")
    elif start_frame is not None:
        start = start_frame
    else:
        raise ValueError("Cannot establish temporal window from saved source_path; provide --start-frame with documented provenance")
    if start + duration > 300:
        raise ValueError("Saved temporal window exceeds this capture's 300 frames")
    cameras = model / "cameras.json"
    if not cameras.is_file():
        raise ValueError("Missing matching cameras.json for browser inspection")
    return {
        "STG_MODEL": str(model), "STG_PLY": str(ply), "STG_CAMERAS": str(cameras),
        "STG_ITERATION": int(ply.parent.name.removeprefix("iteration_")),
        "STG_DURATION": duration, "STG_RESOLUTION": resolution,
        "STG_START": start, "STG_END": start + duration,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--start-frame", type=int, help="Explicit window assumption when the release omits its source path")
    args = parser.parse_args()
    try:
        values = resolve(args.root, args.profile, args.start_frame)
    except (ValueError, OSError, SyntaxError, TypeError) as error:
        parser.exit(1, "Checkpoint inspection failed: " + str(error) + "\n")
    for name, value in values.items():
        print("export " + name + "=" + shlex.quote(str(value)))
