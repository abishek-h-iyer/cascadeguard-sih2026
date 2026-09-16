import json

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
    sequence
):

    packet = build_packet(
        node_id=node_id,
        zone_id=zone_id,
        sensor_type=sensor_type,
        value=value,
        sequence=sequence
    )

    result = gateway.process_packet(
        packet
    )

    print()
    print("PACKET:")
    print(packet)

    print(
        json.dumps(
            result,
            indent=2
        )
    )

    return result


print()
print("=" * 75)
print("CASCADEGUARD GATEWAY + ETA TEST")
print("=" * 75)

print()
print("STAGE 1: BLOCKAGE FORMATION")
print()

send(
    "RAIN_03",
    "MEL_Z03",
    "RAIN",
    46,
    1
)

send(
    "SOIL_03",
    "MEL_Z03",
    "SOIL",
    0.84,
    1
)

send(
    "TILT_03",
    "MEL_Z03",
    "TILT",
    1.60,
    1
)

send(
    "UP_03",
    "MEL_Z03",
    "UP_RISE",
    0.82,
    1
)

blockage_result = send(
    "DOWN_03",
    "MEL_Z03",
    "DOWN_RISE",
    0.04,
    1
)

print()
print("=" * 75)
print("STAGE 2: BLOCKAGE RELEASE / SURGE")
print("=" * 75)
print()

send(
    "RAIN_03",
    "MEL_Z03",
    "RAIN",
    28,
    2
)

send(
    "SOIL_03",
    "MEL_Z03",
    "SOIL",
    0.82,
    2
)

send(
    "TILT_03",
    "MEL_Z03",
    "TILT",
    0.60,
    2
)

send(
    "UP_03",
    "MEL_Z03",
    "UP_RISE",
    0.18,
    2
)

surge_result = send(
    "DOWN_03",
    "MEL_Z03",
    "DOWN_RISE",
    1.05,
    2
)

print()
print("=" * 75)
print("FINAL SUMMARY")
print("=" * 75)
print()

print(
    "Blockage detected:",
    blockage_result[
        "result"
    ][
        "cascade"
    ][
        "possible_blockage"
    ]
)

print(
    "Surge detected:",
    surge_result[
        "result"
    ][
        "cascade"
    ][
        "possible_surge"
    ]
)

print(
    "ETA status:",
    (
        surge_result["eta"]["status"]
        if surge_result["eta"]
        else None
    )
)

if surge_result["eta"]:

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