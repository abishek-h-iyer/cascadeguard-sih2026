// Thin service layer. Every function returns the same shape the rest of the
// app expects (see mockStore.js's `nextZones[zoneId]` shape). To go live:
//   1. Set USE_MOCK = false
//   2. Set BASE_URL to the running FastAPI server
//   3. If the real /zones response doesn't already match the mock shape,
//      adjust adaptBackendZone() below — nothing else in the app needs to change.
import { mockStore } from './mockStore'

const USE_MOCK = true
const BASE_URL = 'http://localhost:8000'

async function getJSON(path) {
  const res = await fetch(`${BASE_URL}${path}`)
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`)
  return res.json()
}

async function postJSON(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`)
  return res.json().catch(() => null)
}

// Adjust this once the real backend's zone JSON shape is known. It should
// return the same fields components read: zone_id, terrain, sensors,
// sensor_states, cascade, alert_level, operational_status, reasons,
// downstream_warnings, incoming_warning, sensor_nodes, last_updated, overridden.
function adaptBackendZone(raw) {
  return raw
}

export async function getHealth() {
  if (USE_MOCK) {
    const { connection } = mockStore.getSnapshot()
    return { status: connection.systemOnline ? 'ONLINE' : 'OFFLINE', gateway: connection.gatewayConnected ? 'CONNECTED' : 'DISCONNECTED' }
  }
  return getJSON('/health')
}

export async function getZones() {
  if (USE_MOCK) {
    const { zones } = mockStore.getSnapshot()
    return Object.values(zones)
  }
  const zones = await getJSON('/zones')
  return zones.map(adaptBackendZone)
}

export async function getZone(zoneId) {
  if (USE_MOCK) {
    const { zones } = mockStore.getSnapshot()
    return zones[zoneId] || null
  }
  return adaptBackendZone(await getJSON(`/zones/${zoneId}`))
}

export async function getLatestRisk() {
  if (USE_MOCK) return getZones()
  const zones = await getJSON('/latest-risk')
  return zones.map(adaptBackendZone)
}

export async function getEvents() {
  if (USE_MOCK) {
    return mockStore.getSnapshot().events
  }
  return getJSON('/events')
}

export async function resetDemo() {
  if (USE_MOCK) {
    mockStore.reset()
    return
  }
  return postJSON('/reset')
}
