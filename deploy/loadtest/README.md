# Load test

`preview-drag.js` is 20 visitors dragging the letter-size slider in the 3D
preview (a GLB request every ~350 ms per visitor, sizes on a shared grid so
the run mixes real builds and cache hits). Threshold: p95 < 2 s (phase 8).

```sh
# Against a local backend container sized like one prod pod:
docker run -d --name coin-lt --cpus 2 --memory 1g -e BUILD_WORKERS=2 \
  -e ENVIRONMENT=prod -p 18000:8000 coin-backend:local
docker run --rm --network host -v "$PWD:/scripts" -e BASE_URL=http://localhost:18000 \
  -e VUS=20 -e DURATION=90s grafana/k6:latest run /scripts/preview-drag.js

# Against a deployed environment (every VU then shares the k6 machine's IP, so
# the per-client caps apply to all of them together: keep VUS small, or run
# from several machines):
docker run --rm -v "$PWD:/scripts" -e BASE_URL=https://pr-<n>.coins.danielvdspoel.com \
  -e SPOOF_CLIENTS=false -e VUS=3 -e DURATION=60s grafana/k6:latest run /scripts/preview-drag.js
```

## Results

2026-10-01, one backend container (`--cpus 2 --memory 1g`, `BUILD_WORKERS=2`),
i.e. **one** prod pod where the acceptance criterion allows two; 20 VUs, 90 s:

| run | requests | failed | p95 | max | memory after |
|---|---|---|---|---|---|
| first | 3779 | 91 (2.4 %) | 152 ms | 6.1 s | 848 MiB |
| after the fixes below | 3631 | 0 | 77 ms | 5.9 s | 339 MiB |

What the load test found and what was fixed:

- **500s** on one design: earcut triangulated the fancy template's face relief
  at letter size 39.5 into a non-volume. The engine now snaps such a polygon
  to a 1 nm grid (or shrinks it by 0.1 µm) and retries. A sweep of every
  text size 10–60 on all three designs, at both qualities, builds cleanly.
- **Memory:** cached meshes carried trimesh's derived arrays, about 14× the
  mesh itself, so the cache's size estimate was off by an order of magnitude
  and a full cache would have outgrown the 1 GiB limit. They are now cleared
  before caching and after each use; `MALLOC_ARENA_MAX=2` stops the build
  threads' glibc arenas from holding freed memory.
- The ~6 s maximum is the first minute's cold builds queueing behind the two
  workers. After that almost every request is a cache hit (3535 hits,
  192 misses).
