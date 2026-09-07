"""User-authorized Basketball variant excluding physical camera 5.

Raw input inventory remains 34 videos. Preserve IDs; never renumber cameras.
Training accounting retains the original vru-basketball-dg ledger key.
"""
PROTOCOL = 'basketball-no-camera5/v1'
EXCLUDED = (5,)
HELD_OUT = (0, 10, 20, 30)
CAMERAS = tuple(c for c in range(34) if c not in EXCLUDED)
TRAINING = tuple(c for c in CAMERAS if c not in HELD_OUT)
FIT_FRAMES = (50, 75, 100, 125, 149)


def manifest_protocol():
    return dict(schema=PROTOCOL, cameras=list(CAMERAS), training_cameras=list(TRAINING),
                held_out_cameras=list(HELD_OUT), excluded_cameras=list(EXCLUDED),
                exclusion_reason='User explicitly removed camera 5 after intrinsic instability.',
                source_camera_ids_preserved=True, images=1650, training_images=1450,
                held_out_images=200, frame_ids=list(range(50)),
                calibration_fit=list(range(50,150)), selection=list(range(150,200)),
                validation=list(range(200,250)), training_ledger_scene='vru-basketball-dg')
