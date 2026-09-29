# Candidate017 preliminary census correction

The first fresh-preflight script stopped before writing any clearance or starting a launch. Its substring scan matched the Codex sandbox wrapper because that wrapper's command line carried the inline census script text containing a Candidate017 workload marker. This is a census-script false positive, not evidence of a Plan049 workload.

The replacement census distinguishes the current observer and its ancestor tool-wrapper chain from other processes, and tests exact argv elements and Plan049 ownership environment fields for matching workloads. It still counts every visible process and thread for capacity, records the observer chain, and stops on unreadable census entries or an actual matching workload. No source, plan, attempt index, output path, or runtime state was changed by the rejected preflight.
