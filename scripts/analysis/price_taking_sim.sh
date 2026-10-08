#!/bin/bash
# Simulated price-takers for price_taking_simulation.py (step_engine.py --sim SEED) for every month not yet on disk, in three parallel chunks.
# usage: price_taking_sim.sh KIND SEED [FROM TO]   (KIND hydro: 2019-01 → 2025-09; thermal: the months with moments_YYYYMM;
#        FROM TO YYYYMM limit the months, e.g. a check seed on the periods that matter;
#        SCALE=1 (hydro): price-takers at step_engine.WATER_SCALE × λ*, files hsimw<SEED>_*)
cd "$(dirname "$0")/../.."
L=${LOGDIR:-outputs/cache/step/logs}; mkdir -p "$L"
KIND=$1; SEED=$2; FROM=${3:-201901}; TO=${4:-202509}
PRE=$([ "$KIND" = hydro ] && echo hsim || echo sim)$([ -n "$SCALE" ] && echo w)
FLAG=$([ -n "$SCALE" ] && echo --sim-scale)
SRC=$([ "$KIND" = hydro ] && echo hmoments || echo moments)
TODO=$(.venv/bin/python -c "
import pathlib
c = pathlib.Path('outputs/cache/step')
ms = sorted(p.stem.split('_')[1] for p in c.glob('${SRC}_2*.parquet'))
ms = [m for m in ms if '$FROM' <= m <= '$TO']
print(' '.join(m for m in ms if not (c / f'${PRE}${SEED}_moments_{m}.parquet').exists()))")
set -- $TODO
A=(); B=(); C=(); i=0
for m in "$@"; do case $((i % 3)) in 0) A+=("$m");; 1) B+=("$m");; 2) C+=("$m");; esac; i=$((i+1)); done
[ ${#A[@]} -gt 0 ] && .venv/bin/python scripts/analysis/step_engine.py --kind $KIND --sim $SEED $FLAG --months "${A[@]}" > $L/${PRE}${SEED}_a.log 2>&1 &
[ ${#B[@]} -gt 0 ] && .venv/bin/python scripts/analysis/step_engine.py --kind $KIND --sim $SEED $FLAG --months "${B[@]}" > $L/${PRE}${SEED}_b.log 2>&1 &
[ ${#C[@]} -gt 0 ] && .venv/bin/python scripts/analysis/step_engine.py --kind $KIND --sim $SEED $FLAG --months "${C[@]}" > $L/${PRE}${SEED}_c.log 2>&1 &
wait
echo "done: $(ls outputs/cache/step/${PRE}${SEED}_moments_*.parquet | wc -l) months"
