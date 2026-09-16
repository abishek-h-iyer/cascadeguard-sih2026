import { useSyncExternalStore, useEffect } from 'react'
import { mockStore } from '../services/mockStore'

export function useDashboardStore() {
  const state = useSyncExternalStore(mockStore.subscribe, mockStore.getSnapshot)

  useEffect(() => {
    return mockStore.startTicking()
  }, [])

  return state
}
