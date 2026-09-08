# Actual saved-image inspection — 2026-09-08

The implementation agent opened all 17 sheets indexed below with the image-viewing tool. This inspection covers full frames 4120/4150/4179, every adjacent transition in 4120–4122, 4148–4152 and 4177–4179, all four fixed crops in each window, and sweep poses 0/10/19 for all four methods. It does **not** claim full-sequence playback, quantitative flicker measurement or freshly rendered evidence.

[The index](inspection.json) binds every sheet and original image to SHA-256, exact frame/time and fixed crop coordinates. [The offline selector](inspection.html) exposes every original held-out image, synchronized frame selection, named original-pixel crops with zoom, and a separate 20-pose sweep selector. Sheet tiles above 480 pixels wide are downsampled with Pillow/Lanczos; smaller crops retain original pixels. The viewing tool may further scale large sheets to fit its display. Use the original links/selector for independent native-resolution inspection.

Crop selection remains camera 0015/frame 4150, hash `e753fcb2588fca2b97da375e4bdd79a79944419e96b5913e6ac81079a7987c1d`, as in the [fixed configuration](../../../configs/detail-crops.selfcap-dance1.json). Bounds are left/top/right/bottom with exclusive right/bottom: hair_motion [330,300,1020,820], face_hair_boundary [620,470,900,750], hands_body_boundary [610,830,1030,1061], static_book_text [850,350,1030,515]. Crops were not moved for any model. The named face crop contains shoulder/hair rather than the face in the early window; the early hand crop mostly shows shorts/thighs. Hair partially occludes the book region in early/end reference frames, so this region is not universally static visible background.

## Adjacent observations

**4120→4121 and 4121→4122:** Reference shoulder and torso boundaries remain defined while hair and the moving hand show real motion blur. Lite and Full sustain a broad translucent head/shoulder smear across both transitions; shelf lines remain visible through areas that should be foreground, and shorts/thigh edges look widened or displaced. This persistent error is more extensive than reference blur. FreeTimeGS retains a more coherent silhouette and shorts boundary but face, hair and forearm remain smeared; it is not sharp-motion recovery. ATGS has fragmented/streaked shoulder/torso appearance in all three images and distorted thigh edges. The book crop changes partly because real hair crosses it; STG adds broader foreground wash. ATGS lettering is comparatively recognizable locally despite its foreground failure.

**4148→4149, 4149→4150, 4150→4151 and 4151→4152:** Reference hair fans upward and changes shape; individual streaks are blurred, while facial contours, shoulder and fingers remain distinguishable. All methods replace much of the fan with a diffuse brown mass. Lite and Full keep double/soft face contours and lose face/hair separation throughout these four transitions. FreeTimeGS has clearer shoulder/face structure, especially 4151–4152, but 4148–4150 faces and the hair fan are still excessively blurred. ATGS face boundaries change irregularly (more face visible by 4151), with smeared cheek/mouth detail and noisy or ghosted shoulder boundaries. No cause such as synchronization, representation, or incomplete optimization can be isolated by these images alone. All methods oversmooth fingers and soften limb boundaries; FreeTimeGS shows more distinct fingers locally. Static books remain broadly stable in position across this window, but small lettering is softened or changed in every model; ATGS retains some recognizable vertical lettering better than its aggregate ranking suggests.

**4177→4178 and 4178→4179:** The reference face/body pose changes slowly, with fine hair still moving. Predicted faces are much more recognizable than in the early/midpoint windows, but Lite and Full remain soft around eyes, hairline and shoulder, and ATGS retains distorted/doubled chin/mouth and diffuse hair/body boundaries across both transitions. FreeTimeGS gives the clearest sampled facial structure among the methods here, while its hands remain smooth. Its book/shelf region shows a broad pale veil/haze, including where the reference retains high-contrast lettering and finer hair. STG also softens the books; ATGS’s lettering can be more legible locally. These slowly changing samples do not establish a global temporal stability ranking.

Across the inspected full frames, shelf layout and body pose are recognizable in all methods; fast-motion foreground detail is the common limitation. Full’s aggregate gain over Lite does not imply a consistently sharper face in every inspected crop. FreeTimeGS’s aggregate lead is supported by some stronger foreground boundaries, with local background and motion defects still present. ATGS’s local lettering advantage is insufficient to offset its measured aggregate/foreground disadvantages for this profile.

## Frozen-time views

Poses 0, 10 and 19 use the same normalized time **0.5002984601802468**, source midpoint frame **4150**, shared 20-pose metadata, start camera 0015/end 0014 and camera-0015 intrinsics. Pose 0 corresponds to the held-out starting viewpoint. The interior pose 10 has no ground-truth image: the comparison supports visible view consistency only. Pose 19 remains rendered with shared intrinsics, so no unperformed matched-reference fidelity claim is made there.

All methods retain a recognizable crouched person, shelves and floor as viewpoint changes. The camera framing shifts downward toward pose 19, clipping much of the head in every method; this is shared framing, not evidence that a model loses its head. STG/ATGS foreground and floor look softer/streakier, while FreeTimeGS shows more coherent hand/body and floor detail at these sampled poses. The same hair blur persists wherever the head is visible. Three poses cannot establish complete-path consistency or unseen-surface accuracy.

The prior analyzer’s adjacent MAE contains real motion and cannot rank flicker; its blinds crop does not apply to this scene. No combined score, new temporal metric, long-sequence claim, equal-compute comparison or full-paper convergence claim is made.

## Viewed sheet and time index

- [full-4120-4179.png](../../../.local/runs/selfcap-evidence-20260908/sheets/full-4120-4179.png) — viewed; frames/poses [4120, 4150, 4179]; scale 0.253968.
- [full-4120-4122.png](../../../.local/runs/selfcap-evidence-20260908/sheets/full-4120-4122.png) — viewed; frames/poses [4120, 4121, 4122]; scale 0.253968.
- [hair_motion-4120-4122.png](../../../.local/runs/selfcap-evidence-20260908/sheets/hair_motion-4120-4122.png) — viewed; frames/poses [4120, 4121, 4122]; scale 0.695652.
- [face_hair_boundary-4120-4122.png](../../../.local/runs/selfcap-evidence-20260908/sheets/face_hair_boundary-4120-4122.png) — viewed; frames/poses [4120, 4121, 4122]; scale 1.000000.
- [hands_body_boundary-4120-4122.png](../../../.local/runs/selfcap-evidence-20260908/sheets/hands_body_boundary-4120-4122.png) — viewed; frames/poses [4120, 4121, 4122]; scale 1.000000.
- [static_book_text-4120-4122.png](../../../.local/runs/selfcap-evidence-20260908/sheets/static_book_text-4120-4122.png) — viewed; frames/poses [4120, 4121, 4122]; scale 1.000000.
- [full-4148-4152.png](../../../.local/runs/selfcap-evidence-20260908/sheets/full-4148-4152.png) — viewed; frames/poses [4148, 4149, 4150, 4151, 4152]; scale 0.253968.
- [hair_motion-4148-4152.png](../../../.local/runs/selfcap-evidence-20260908/sheets/hair_motion-4148-4152.png) — viewed; frames/poses [4148, 4149, 4150, 4151, 4152]; scale 0.695652.
- [face_hair_boundary-4148-4152.png](../../../.local/runs/selfcap-evidence-20260908/sheets/face_hair_boundary-4148-4152.png) — viewed; frames/poses [4148, 4149, 4150, 4151, 4152]; scale 1.000000.
- [hands_body_boundary-4148-4152.png](../../../.local/runs/selfcap-evidence-20260908/sheets/hands_body_boundary-4148-4152.png) — viewed; frames/poses [4148, 4149, 4150, 4151, 4152]; scale 1.000000.
- [static_book_text-4148-4152.png](../../../.local/runs/selfcap-evidence-20260908/sheets/static_book_text-4148-4152.png) — viewed; frames/poses [4148, 4149, 4150, 4151, 4152]; scale 1.000000.
- [full-4177-4179.png](../../../.local/runs/selfcap-evidence-20260908/sheets/full-4177-4179.png) — viewed; frames/poses [4177, 4178, 4179]; scale 0.253968.
- [hair_motion-4177-4179.png](../../../.local/runs/selfcap-evidence-20260908/sheets/hair_motion-4177-4179.png) — viewed; frames/poses [4177, 4178, 4179]; scale 0.695652.
- [face_hair_boundary-4177-4179.png](../../../.local/runs/selfcap-evidence-20260908/sheets/face_hair_boundary-4177-4179.png) — viewed; frames/poses [4177, 4178, 4179]; scale 1.000000.
- [hands_body_boundary-4177-4179.png](../../../.local/runs/selfcap-evidence-20260908/sheets/hands_body_boundary-4177-4179.png) — viewed; frames/poses [4177, 4178, 4179]; scale 1.000000.
- [static_book_text-4177-4179.png](../../../.local/runs/selfcap-evidence-20260908/sheets/static_book_text-4177-4179.png) — viewed; frames/poses [4177, 4178, 4179]; scale 1.000000.
- [sweep-0-19.png](../../../.local/runs/selfcap-evidence-20260908/sheets/sweep-0-19.png) — viewed; frames/poses [0, 10, 19]; scale 0.253968.

| Frame | timestamp_seconds | normalized_time |
| --- | ---: | ---: |
| 4120 | 68.66740551053469 | 0.012362351198530078 |
| 4121 | 68.68407217720136 | 0.02862688816458638 |
| 4122 | 68.70073884386802 | 0.044891425130642676 |
| 4148 | 69.13407217720136 | 0.4677693862481342 |
| 4149 | 69.15073884386803 | 0.4840339232141905 |
| 4150 | 69.16740551053469 | 0.5002984601802468 |
| 4151 | 69.18407217720136 | 0.516562997146303 |
| 4152 | 69.20073884386802 | 0.5328275341123594 |
| 4177 | 69.61740551053468 | 0.9394409582637807 |
| 4178 | 69.63407217720136 | 0.9557054952298509 |
| 4179 | 69.65073884386803 | 0.9719700321959073 |
