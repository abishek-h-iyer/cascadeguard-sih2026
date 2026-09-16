import json

from risk_engine import RiskEngine


engine = RiskEngine()


tests = [

    {
        "name": "NORMAL CONDITIONS",
        "data": {
            "zone_id": "MEL_Z03",
            "rainfall_mm_h": 3,
            "soil_moisture": 0.38,
            "tilt_change_deg": 0.1,
            "upstream_rise_m_10m": 0.05,
            "downstream_rise_m_10m": 0.04
        }
    },

    {
        "name": "HEAVY RAIN",
        "data": {
            "zone_id": "MEL_Z03",
            "rainfall_mm_h": 32,
            "soil_moisture": 0.73,
            "tilt_change_deg": 0.2,
            "upstream_rise_m_10m": 0.25,
            "downstream_rise_m_10m": 0.22
        }
    },

    {
        "name": "POSSIBLE LANDSLIDE AND BLOCKAGE",
        "data": {
            "zone_id": "MEL_Z03",
            "rainfall_mm_h": 46,
            "soil_moisture": 0.84,
            "tilt_change_deg": 1.6,
            "upstream_rise_m_10m": 0.82,
            "downstream_rise_m_10m": 0.04
        }
    },

    {
        "name": "BLOCKAGE RELEASE AND SURGE",
        "data": {
            "zone_id": "MEL_Z03",
            "rainfall_mm_h": 28,
            "soil_moisture": 0.82,
            "tilt_change_deg": 0.6,
            "upstream_rise_m_10m": 0.18,
            "downstream_rise_m_10m": 1.05
        }
    }

]


for test in tests:

    print("\n")
    print("=" * 60)
    print(test["name"])
    print("=" * 60)

    result = engine.evaluate(
        test["data"]
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )