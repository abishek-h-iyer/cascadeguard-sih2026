import json

from datetime import datetime, timedelta

from packet_gateway import (
    PacketGateway,
    build_packet
)


gateway = PacketGateway()


def send(
    node_id,
    zone_id,
    sensor_type,
    value,
    sequence,
    received_time
):

    packet = build_packet(
        node_id=node_id,
        zone_id=zone_id,
        sensor_type=sensor_type,
        value=value,
        sequence=sequence
    )

    result = gateway.process_packet(
        packet,
        received_time=received_time
    )

    return result


source_time = datetime.now()

blockage_time = (
    source_time
    - timedelta(
        minutes=2
    )
)


print()
print("=" * 75)
print("CASCADEGUARD MULTI-SENSOR ADAPTIVE ETA TEST")
print("=" * 75)


print()
print("STAGE 1: BLOCKAGE")
print()


send(
    "RAIN_03",
    "MEL_Z03",
    "RAIN",
    46,
    1,
    blockage_time
)

send(
    "SOIL_03",
    "MEL_Z03",
    "SOIL",
    0.84,
    1,
    blockage_time
)

send(
    "TILT_03",
    "MEL_Z03",
    "TILT",
    1.60,
    1,
    blockage_time
)

send(
    "UP_03",
    "MEL_Z03",
    "UP_RISE",
    0.82,
    1,
    blockage_time
)

blockage_result = send(
    "DOWN_03",
    "MEL_Z03",
    "DOWN_RISE",
    0.04,
    1,
    blockage_time
)


print(
    "Blockage Time:",
    blockage_time.strftime(
        "%H:%M:%S"
    )
)

print(
    "Possible Blockage:",
    blockage_result[
        "result"
    ][
        "cascade"
    ][
        "possible_blockage"
    ]
)


print()
print("=" * 75)
print("STAGE 2: SURGE RELEASE AT MEL_Z03")
print("=" * 75)
print()


send(
    "RAIN_03",
    "MEL_Z03",
    "RAIN",
    28,
    2,
    source_time
)

send(
    "SOIL_03",
    "MEL_Z03",
    "SOIL",
    0.82,
    2,
    source_time
)

send(
    "TILT_03",
    "MEL_Z03",
    "TILT",
    0.60,
    2,
    source_time
)

send(
    "UP_03",
    "MEL_Z03",
    "UP_RISE",
    0.18,
    2,
    source_time
)

surge_result = send(
    "DOWN_03",
    "MEL_Z03",
    "DOWN_RISE",
    1.05,
    2,
    source_time
)


print(
    "Surge Detection Time:",
    source_time.strftime(
        "%H:%M:%S"
    )
)

print(
    "Possible Surge:",
    surge_result[
        "result"
    ][
        "cascade"
    ][
        "possible_surge"
    ]
)

print(
    "ETA Status:",
    surge_result[
        "eta"
    ][
        "status"
    ]
)


print()
print("INITIAL PHYSICS ETA")
print()


for prediction in surge_result[
    "eta"
][
    "predictions"
]:

    print(
        prediction["zone_id"],
        prediction["eta_min"],
        "-",
        prediction["eta_max"]
    )


z04_time = (
    source_time
    + timedelta(
        minutes=9
    )
)


print()
print("=" * 75)
print("STAGE 3: MEL_Z04 OBSERVES SURGE")
print("=" * 75)
print()


z04_result = send(
    "DOWN_04",
    "MEL_Z04",
    "DOWN_RISE",
    0.95,
    1,
    z04_time
)


z04_observation = z04_result[
    "eta_observation"
]


print(
    "MEL_Z04 Detection Time:",
    z04_time.strftime(
        "%H:%M:%S"
    )
)

print(
    "Observed Wave Speed:",
    z04_observation[
        "observation"
    ][
        "observed_celerity_m_s"
    ],
    "m/s"
)

print(
    "Calibration Factor:",
    z04_observation[
        "observation"
    ][
        "calibration_factor"
    ]
)


print()
print("FIRST UPDATED ETA")
print()


for prediction in z04_observation[
    "predictions"
]:

    print(
        prediction["zone_id"],
        prediction["eta_min"],
        "-",
        prediction["eta_max"]
    )


z05_time = (
    source_time
    + timedelta(
        minutes=21
    )
)


print()
print("=" * 75)
print("STAGE 4: MEL_Z05 OBSERVES SURGE")
print("=" * 75)
print()


z05_result = send(
    "DOWN_05",
    "MEL_Z05",
    "DOWN_RISE",
    0.90,
    1,
    z05_time
)


z05_observation = z05_result[
    "eta_observation"
]


print(
    "MEL_Z05 Detection Time:",
    z05_time.strftime(
        "%H:%M:%S"
    )
)

print()

print(
    json.dumps(
        z05_observation,
        indent=2
    )
)


print()
print("=" * 75)
print("SECOND SENSOR-CALIBRATED ETA")
print("=" * 75)
print()


print(
    "Observed Zone:",
    z05_observation[
        "observed_zone"
    ]
)

print(
    "Cumulative Observed Distance:",
    round(
        z05_observation[
            "observation"
        ][
            "distance_m"
        ] / 1000,
        2
    ),
    "km"
)

print(
    "Cumulative Travel Time:",
    round(
        z05_observation[
            "observation"
        ][
            "travel_seconds"
        ] / 60,
        2
    ),
    "minutes"
)

print(
    "Observed Average Wave Speed:",
    z05_observation[
        "observation"
    ][
        "observed_celerity_m_s"
    ],
    "m/s"
)

print(
    "New Calibration Factor:",
    z05_observation[
        "observation"
    ][
        "calibration_factor"
    ]
)

print()


for prediction in z05_observation[
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