// Real values from data/processed/eta_reach_parameters.csv (DEM-derived reach
// length + slope, one reach per zone = the river segment immediately
// upstream of that zone). Kept as static data, same pattern as
// zoneStaticData.js, so utils/etaEngine.js never has to read a CSV at
// runtime in the browser.

export const ETA_REACHES = {
  MEL_Z01: { reach_length_m: 3697.77, reach_slope: 0.177134 },
  MEL_Z02: { reach_length_m: 4270.37, reach_slope: 0.189211 },
  MEL_Z03: { reach_length_m: 3922.11, reach_slope: 0.173631 },
  MEL_Z04: { reach_length_m: 3913.6, reach_slope: 0.155867 },
  MEL_Z05: { reach_length_m: 4181.16, reach_slope: 0.11504 },
  MEL_Z06: { reach_length_m: 3773.28, reach_slope: 0.090372 },
  MEL_Z07: { reach_length_m: 4080.61, reach_slope: 0.062491 },
  MEL_Z08: { reach_length_m: 4172.67, reach_slope: 0.043378 },
  MEL_Z09: { reach_length_m: 3846.76, reach_slope: 0.036914 },
  MEL_Z10: { reach_length_m: 4104.94, reach_slope: 0.029964 },
  MEL_Z11: { reach_length_m: 3993.03, reach_slope: 0.018282 },
  MEL_Z12: { reach_length_m: 1931.37, reach_slope: 0.023817 },
}
