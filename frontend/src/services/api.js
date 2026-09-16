// Thin service layer. Every function here returns the same shape a future
// FastAPI backend would return. Right now they read from mockStore; once the
// real API exists, replace each function body with a fetch(`${BASE_URL}/...`)
// call and no component code needs to change.
import { mockStore } from './mockStore'

const USE_MOCK = true
// const BASE_URL = 'http://localhost:8000'

export async function getHealth() {
  if (USE_MOCK) {
    const { connection } = mockStore.getSnapshot()
    return { status: connection.systemOnline ? 'ONLINE' : 'OFFLINE', gateway: connection.gatewayConnected ? 'CONNECTED' : 'DISCONNECTED' }
  }
}

export async function getZones() {
  if (USE_MOCK) {
    const { zones } = mockStore.getSnapshot()
    return Object.values(zones)
  }
}

export async function getZone(zoneId) {
  if (USE_MOCK) {
    const { zones } = mockStore.getSnapshot()
    return zones[zoneId] || null
  }
}

export async function getLatestRisk() {
  return getZones()
}

export async function getEvents() {
  if (USE_MOCK) {
    return mockStore.getSnapshot().events
  }
}

export async function resetDemo() {
  if (USE_MOCK) {
    mockStore.reset()
  }
}
