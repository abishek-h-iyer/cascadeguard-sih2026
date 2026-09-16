// Client-side store backed by the real CascadeGuard API instead of an
// in-browser simulation. Keeps the same subscribe/getSnapshot shape the old
// mockStore had so App.jsx and useDashboardStore don't need to change their
// interaction pattern — only where the data comes from changes.
import {
  getHealth,
  getZones,
  getEvents,
  resetDemo,
  setZoneOverride,
  clearZoneOverride,
} from './api'

const STATUS_RANK = { SAFE: 0, WATCH: 1, CRITICAL: 2 }
const OVERRIDE_DEBOUNCE_MS = 150

function pickHighestRiskZone(zones) {
  let best = null
  for (const zone of Object.values(zones)) {
    if (!best || STATUS_RANK[zone.operational_status] > STATUS_RANK[best.operational_status]) {
      best = zone
    }
  }
  return best ? best.zone_id : null
}

function zonesById(zoneList) {
  const zones = {}
  for (const zone of zoneList) zones[zone.zone_id] = zone
  return zones
}

function createStore() {
  let state = {
    zones: {},
    events: [],
    connection: { systemOnline: false, gatewayConnected: false, lastSensorUpdate: Date.now() },
    riskViewMode: 'LIVE',
    selectedZoneId: null,
  }

  const listeners = new Set()
  const overrideTimers = {}

  function notify() {
    for (const fn of listeners) fn()
  }

  async function refresh() {
    try {
      const [health, zoneList, events] = await Promise.all([getHealth(), getZones(), getEvents()])
      state = {
        ...state,
        zones: zonesById(zoneList),
        events,
        connection: health,
        selectedZoneId: state.selectedZoneId || pickHighestRiskZone(zonesById(zoneList)),
      }
    } catch (error) {
      state = {
        ...state,
        connection: { ...state.connection, systemOnline: false, gatewayConnected: false },
      }
      console.error('CascadeGuard API unreachable:', error.message)
    }
    notify()
  }

  return {
    subscribe(fn) {
      listeners.add(fn)
      return () => listeners.delete(fn)
    },

    getSnapshot() {
      return state
    },

    selectZone(zoneId) {
      state = { ...state, selectedZoneId: zoneId }
      notify()
    },

    setRiskViewMode(mode) {
      state = { ...state, riskViewMode: mode }
      notify()
    },

    setSensorOverride(zoneId, partial) {
      // Merge optimistically so sliders feel responsive while the debounced
      // request is in flight.
      const current = state.zones[zoneId]
      if (current) {
        const optimisticZone = { ...current, sensors: { ...current.sensors, ...partial }, overridden: true }
        state = { ...state, zones: { ...state.zones, [zoneId]: optimisticZone } }
        notify()
      }

      clearTimeout(overrideTimers[zoneId])
      overrideTimers[zoneId] = setTimeout(async () => {
        try {
          const { zone } = await setZoneOverride(zoneId, partial)
          state = { ...state, zones: { ...state.zones, [zoneId]: zone } }
          notify()
        } catch (error) {
          console.error(`Failed to override ${zoneId}:`, error.message)
        }
      }, OVERRIDE_DEBOUNCE_MS)
    },

    async clearOverride(zoneId) {
      try {
        const { zone } = await clearZoneOverride(zoneId)
        state = { ...state, zones: { ...state.zones, [zoneId]: zone } }
        notify()
      } catch (error) {
        console.error(`Failed to clear override for ${zoneId}:`, error.message)
      }
    },

    async reset() {
      await resetDemo().catch((error) => console.error('Failed to reset demo:', error.message))
      state = { ...state, selectedZoneId: null }
      await refresh()
    },

    startTicking(intervalMs = 3500) {
      refresh()
      const id = setInterval(refresh, intervalMs)
      return () => clearInterval(id)
    },
  }
}

export const dashboardStore = createStore()
