"""Fit and backtest native-loss asymptotes using only recorded Plan 026 losses."""
import csv
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', '/tmp/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import least_squares
from scipy.signal import savgol_filter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/experiments/basketball-dense-temporal/loss-extrapolation'
ARMS = ('stg-full', 'freetimegs-sparse')


def predict(kind, t, par):
    c, a, rate = par
    if kind == 'power':
        return c + a * (np.asarray(t) / 20000) ** (-rate)
    return c + a * np.exp(-(np.asarray(t) - 20000) / (10000 * rate))


def fit(kind, x, y):
    # Multiple starts guard against local minima in these nonlinear fits.
    results = []
    for fraction in (0, .5, .9):
        for rate in (.25, 1, 4):
            initial = [float(y.min()) * fraction, max(float(y.max()-y.min()*fraction), .001), rate]
            result = least_squares(lambda p: predict(kind, x, p)-y, initial,
                bounds=([0, 0, .001], [float(y.min()), 2, 100]),
                max_nfev=10000, ftol=1e-12, xtol=1e-12, gtol=1e-12)
            if result.success:
                results.append(result)
    if not results:
        raise RuntimeError('No converged fit')
    result = min(results, key=lambda r: np.sum(r.fun**2))
    return result.x


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    result = {'block_updates': 500, 'primary_fit_start': 20000,
              'validation': 'fit 20000–40000; predict untouched 40001–50000 block means',
              'constraints': 'c >= 0, a >= 0, decay rate > 0; constraints are modeling assumptions',
              'uncertainty': 'model/window and per-seed sensitivity ranges, not confidence intervals',
              'arms': {}}
    fig, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    csv_rows = []
    for row, arm in enumerate(ARMS):
        series, sources = [], []
        for seed in range(3):
            path = ROOT / '.local/basketball-dense-temporal/training' / f'{arm}-seed{seed}' / 'loss.jsonl'
            records = [json.loads(line) for line in path.open()]
            assert [r['iteration'] for r in records] == list(range(5001, 50001))
            values = np.array([r['loss'] for r in records])
            assert np.isfinite(values).all()
            series.append(values.reshape(-1, 500).mean(axis=1))
            sources.append({'path': str(path.relative_to(ROOT)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        series = np.array(series)
        x = np.arange(5250.5, 50000, 500)
        y = series.mean(axis=0)
        tail = x >= 20000
        train = tail & (x < 40000)
        test = x > 40000
        backtest = {}
        for kind in ('exponential', 'power'):
            par = fit(kind, x[train], y[train])
            backtest[kind] = {'parameters': par.tolist(), 'rmse': float(np.sqrt(np.mean((predict(kind,x[test],par)-y[test])**2)))}
        kind = min(backtest, key=lambda k: backtest[k]['rmse'])
        par = fit(kind, x[tail], y[tail])
        candidates = []
        for start in (10000, 20000, 30000):
            for model in ('exponential', 'power'):
                p = fit(model, x[x>=start], y[x>=start])
                candidates.append({'model': model, 'start': start, 'parameters': p.tolist(), 'asymptote': float(p[0]),
                                   'at_100000': float(predict(model,100000,p))})
        seed_fits = [fit(kind,x[tail],ys[tail]).tolist() for ys in series]
        current = float(y[-4:].mean())
        endpoint = float(predict(kind,50000,par))
        forecasts = {str(t): float(predict(kind,t,par)) for t in (50000,70000,100000,200000)}
        floors = [c['asymptote'] for c in candidates]
        result['arms'][arm] = dict(sources=sources, selected_model=kind, parameters=par.tolist(),
            last_2000_observed_mean=current, fitted_50000=endpoint, forecasts=forecasts,
            asymptote=float(par[0]), remaining_reduction_from_fitted_50000=float(endpoint-par[0]),
            remaining_percent_from_fitted_50000=float(100*(endpoint-par[0])/endpoint),
            backtest=backtest, sensitivity=candidates, asymptote_sensitivity_range=[min(floors),max(floors)],
            seed_parameters=seed_fits, seed_asymptote_range=[min(p[0] for p in seed_fits),max(p[0] for p in seed_fits)])
        for t, mean, *seeds in zip(x,y,*series):
            csv_rows.append([arm,t,mean,*seeds,float(predict(kind,t,par)) if t>=20000 else ''])
        for ax in axes[row]:
            for seed, ys in enumerate(series):
                ax.plot(x,ys,alpha=.25,lw=.65,color='gray',label='500-update means, each seed' if seed==0 else None)
            ax.plot(x,y,color='#2463a5',lw=.6,alpha=.3)
            ax.plot(x,savgol_filter(y,11,2),color='#2463a5',lw=1.5,label='Smoothed three-seed mean (observed only)')
            grid = np.linspace(20000,50000,200)
            ax.plot(grid,predict(kind,grid,par),color='#d34d26',lw=2.5,label=f'Smooth {kind} fit')
            ax.set_ylabel('Native training loss')
            ax.set_xlabel('Total optimizer updates')
            ax.grid(alpha=.2)
            ax.ticklabel_format(axis='x',style='sci',scilimits=(3,3))
        axes[row,0].set_title(f'{arm}: observed losses and fitted tail')
        ax=axes[row,1]
        grid=np.linspace(50000,200000,300)
        alternatives=np.array([predict(c['model'],grid,c['parameters']) for c in candidates])
        ax.fill_between(grid,alternatives.min(axis=0),alternatives.max(axis=0),color='#d34d26',alpha=.14,label='Model/window sensitivity (not CI)')
        ax.plot(grid,predict(kind,grid,par),'--',color='#d34d26',lw=2,label='Conditional extrapolation')
        ax.axhline(par[0],color='#39803c',ls=':',lw=2,label=f'Fitted asymptote = {par[0]:.5f}')
        ax.axvline(50000,color='black',alpha=.3,lw=1)
        ax.set_xlim(20000,200000)
        ax.set_ylim(min(float(par[0]),float(alternatives.min()))*.98,float(y[x>=20000].max())*1.03)
        equation = (f'L(t) = {par[0]:.6f} + {par[1]:.6f}(t/20000)^(-{par[2]:.4f})'
                    if kind=='power' else f'L(t) = {par[0]:.6f} + {par[1]:.6f} exp(-(t-20000)/{10000*par[2]:.1f})')
        ax.set_title(equation,fontsize=10)
        ax.legend(fontsize=8,loc='upper right')
        axes[row,0].legend(fontsize=8)
    fig.suptitle('Plan 026 native loss: fitted trends and conditional long-run estimates\nDifferent objectives: absolute losses are not a reconstruction-quality comparison',fontsize=13)
    fig.savefig(OUT/'native-loss-asymptotes.png',dpi=180)
    fig.savefig(OUT/'native-loss-asymptotes.pdf')
    (OUT/'fits.json').write_text(json.dumps(result,indent=2)+'\n')
    with (OUT/'block-means.csv').open('w') as f:
        writer=csv.writer(f,lineterminator='\n');writer.writerow(['arm','update_center','mean','seed0','seed1','seed2','fitted_tail']);writer.writerows(csv_rows)
    print(json.dumps({arm:{k:v for k,v in r.items() if k not in ('sources','sensitivity','seed_parameters')} for arm,r in result['arms'].items()},indent=2))


if __name__=='__main__':
    main()
