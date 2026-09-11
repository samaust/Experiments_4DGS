# Why the parent fragmented, and what C and D require

The [shared code provenance](../basketball-code-provenance.md) explains the
research papers, upstream repositories, and local additions behind this workflow
and the dense initialization studies.

The results point to missing training frames as the main reason the parent failed
during the crossing. C and D both restore those frames. In the user's assessment
on 2026-09-11, A and B provide minimal improvement and are rejected as solutions;
C and D noticeably repair the issue and are approved solutions. They look
different, but no winner has been selected between them. This records the user's
arm-level judgment, without claiming a separate visual assessment for every
recipe, seed, and camera.

The lifetime bug was real, but B's limited improvement shows that correcting it
alone did not solve this event.

The **Parent 50k** had deliberately been trained with a gap:

- It used 45 of the 50 frames from each of the 30 training cameras.
- Frames **20–24**, covering **[0.80, 1.00) seconds**, were excluded from every
  training camera.
- Those images existed; the experiment withheld them to test reconstruction
  through an unseen time interval.

Consequently, the model received image feedback before and after the crossing,
but none during those five frames. That was an intentional interpolation
challenge. For a workflow intended to reconstruct the recorded sequence
faithfully, it removed useful evidence precisely where the motion was difficult.
The exclusion is enforced by the [scene adapter](../../../scripts/basketball_scene.py)
and [training-key selection](../../../scripts/sync_timing.py).

Each Gaussian has its own position, velocity, temporal center, and visibility
width. The model can fit observed frames without those individual moving pieces
forming a coherent player throughout an unobserved interval. Incorrect positions
and overlapping or missing contributions can then appear as fragments during
playback. This is the supported explanation for the failure; we have not isolated
which individual Gaussians produced each fragment. The comparison establishes
the effective intervention more directly than the exact contribution of each
motion or visibility error.

There was also a duration-handling defect. The value `-1`, meaning "automatically
determine the setting," remained in the configuration used by the duration
penalty. That penalty therefore encouraged all positive durations to shrink.
Learned durations could fall below the renderer's `0.02` floor, where image
feedback could no longer directly adjust their width. This made temporal
behavior harder to learn, but the comparison shows it was not the only obstacle.
The native optimization step is bound by the [training adapter](../../../scripts/freetimegs_training.py).

**C fixes the missing supervision.** It starts from the matching 50k parent,
adds frames 20–24 from the same 30 training cameras, and trains the model for
another 20,000 updates, ending at update 70,000.

That changes the training set from **1,350 to 1,500 images**. The added images let
the existing image losses correct Gaussian positions, motion, visibility, colors,
and other learned parameters during the crossing itself. C retains the original
duration behavior, including the defect described above.

C requires no new capture, player tracking, masks, or reconstructed geometry in
this experiment. Its changes are to training-image selection and subsequent
optimization. Cameras 0, 10, 20, and 30 remain excluded, so the improvement also
appears from viewpoints the model was not trained on. The selection is
implemented in the [Plan 028 training adapter](../../../scripts/basketball_crossing_train.py)
as `--training-policy all-times --lifetime-policy original`.

**D does everything C does, plus the duration repair.** It uses the same 1,500
images and the same 20,000 additional updates, with three extra changes:

1. Resolve the automatic duration setting to **0.2**, from the frozen initializer
   metadata, requiring a finite, positive value.
2. Keep learned durations at or above the existing **0.02 rendering floor**,
   when starting the branch and after every complete training step. The stored
   log-duration boundary is chosen to exponentiate safely to at least `0.02`.
3. Clear Adam's accumulated moments only for duration entries raised to that
   floor, retaining optimizer step counters.

**0.2 is a threshold above which the duration penalty applies. It does not pull
every duration toward 0.2.** For a positive raw duration `d`, the penalty is
proportional to `max(d - threshold, 0)^2`. Durations between approximately `0.02`
and `0.2` remain learnable without that penalty. The repair removes the erroneous
pressure to shrink every duration and keeps the parameter out of the renderer's
flat-gradient region. See the [repair implementation](../../../scripts/basketball_crossing_repair.py).
D selects `--training-policy all-times --lifetime-policy repaired`.

Both arms retain the initializer and point count, native rendering equations,
other losses and weights, and the absolute 70,000-update schedule. Relocation
ends at update 63,000. Each experimental branch restores the matching parent
model and training state before applying its declared changes and starts a fresh
dedicated sampler with the trajectory's seed.

The recorded gap metrics give D a modest numerical advantage:

| Frames 20–24, held-out cameras | C | D |
|---|---:|---:|
| Motion-pixel MAE, lower is better | 0.04694 | 0.04574 |
| Motion-crop LPIPS, lower is better | 0.05782 | 0.05629 |

These are equal averages across both recipes, three seeds, and four held-out
cameras. D is about **2.6% better on these two measures**, which supports a small
numerical edge without establishing a clear visual winner. The values come from
the gap summaries in [results.json](results.json); the underlying per-frame
metrics are in the [metric manifest](../../../.local/basketball-crossing-repair/metrics/records.json).

For a **future workflow**, the requirements are:

| Requirement | C workflow | D workflow |
|---|---|---|
| Training coverage | Include the recorded frames throughout the motion interval | Same |
| Duration logic | Retain original behavior | Resolve the automatic setting and enforce the trainable floor |
| Existing failed checkpoint | Continue training with the missing frames included | Same, applying the duration repair before continuation |
| Rendering afterward | Render the updated checkpoint normally | Render the updated checkpoint normally |

For new training, include the full recorded time interval from the outset and
reserve cameras for evaluation. There is no need to deliberately create a
deficient 50k parent first. However, **the measured result here used 50k→70k
continuation**; we have not established the minimum training budget or the exact
result of starting with these policies from update zero.

For D, preserve consistent time units. Here, `t = frame/50`: `0.02` corresponds
to a 40 ms temporal width, and `0.2` to 400 ms. These are Gaussian widths, not
hard visibility durations. A different clip length needs an explicit conversion
and a duration setting resolved from its initializer metadata. If retaining the
same physical width, convert it into that clip's normalized time rather than
assuming the same numeric constant represents the same duration in seconds.

Both approved solutions require training images that cover the event and enough
optimization to use them. **If those frames genuinely do not exist, neither C nor
D has demonstrated a solution for that missing interval.** Their success here
establishes reconstruction with added temporal supervision and held-out cameras;
it does not establish reconstruction through an unseen temporal gap. Future
validation should include playback and frame inspection of the crossing and
player detail elsewhere, alongside metrics from held-out cameras.

The [report](report.md), [status](status.md), and
[comparison videos and crops](../../../.local/basketball-crossing-repair/videos/artifacts.json)
provide the associated study records.
