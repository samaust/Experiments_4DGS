# Partial 5,000-update comparison

This snapshot contains all 30 verified historical results and the six new dense
5,000-update results. The 24 later dense results remain pending; this is not the
completed Plan 027 report. Both recipes continue unchanged to 50,000 updates.

See [statistics](statistics.json), [curves](curves.csv), and [artifact index](artifact-index.json).
The training-time endpoint axis includes the complete charged training segment,
including checkpoint saving and cleanup. GPU accounting includes completed jobs
only; the active continuation is not yet charged in this snapshot. Initialization
cost is separate. Standalone CPU postprocessing is excluded from GPU-job accounting.

All three seeds are retained. Temporal interpolation covers one held-out time block.
Initialization changes point count, geometry, and motion together. Court metrics
alone cannot establish better player reconstruction. The Plan 026 visual rejection
remains unchanged; matched trained-view inspection is still pending.
