// Thin fetch wrapper around the FastAPI backend (backend/main.py). Every
// function returns the shape the rest of the app expects; adaptBackendZone()
// is the one seam where the wire format (snake_case, except sensor node
// crc_valid) gets translated to what the components read.
// Pinned to the IPv4 loopback address rather than 'localhost': uvicorn
// binds IPv4-only by default, but on Windows 'localhost' often resolves to
// the IPv6 loopback (::1) first, which silently fails to connect.
const BASE_URL = 'http://127.0.0.1:8000'

async function getJSON(path) {
  const res = await fetch(`${BASE_URL}${path}`)
  if (!res.ok) throw await toApiError(res)
  return res.json()
}

async function postJSON(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw await toApiError(res)
  return res.json().catch(() => null)
}

async function deleteJSON(path) {
  const res = await fetch(`${BASE_URL}${path}`, { method: 'DELETE' })
  if (!res.ok) throw await toApiError(res)
  return res.json().catch(() => null)
}

async function toApiError(res) {
  const body = await res.json().catch(() => null)
  const detail = body?.detail
  const message = typeof detail === 'string'
    ? detail
    : Array.isArray(detail)
      ? detail.map((d) => d.msg).join('; ')
      : `Request failed with status ${res.status}`
  const error = new Error(message)
  error.status = res.status
  return error
}

function adaptBackendZone(raw) {
  return {
    ...raw,
    sensor_nodes: raw.sensor_nodes.map((node) => ({
      ...node,
      crcValid: node.crc_valid,
    })),
  }
}

function adaptHealth(raw) {
  return {
    systemOnline: raw.status === 'ONLINE',
    gatewayConnected: raw.gateway === 'CONNECTED',
    lastSensorUpdate: raw.last_sensor_update,
  }
}

export async function getHealth() {
  return adaptHealth(await getJSON('/health'))
}

export async function getZones() {
  const zones = await getJSON('/zones')
  return zones.map(adaptBackendZone)
}

export async function getZone(zoneId) {
  return adaptBackendZone(await getJSON(`/zones/${zoneId}`))
}

export async function getLatestRisk() {
  const zones = await getJSON('/latest-risk')
  return zones.map(adaptBackendZone)
}

export async function getEvents() {
  return getJSON('/events')
}

export async function resetDemo() {
  return postJSON('/reset')
}

export async function setZoneOverride(zoneId, partialSensors) {
  const result = await postJSON(`/zones/${zoneId}/override`, partialSensors)
  return { ...result, zone: adaptBackendZone(result.zone) }
}

export async function clearZoneOverride(zoneId) {
  const result = await deleteJSON(`/zones/${zoneId}/override`)
  return { ...result, zone: adaptBackendZone(result.zone) }
}

export async function ingestPacket(packet) {
  return postJSON('/ingest', { packet })
}
