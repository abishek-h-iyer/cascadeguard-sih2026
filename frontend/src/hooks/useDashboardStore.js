import { useSyncExternalStore, useEffect } from 'react'
import { dashboardStore } from '../services/dashboardStore'

export function useDashboardStore() {
  const state = useSyncExternalStore(dashboardStore.subscribe, dashboardStore.getSnapshot)

  useEffect(() => {
    return dashboardStore.startTicking()
  }, [])

  return state
}
