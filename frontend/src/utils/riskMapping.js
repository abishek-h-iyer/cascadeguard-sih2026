// Colors for LIVE RISK (operational status) deliberately use a different
// hue family than TERRAIN SUSCEPTIBILITY so toggling between the two map
// modes never looks like "the same data recolored."

export const STATUS_COLOR = {
  SAFE: '#1a8a4a',
  WATCH: '#c98a12',
  CRITICAL: '#c62828',
  OFFLINE: '#8a8f98',
}

export const STATUS_LABEL = {
  SAFE: 'Safe',
  WATCH: 'Watch',
  CRITICAL: 'Critical',
  OFFLINE: 'Offline',
}

export const SUSCEPTIBILITY_COLOR = {
  LOW: '#9fc3e0',
  MODERATE: '#4f8fc0',
  HIGH: '#1c4f7c',
}

export function statusColor(status) {
  return STATUS_COLOR[status] || STATUS_COLOR.OFFLINE
}

export function susceptibilityColor(cls) {
  return SUSCEPTIBILITY_COLOR[cls] || SUSCEPTIBILITY_COLOR.LOW
}
