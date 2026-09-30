// k6 load test: N visitors dragging a slider in the 3D preview.
//
// Each virtual user takes the fancy template and changes the letter size along a
// 0.5-unit grid, requesting a GLB every ~350 ms (the frontend's debounce). Grid
// values repeat across users, so the run mixes cache misses (real builds) and
// hits, like a real crowd. The p95 threshold is the phase 8 acceptance number.
//
//   BASE_URL=https://coins.danielvdspoel.com VUS=20 DURATION=2m k6 run preview-drag.js
//   (or via Docker, see README.md)
import http from 'k6/http'
import { check, sleep } from 'k6'

const BASE = __ENV.BASE_URL || 'http://localhost:8000'
// Each VU claims its own client address, so per-client limits apply per VU.
// Only honoured where the backend trusts the peer (local runs); through
// Cloudflare every VU is the machine running k6.
const SPOOF_CLIENTS = (__ENV.SPOOF_CLIENTS || 'true') === 'true'

export const options = {
  scenarios: {
    drag: {
      executor: 'constant-vus',
      vus: Number(__ENV.VUS || 20),
      duration: __ENV.DURATION || '2m',
    },
  },
  thresholds: {
    'http_req_duration{endpoint:glb}': ['p(95)<2000'],
    'checks{endpoint:glb}': ['rate>0.95'],
  },
}

export function setup() {
  const res = http.get(`${BASE}/api/templates`)
  const fancy = res.json().find((t) => t.id === 'fancy-example')
  return { config: fancy.config }
}

export default function (data) {
  const config = JSON.parse(JSON.stringify(data.config))
  const step = (__VU * 7 + __ITER) % 41 // 41 grid positions, users overlap
  config.faces.front.top_text.size = 20 + step * 0.5
  const headers = { 'Content-Type': 'application/json' }
  if (SPOOF_CLIENTS) headers['X-Forwarded-For'] = `203.0.113.${__VU}`
  const res = http.post(`${BASE}/api/preview/glb`, JSON.stringify({ config, quality: 'preview' }), {
    headers,
    tags: { endpoint: 'glb' },
    timeout: '30s',
  })
  check(res, { 'glb 200': (r) => r.status === 200 }, { endpoint: 'glb' })
  sleep(0.35)
}
