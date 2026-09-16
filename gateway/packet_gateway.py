from pathlib import Path
from datetime import datetime
import sys


BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(
    0,
    str(BASE_DIR / "backend")
)

from risk_engine import RiskEngine
from eta_engine import ETAEngine


def crc8(data):

    crc = 0x00

    for byte in data.encode("utf-8"):

        crc ^= byte

        for _ in range(8):

            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF

            else:
                crc = (crc << 1) & 0xFF

    return crc


def crc8_hex(data):

    return f"{crc8(data):02X}"


def build_packet(
    node_id,
    zone_id,
    sensor_type,
    value,
    sequence
):

    payload = (
        f"{node_id}|"
        f"{zone_id}|"
        f"{sensor_type}|"
        f"{value}|"
        f"{sequence}"
    )

    crc = crc8_hex(payload)

    return (
        f"SOF|"
        f"{payload}|"
        f"{crc}|"
        f"EOF"
    )


class PacketGateway:

    SENSOR_MAP = {
        "RAIN": "rainfall_mm_h",
        "SOIL": "soil_moisture",
        "TILT": "tilt_change_deg",
        "UP_RISE": "upstream_rise_m_10m",
        "DOWN_RISE": "downstream_rise_m_10m"
    }

    REQUIRED_FIELDS = {
        "rainfall_mm_h",
        "soil_moisture",
        "tilt_change_deg",
        "upstream_rise_m_10m",
        "downstream_rise_m_10m"
    }


    def __init__(self):

        self.engine = RiskEngine()

        self.eta_engine = ETAEngine()

        self.zone_state = {}

        self.last_sequence = {}

        self.active_surge_events = {}


    def parse_packet(self, packet):

        parts = packet.strip().split("|")

        if len(parts) != 8:

            raise ValueError(
                "Invalid packet length"
            )


        if parts[0] != "SOF":

            raise ValueError(
                "Invalid SOF"
            )


        if parts[-1] != "EOF":

            raise ValueError(
                "Invalid EOF"
            )


        node_id = parts[1]
        zone_id = parts[2]
        sensor_type = parts[3]

        value_text = parts[4]
        sequence_text = parts[5]

        received_crc = parts[6].upper()


        payload = "|".join(
            parts[1:6]
        )

        calculated_crc = crc8_hex(
            payload
        )


        if received_crc != calculated_crc:

            raise ValueError(
                f"CRC mismatch: "
                f"received={received_crc}, "
                f"calculated={calculated_crc}"
            )


        try:

            value = float(
                value_text
            )

        except ValueError:

            raise ValueError(
                "Sensor value must be numeric"
            )


        try:

            sequence = int(
                sequence_text
            )

        except ValueError:

            raise ValueError(
                "Sequence number must be integer"
            )


        if not 0 <= sequence <= 255:

            raise ValueError(
                "Sequence number must be 0-255"
            )


        if sensor_type not in self.SENSOR_MAP:

            raise ValueError(
                f"Unknown sensor type: {sensor_type}"
            )


        if zone_id not in self.engine.susceptibility:

            raise ValueError(
                f"Unknown zone: {zone_id}"
            )


        return {
            "node_id": node_id,
            "zone_id": zone_id,
            "sensor_type": sensor_type,
            "value": value,
            "sequence": sequence,
            "crc": received_crc
        }


    def start_eta_forecast(
        self,
        zone_id,
        event_time
    ):

        if zone_id in self.active_surge_events:

            event = self.active_surge_events[
                zone_id
            ]

            return {
                "status": "ACTIVE",
                "source_zone": zone_id,
                "source_time": event[
                    "source_time"
                ].strftime(
                    "%H:%M:%S"
                ),
                "predictions": event[
                    "predictions"
                ]
            }


        predictions = self.eta_engine.predict(
            source_zone=zone_id,
            event_time=event_time,
            zone_count=4
        )

        self.active_surge_events[
            zone_id
        ] = {
            "source_time": event_time,
            "predictions": predictions,
            "observed_zones": set()
        }

        return {
            "status": "INITIAL_FORECAST",
            "source_zone": zone_id,
            "source_time": event_time.strftime(
                "%H:%M:%S"
            ),
            "predictions": predictions
        }


    def find_active_source(
        self,
        observed_zone
    ):

        observed_number = (
            self.eta_engine.zone_number(
                observed_zone
            )
        )

        candidates = []

        for source_zone, event in (
            self.active_surge_events.items()
        ):

            source_number = (
                self.eta_engine.zone_number(
                    source_zone
                )
            )

            if (
                source_number
                < observed_number
                and observed_zone
                not in event["observed_zones"]
            ):

                candidates.append(
                    (
                        source_number,
                        source_zone
                    )
                )


        if not candidates:

            return None


        candidates.sort(
            reverse=True
        )

        return candidates[0][1]


    def process_eta_observation(
        self,
        observed_zone,
        observed_time
    ):

        source_zone = (
            self.find_active_source(
                observed_zone
            )
        )


        if source_zone is None:

            return None


        event = self.active_surge_events[
            source_zone
        ]

        updated = (
            self.eta_engine.update_from_observation(
                source_zone=source_zone,
                observed_zone=observed_zone,
                source_time=event[
                    "source_time"
                ],
                observed_time=observed_time,
                zone_count=4
            )
        )


        event["observed_zones"].add(
            observed_zone
        )

        event["predictions"] = (
            updated["predictions"]
        )


        return {
            "status": "SENSOR_CALIBRATED",
            "source_zone": source_zone,
            "observed_zone": observed_zone,
            "source_time": event[
                "source_time"
            ].strftime(
                "%H:%M:%S"
            ),
            "observed_time": (
                observed_time.strftime(
                    "%H:%M:%S"
                )
            ),
            "observation": updated[
                "observation"
            ],
            "predictions": updated[
                "predictions"
            ]
        }


    def process_packet(
        self,
        packet,
        received_time=None
    ):

        packet_time = (
            received_time
            if received_time is not None
            else datetime.now()
        )

        try:

            parsed = self.parse_packet(
                packet
            )

        except ValueError as error:

            return {
                "status": "REJECTED",
                "reason": str(error)
            }


        node_id = parsed[
            "node_id"
        ]

        sequence = parsed[
            "sequence"
        ]


        if (
            node_id in self.last_sequence
            and self.last_sequence[node_id]
            == sequence
        ):

            return {
                "status": "DUPLICATE",
                "node_id": node_id,
                "sequence": sequence
            }


        sequence_warning = None


        if node_id in self.last_sequence:

            expected = (
                self.last_sequence[node_id] + 1
            ) % 256

            if sequence != expected:

                sequence_warning = {
                    "expected": expected,
                    "received": sequence
                }


        self.last_sequence[
            node_id
        ] = sequence


        zone_id = parsed[
            "zone_id"
        ]


        if zone_id not in self.zone_state:

            self.zone_state[
                zone_id
            ] = {}


        field = self.SENSOR_MAP[
            parsed["sensor_type"]
        ]


        self.zone_state[
            zone_id
        ][field] = parsed["value"]


        eta_observation = None


        if (
            parsed["sensor_type"]
            == "DOWN_RISE"
            and parsed["value"] >= 0.60
        ):

            eta_observation = (
                self.process_eta_observation(
                    observed_zone=zone_id,
                    observed_time=packet_time
                )
            )


        state = self.zone_state[
            zone_id
        ]


        missing = (
            self.REQUIRED_FIELDS
            - set(state.keys())
        )


        if missing:

            return {
                "status": "WAITING",
                "node_id": node_id,
                "zone_id": zone_id,
                "sensor_type": (
                    parsed["sensor_type"]
                ),
                "value": parsed["value"],
                "sequence": sequence,
                "crc": parsed["crc"],
                "sequence_warning": (
                    sequence_warning
                ),
                "missing": sorted(
                    missing
                ),
                "eta_observation": (
                    eta_observation
                )
            }


        input_data = {
            "zone_id": zone_id,
            **state
        }


        result = self.engine.evaluate(
            input_data
        )


        eta = None


        if result[
            "cascade"
        ][
            "possible_surge"
        ]:

            eta = self.start_eta_forecast(
                zone_id=zone_id,
                event_time=packet_time
            )


        return {
            "status": "EVALUATED",
            "source_node": node_id,
            "updated_sensor": (
                parsed["sensor_type"]
            ),
            "sequence": sequence,
            "crc": parsed["crc"],
            "sequence_warning": (
                sequence_warning
            ),
            "result": result,
            "eta": eta,
            "eta_observation": (
                eta_observation
            )
        }