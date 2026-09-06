"""Render a diagnostic z-buffered point thumbnail, not a Gaussian benchmark."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

from freetimegs_initialization import digest, load_dense_cloud
from stg_scene import SelfCapScene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--cloud', type=Path, required=True)
    parser.add_argument('--frame-id', type=int, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix('.json').exists():
        parser.error('choose new output paths')
    scene = SelfCapScene(args.manifest)
    xyz, rgb, evidence = load_dense_cloud(args.cloud, scene, args.frame_id)
    calibration = scene.cameras['0015']
    R, T = np.asarray(calibration['world_to_camera_R']), np.asarray(calibration['world_to_camera_T'])
    camera = xyz @ R.T + T
    visible = np.isfinite(camera).all(1) & (camera[:, 2] > 0)
    camera, rgb = camera[visible], rgb[visible]
    projected = camera @ np.asarray(calibration['K']).T
    # Quarter-resolution diagnostic, explicitly separate from native previews.
    width, height = round(calibration['width']/4), round(calibration['height']/4)
    scale = np.array([width/calibration['width'], height/calibration['height']])
    pixels = np.floor(projected[:, :2] / projected[:, 2:3] * scale).astype(np.int64)
    inside = (pixels >= 0).all(1) & (pixels[:, 0] < width) & (pixels[:, 1] < height)
    pixels, rgb, depths = pixels[inside], rgb[inside], camera[inside, 2]
    order = np.argsort(depths, kind='stable')
    flat = pixels[:, 1] * width + pixels[:, 0]
    _, first = np.unique(flat[order], return_index=True)
    selected = order[first]
    image = np.zeros((height*width, 3), dtype=np.uint8)
    image[flat[selected]] = (rgb[selected]*255).round().astype(np.uint8)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image.reshape(height, width, 3)).save(args.output)
    report = dict(scope='quarter-resolution z-buffered point diagnostic, not Gaussian evaluation',
        manifest_sha256=scene.sha256, cloud_evidence=evidence, camera='0015',
        frame_id=args.frame_id, width=width, height=height,
        occupied_pixels=len(selected), total_pixels=width*height, image_sha256=digest(args.output),
        heldout_images_loaded=False)
    args.output.with_suffix('.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
