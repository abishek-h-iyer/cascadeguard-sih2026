import json

from packet_gateway import (
    PacketGateway,
    build_packet
)


gateway = PacketGateway()


def show(packet):

    print("\nPACKET:")
    print(packet)

    result = gateway.process_packet(
        packet
    )

    print(
        json.dumps(
            result,
            indent=2
        )
    )

    return result


print("\n==============================")
print("VALID PACKET")
print("==============================")


valid_packet = build_packet(
    "RAIN_03",
    "MEL_Z03",
    "RAIN",
    3,
    1
)

show(
    valid_packet
)


print("\n==============================")
print("CORRUPTED PACKET")
print("==============================")


corrupted_packet = (
    valid_packet.replace(
        "|3|1|",
        "|99|1|"
    )
)

show(
    corrupted_packet
)


print("\n==============================")
print("DUPLICATE PACKET")
print("==============================")


show(
    valid_packet
)


print("\n==============================")
print("COMPLETE SENSOR SET")
print("==============================")


packets = [

    build_packet(
        "SOIL_03",
        "MEL_Z03",
        "SOIL",
        0.38,
        1
    ),

    build_packet(
        "TILT_03",
        "MEL_Z03",
        "TILT",
        0.1,
        1
    ),

    build_packet(
        "UP_03",
        "MEL_Z03",
        "UP_RISE",
        0.05,
        1
    ),

    build_packet(
        "DOWN_03",
        "MEL_Z03",
        "DOWN_RISE",
        0.04,
        1
    )

]


for packet in packets:

    show(
        packet
    )