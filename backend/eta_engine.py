from pathlib import Path
from datetime import datetime, timedelta

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

REACH_FILE = (
    ROOT
    / "data"
    / "processed"
    / "eta_reach_parameters.csv"
)

MANNING_N_FAST = 0.035
MANNING_N_SLOW = 0.050

HYDRAULIC_RADIUS_FAST = 0.60
HYDRAULIC_RADIUS_SLOW = 0.30

MANNING_N_NOMINAL = 0.0425
HYDRAULIC_RADIUS_NOMINAL = 0.45

CELERITY_FACTOR = 5 / 3


class ETAEngine:

    def __init__(self):

        self.reaches = pd.read_csv(
            REACH_FILE
        )

        self.reaches["zone_number"] = (
            self.reaches["zone_id"]
            .str.extract(r"(\d+)")
            .astype(int)
        )

    def zone_number(
        self,
        zone_id
    ):

        return int(
            zone_id.split("Z")[-1]
        )

    def velocity(
        self,
        slope,
        manning_n,
        hydraulic_radius
    ):

        if slope <= 0:
            return 0

        return (
            (1 / manning_n)
            * (hydraulic_radius ** (2 / 3))
            * (slope ** 0.5)
        )

    def celerity(
        self,
        slope,
        manning_n,
        hydraulic_radius
    ):

        return (
            CELERITY_FACTOR
            * self.velocity(
                slope,
                manning_n,
                hydraulic_radius
            )
        )

    def predict(
        self,
        source_zone,
        event_time,
        zone_count=4
    ):

        source_number = self.zone_number(
            source_zone
        )

        downstream = (
            self.reaches[
                self.reaches["zone_number"]
                > source_number
            ]
            .sort_values("zone_number")
            .head(zone_count)
        )

        results = []

        cumulative_min_seconds = 0
        cumulative_max_seconds = 0

        for _, reach in downstream.iterrows():

            length = float(
                reach["reach_length_m"]
            )

            slope = float(
                reach["reach_slope"]
            )

            fast_celerity = self.celerity(
                slope,
                MANNING_N_FAST,
                HYDRAULIC_RADIUS_FAST
            )

            slow_celerity = self.celerity(
                slope,
                MANNING_N_SLOW,
                HYDRAULIC_RADIUS_SLOW
            )

            min_seconds = (
                length / fast_celerity
            )

            max_seconds = (
                length / slow_celerity
            )

            cumulative_min_seconds += (
                min_seconds
            )

            cumulative_max_seconds += (
                max_seconds
            )

            eta_min = (
                event_time
                + timedelta(
                    seconds=cumulative_min_seconds
                )
            )

            eta_max = (
                event_time
                + timedelta(
                    seconds=cumulative_max_seconds
                )
            )

            results.append(
                {
                    "zone_id": reach["zone_id"],

                    "reach_length_km": round(
                        length / 1000,
                        2
                    ),

                    "reach_slope": round(
                        slope,
                        4
                    ),

                    "celerity_min_m_s": round(
                        slow_celerity,
                        2
                    ),

                    "celerity_max_m_s": round(
                        fast_celerity,
                        2
                    ),

                    "travel_time_min_minutes": round(
                        cumulative_min_seconds / 60,
                        1
                    ),

                    "travel_time_max_minutes": round(
                        cumulative_max_seconds / 60,
                        1
                    ),

                    "eta_min": eta_min.strftime(
                        "%H:%M:%S"
                    ),

                    "eta_max": eta_max.strftime(
                        "%H:%M:%S"
                    ),

                    "forecast_type": "PHYSICS_INITIAL"
                }
            )

        return results

    def update_from_observation(
        self,
        source_zone,
        observed_zone,
        source_time,
        observed_time,
        zone_count=3,
        uncertainty_fraction=0.20
    ):

        source_number = self.zone_number(
            source_zone
        )

        observed_number = self.zone_number(
            observed_zone
        )

        if observed_number <= source_number:

            raise ValueError(
                "Observed zone must be downstream."
            )

        observed_reaches = (
            self.reaches[
                (
                    self.reaches["zone_number"]
                    > source_number
                )
                &
                (
                    self.reaches["zone_number"]
                    <= observed_number
                )
            ]
            .sort_values("zone_number")
        )

        actual_travel_seconds = (
            observed_time
            - source_time
        ).total_seconds()

        if actual_travel_seconds <= 0:

            raise ValueError(
                "Observed time must be after source time."
            )

        total_distance = (
            observed_reaches[
                "reach_length_m"
            ].sum()
        )

        observed_average_speed = (
            total_distance
            / actual_travel_seconds
        )

        nominal_travel_seconds = 0

        for _, reach in observed_reaches.iterrows():

            length = float(
                reach["reach_length_m"]
            )

            slope = float(
                reach["reach_slope"]
            )

            nominal_celerity = self.celerity(
                slope,
                MANNING_N_NOMINAL,
                HYDRAULIC_RADIUS_NOMINAL
            )

            nominal_travel_seconds += (
                length
                / nominal_celerity
            )

        calibration_factor = (
            nominal_travel_seconds
            / actual_travel_seconds
        )

        downstream = (
            self.reaches[
                self.reaches["zone_number"]
                > observed_number
            ]
            .sort_values("zone_number")
            .head(zone_count)
        )

        results = []

        cumulative_min_seconds = 0
        cumulative_max_seconds = 0

        for _, reach in downstream.iterrows():

            length = float(
                reach["reach_length_m"]
            )

            slope = float(
                reach["reach_slope"]
            )

            nominal_celerity = self.celerity(
                slope,
                MANNING_N_NOMINAL,
                HYDRAULIC_RADIUS_NOMINAL
            )

            corrected_celerity = (
                nominal_celerity
                * calibration_factor
            )

            slow_celerity = (
                corrected_celerity
                * (
                    1
                    - uncertainty_fraction
                )
            )

            fast_celerity = (
                corrected_celerity
                * (
                    1
                    + uncertainty_fraction
                )
            )

            min_seconds = (
                length
                / fast_celerity
            )

            max_seconds = (
                length
                / slow_celerity
            )

            cumulative_min_seconds += (
                min_seconds
            )

            cumulative_max_seconds += (
                max_seconds
            )

            eta_min = (
                observed_time
                + timedelta(
                    seconds=cumulative_min_seconds
                )
            )

            eta_max = (
                observed_time
                + timedelta(
                    seconds=cumulative_max_seconds
                )
            )

            results.append(
                {
                    "zone_id": reach["zone_id"],

                    "nominal_celerity_m_s": round(
                        nominal_celerity,
                        2
                    ),

                    "corrected_celerity_m_s": round(
                        corrected_celerity,
                        2
                    ),

                    "travel_time_min_minutes": round(
                        cumulative_min_seconds / 60,
                        1
                    ),

                    "travel_time_max_minutes": round(
                        cumulative_max_seconds / 60,
                        1
                    ),

                    "eta_min": eta_min.strftime(
                        "%H:%M:%S"
                    ),

                    "eta_max": eta_max.strftime(
                        "%H:%M:%S"
                    ),

                    "forecast_type": "SENSOR_CALIBRATED"
                }
            )

        return {
            "observation": {

                "distance_m": round(
                    total_distance,
                    2
                ),

                "travel_seconds": round(
                    actual_travel_seconds,
                    2
                ),

                "observed_celerity_m_s": round(
                    observed_average_speed,
                    3
                ),

                "nominal_travel_minutes": round(
                    nominal_travel_seconds / 60,
                    2
                ),

                "calibration_factor": round(
                    calibration_factor,
                    3
                )
            },

            "predictions": results
        }


if __name__ == "__main__":

    engine = ETAEngine()

    source_zone = "MEL_Z03"

    source_time = datetime.now()

    print()
    print("=" * 75)
    print("CASCADEGUARD INITIAL ETA")
    print("=" * 75)

    print(
        "Source Zone:",
        source_zone
    )

    print(
        "Source Time:",
        source_time.strftime(
            "%H:%M:%S"
        )
    )

    initial = engine.predict(
        source_zone,
        source_time,
        zone_count=4
    )

    print()

    for prediction in initial:

        print(
            prediction["zone_id"],
            prediction["eta_min"],
            "-",
            prediction["eta_max"],
            prediction["forecast_type"]
        )

    simulated_observed_time = (
        source_time
        + timedelta(
            minutes=9
        )
    )

    print()
    print("=" * 75)
    print("DOWNSTREAM SENSOR OBSERVATION")
    print("=" * 75)

    print(
        "MEL_Z04 detected surge at:",
        simulated_observed_time.strftime(
            "%H:%M:%S"
        )
    )

    updated = engine.update_from_observation(
        source_zone="MEL_Z03",
        observed_zone="MEL_Z04",
        source_time=source_time,
        observed_time=simulated_observed_time,
        zone_count=3
    )

    observation = updated[
        "observation"
    ]

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
        "Nominal Model Travel Time:",
        observation[
            "nominal_travel_minutes"
        ],
        "minutes"
    )

    print(
        "Calibration Factor:",
        observation[
            "calibration_factor"
        ]
    )

    print()
    print("=" * 75)
    print("SENSOR-CALIBRATED ETA")
    print("=" * 75)

    print()

    for prediction in updated[
        "predictions"
    ]:

        print(
            prediction["zone_id"]
        )

        print(
            "  Nominal Wave Speed:",
            prediction[
                "nominal_celerity_m_s"
            ],
            "m/s"
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
            "  Forecast:",
            prediction[
                "forecast_type"
            ]
        )

        print()