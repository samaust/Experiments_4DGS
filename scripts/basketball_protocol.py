"""User-authorized Basketball variant retaining cameras passing the 20% gate.

Raw input inventory remains 34 videos. Preserve IDs; never renumber cameras.
Training accounting retains the original vru-basketball-dg ledger key.
"""
PROTOCOL = 'basketball-intrinsic20-no-camera19/v1'
INTRINSIC_LIMIT = .20
EXCLUDED = (4, 5, 8, 11, 15, 16, 17, 18, 19, 20, 23)
HELD_OUT = (0, 10, 30)
CAMERAS = tuple(c for c in range(34) if c not in EXCLUDED)
TRAINING = tuple(c for c in CAMERAS if c not in HELD_OUT)
FIT_FRAMES = (50, 75, 100, 125, 149)


def manifest_protocol():
    return dict(schema=PROTOCOL, cameras=list(CAMERAS), training_cameras=list(TRAINING),
                held_out_cameras=list(HELD_OUT), excluded_cameras=list(EXCLUDED),
                exclusion_reason='User excluded 20% intrinsic failures, previously removed camera 5, and explicitly removed camera 19 after pose instability.',
                intrinsic_limit=INTRINSIC_LIMIT,
                source_camera_ids_preserved=True, images=len(CAMERAS)*50, training_images=len(TRAINING)*50,
                held_out_images=len(HELD_OUT)*50, frame_ids=list(range(50)),
                calibration_fit=list(range(50,150)), selection=list(range(150,200)),
                validation=list(range(200,250)), training_ledger_scene='vru-basketball-dg')
