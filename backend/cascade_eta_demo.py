from datetime import datetime, timedelta

from risk_engine import RiskEngine
from eta_engine import ETAEngine


risk_engine = RiskEngine()
eta_engine = ETAEngine()

zone_id = "MEL_Z03"

print()
print("=" * 75)
print("CASCADEGUARD CASCADE + ETA DEMO")
print("=" * 75)

print()
print("STAGE 1: POSSIBLE LANDSLIDE / BLOCKAGE")
print()

blockage_data = {
    "zone_id": zone_id,
    "rainfall_mm_h": 46,
    "soil_moisture": 0.84,
    "tilt_change_deg": 1.60,
    "upstream_rise_m_10m": 0.82,
    "downstream_rise_m_10m": 0.04
}

blockage_result = risk_engine.evaluate(
    blockage_data
)

print(
    "Zone:",
    blockage_result["zone_id"]
)

print(
    "Terrain Susceptibility:",
    blockage_result["terrain"][
        "susceptibility_class"
    ],
    blockage_result["terrain"][
        "susceptibility_score"
    ]
)

print(
    "Alert Level:",
    blockage_result["alert_level"]
)

print(
    "Possible Landslide:",
    blockage_result["cascade"][
        "possible_landslide"
    ]
)

print(
    "Possible Blockage:",
    blockage_result["cascade"][
        "possible_blockage"
    ]
)

print(
    "Possible Surge:",
    blockage_result["cascade"][
        "possible_surge"
    ]
)

print()
print("Downstream Pre-Warnings:")

for warning in blockage_result[
    "downstream_warnings"
]:

    print(
        warning["zone_id"],
        "→",
        warning["warning"]
    )

print()

input(
    "Press ENTER to simulate blockage release..."
)

print()
print("=" * 75)
print("STAGE 2: BLOCKAGE RELEASE / SURGE")
print("=" * 75)
print()

surge_data = {
    "zone_id": zone_id,
    "rainfall_mm_h": 28,
    "soil_moisture": 0.82,
    "tilt_change_deg": 0.60,
    "upstream_rise_m_10m": 0.18,
    "downstream_rise_m_10m": 1.05
}

surge_result = risk_engine.evaluate(
    surge_data
)

surge_time = datetime.now()

print(
    "Zone:",
    surge_result["zone_id"]
)

print(
    "Detection Time:",
    surge_time.strftime(
        "%H:%M:%S"
    )
)

print(
    "Alert Level:",
    surge_result["alert_level"]
)

print(
    "Possible Blockage:",
    surge_result["cascade"][
        "possible_blockage"
    ]
)

print(
    "Possible Surge:",
    surge_result["cascade"][
        "possible_surge"
    ]
)

print()
print("Downstream Surge Warnings:")

for warning in surge_result[
    "downstream_warnings"
]:

    print(
        warning["zone_id"],
        "→",
        warning["warning"]
    )

if surge_result["cascade"]["possible_surge"]:

    print()
    print("SURGE DETECTED")

    print()
    print("=" * 75)
    print("PHYSICS-INFORMED DOWNSTREAM ETA")
    print("=" * 75)
    print()

    predictions = eta_engine.predict(
        source_zone=zone_id,
        event_time=surge_time,
        zone_count=4
    )

    for prediction in predictions:

        print(
            prediction["zone_id"]
        )

        print(
            "  River Reach:",
            prediction[
                "reach_length_km"
            ],
            "km"
        )

        print(
            "  Estimated Travel Time:",
            prediction[
                "travel_time_min_minutes"
            ],
            "-",
            prediction[
                "travel_time_max_minutes"
            ],
            "min"
        )

        print(
            "  Estimated Arrival:",
            prediction[
                "eta_min"
            ],
            "-",
            prediction[
                "eta_max"
            ]
        )

        print(
            "  Forecast Type:",
            prediction[
                "forecast_type"
            ]
        )

        print()

    print(
        "Simulating MEL_Z04 surge detection 9 minutes later..."
    )

    observed_time = (
        surge_time
        + timedelta(
            minutes=9
        )
    )

    print()

    print(
        "MEL_Z04 Actual Detection Time:",
        observed_time.strftime(
            "%H:%M:%S"
        )
    )

    updated = eta_engine.update_from_observation(
        source_zone="MEL_Z03",
        observed_zone="MEL_Z04",
        source_time=surge_time,
        observed_time=observed_time,
        zone_count=3
    )

    observation = updated[
        "observation"
    ]

    print()
    print("=" * 75)
    print("REAL-TIME SENSOR CALIBRATION")
    print("=" * 75)
    print()

    print(
        "Observed Distance:",
        round(
            observation["distance_m"]
            / 1000,
            2
        ),
        "km"
    )

    print(
        "Observed Travel Time:",
        round(
            observation["travel_seconds"]
            / 60,
            2
        ),
        "minutes"
    )

    print(
        "Observed Average Wave Speed:",
        observation[
            "observed_celerity_m_s"
        ],
        "m/s"
    )

    print(
        "Calibration Factor:",
        observation[
            "calibration_factor"
        ]
    )

    print()
    print("=" * 75)
    print("UPDATED DOWNSTREAM ETA")
    print("=" * 75)
    print()

    for prediction in updated[
        "predictions"
    ]:

        print(
            prediction["zone_id"]
        )

        print(
            "  Corrected Wave Speed:",
            prediction[
                "corrected_celerity_m_s"
            ],
            "m/s"
        )

        print(
            "  Updated Travel Time:",
            prediction[
                "travel_time_min_minutes"
            ],
            "-",
            prediction[
                "travel_time_max_minutes"
            ],
            "min"
        )

        print(
            "  Updated Arrival:",
            prediction[
                "eta_min"
            ],
            "-",
            prediction[
                "eta_max"
            ]
        )

        print(
            "  Forecast Type:",
            prediction[
                "forecast_type"
            ]
        )

        print()

else:

    print()
    print(
        "No surge detected. ETA engine not activated."
    )