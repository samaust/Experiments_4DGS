"""Reanalyze saved SIFT/LK evidence under Plan 024's common global estimator."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

from sync_timing import robust_offsets


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    source=json.loads(a.source.read_text())
    expected='21139df550a6fa72c9730d4c658a58464ce00be9ff268380ab433c3d9471e74f'
    if source['calibration_sha256']!=expected:raise ValueError('calibration mismatch')
    ids=[str(i) for i in range(34)]
    saved={(e['a'],e['b']):e for e in source['edges']}
    edges, pairs=[],[]
    for i,j in itertools.combinations(range(34),2):
        e=saved.get((i,j))
        reasons=['outside-saved-pair-selection'] if e is None else []
        if e is not None and not e['passed']:
            reasons=e.get('refined',e['integer'])['blockers'] or ['saved-gate-failed']
        if not reasons:
            # Saved lag means b(frame_a+lag) matches a(frame_a): o_b-o_a=lag/fps.
            edges.append(dict(i=str(i),j=str(j),delta_seconds=-e['lag']/25))
        pairs.append(dict(i=str(i),j=str(j),accepted=not reasons,rejection_reasons=reasons,
                          learned_rejection_reasons=['released-VisualSync-matching-preprocessor-incomplete']))
    fit=robust_offsets(ids,'1',edges,huber_seconds=.01)
    removal=[]
    for e in edges:
        reduced=robust_offsets(ids,'1',[x for x in edges if x is not e],huber_seconds=.01)
        common=set(fit['coverage'])&set(reduced['coverage'])
        removal.append(dict(i=e['i'],j=e['j'],lost_coverage=sorted(set(fit['coverage'])-common),
            maximum_change_seconds=max(abs(fit['offset_seconds'][c]-reduced['offset_seconds'][c]) for c in common)))
    import networkx as nx
    g=nx.Graph();g.add_nodes_from(ids)
    directed={}
    for e in edges:
        g.add_edge(e['i'],e['j']);directed[e['i'],e['j']]=e['delta_seconds'];directed[e['j'],e['i']]=-e['delta_seconds']
    cycles=[dict(cameras=c,closure_seconds=sum(directed[i,j] for i,j in zip(c,c[1:]+c[:1])))
            for c in nx.cycle_basis(g)]
    result=dict(schema='basketball-common-graph-audit/v1',kind='saved-fit-diagnostic',
        source_path=str(a.source),source_sha256=hashlib.sha256(a.source.read_bytes()).hexdigest(),
        calibration_sha256=expected,fit_source_frames=[50,149],pairs=pairs,global_fit=fit,
        cycle_basis=cycles,leave_one_edge_out=removal,
        learned_global_fit=robust_offsets(ids,'1',[],huber_seconds=.01),
        huber_seconds=.01,provenance='Same estimator for saved evidence and empty unavailable learned evidence; no new pair fitting or gate relaxation.',
        uncertainty='Marginal uncertainty and cross-window repeatability unverified; graph alone is not timing truth.',
        approved_for_reconstruction=False,script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    with a.output.open('x') as stream:json.dump(result,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(pairs=len(pairs),accepted=len(edges),coverage=len(fit['coverage']),bridges=len(fit['bridges']))))


if __name__=='__main__':main()
