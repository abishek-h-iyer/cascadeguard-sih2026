from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent
SUSCEPTIBILITY_FILE = (
    BASE_DIR
    / "data"
    / "processed"
    / "zone_susceptibility_final.csv"
)


class RiskEngine:

    def __init__(self):

        df = pd.read_csv(SUSCEPTIBILITY_FILE)

        self.susceptibility = {}

        for _, row in df.iterrows():

            self.susceptibility[row["zone_id"]] = {
                "score": float(row["mean_susceptibility"]),
                "class": row["susceptibility_class"]
            }

        self.blockage_memory = {}


    def zone_number(self, zone_id):

        return int(
            zone_id.split("Z")[1]
        )


    def downstream_zones(self, zone_id, count=4):

        number = self.zone_number(zone_id)

        zones = []

        for value in range(
            number + 1,
            min(number + count + 1, 13)
        ):

            zones.append(
                f"MEL_Z{value:02d}"
            )

        return zones


    def rainfall_state(self, rainfall):

        if rainfall >= 50:
            return "SEVERE"

        if rainfall >= 25:
            return "HIGH"

        if rainfall >= 10:
            return "MODERATE"

        return "LOW"


    def soil_state(self, soil):

        if soil >= 0.80:
            return "SATURATED"

        if soil >= 0.65:
            return "HIGH"

        if soil >= 0.45:
            return "ELEVATED"

        return "NORMAL"


    def tilt_state(self, tilt):

        if tilt >= 1.0:
            return "ABNORMAL"

        if tilt >= 0.4:
            return "WATCH"

        return "NORMAL"


    def upstream_state(self, rise):

        if rise >= 0.50:
            return "RAPID_RISE"

        if rise >= 0.20:
            return "RISING"

        return "STABLE"


    def downstream_state(self, rise):

        if rise >= 0.60:
            return "SURGE"

        if rise >= 0.20:
            return "RISING"

        return "STABLE"


    def operational_status(self, alert_level):

        if alert_level == "CRITICAL":
            return "CRITICAL"

        if alert_level == "LOW":
            return "SAFE"

        return "WATCH"


    def evaluate(self, data):

        zone_id = data["zone_id"]

        rainfall = float(
            data["rainfall_mm_h"]
        )

        soil = float(
            data["soil_moisture"]
        )

        tilt = float(
            data["tilt_change_deg"]
        )

        upstream_rise = float(
            data["upstream_rise_m_10m"]
        )

        downstream_rise = float(
            data["downstream_rise_m_10m"]
        )


        susceptibility = self.susceptibility[
            zone_id
        ]


        rain_state = self.rainfall_state(
            rainfall
        )

        soil_state = self.soil_state(
            soil
        )

        tilt_state = self.tilt_state(
            tilt
        )

        upstream_state = self.upstream_state(
            upstream_rise
        )

        downstream_state = self.downstream_state(
            downstream_rise
        )


        landslide_possible = (
            tilt >= 1.0
            and soil >= 0.65
        ) or (
            tilt >= 0.70
            and rainfall >= 25
            and soil >= 0.75
        )


        blockage_possible = (
            upstream_rise >= 0.50
            and downstream_rise <= 0.10
            and (
                landslide_possible
                or tilt >= 0.70
            )
        )


        previous_blockage = self.blockage_memory.get(
            zone_id,
            False
        )


        surge_possible = (
            downstream_rise >= 0.60
            and previous_blockage
        )


        if blockage_possible:

            self.blockage_memory[
                zone_id
            ] = True


        severity = 0

        reasons = []


        if rainfall >= 10:

            severity = max(
                severity,
                1
            )

            reasons.append(
                "Elevated rainfall"
            )


        if soil >= 0.65:

            severity = max(
                severity,
                1
            )

            reasons.append(
                "High soil moisture"
            )


        if (
            rainfall >= 25
            and soil >= 0.65
        ):

            severity = max(
                severity,
                2
            )

            reasons.append(
                "Heavy rainfall with wet soil"
            )


        if tilt >= 1.0:

            severity = max(
                severity,
                2
            )

            reasons.append(
                "Abnormal slope movement"
            )


        if (
            upstream_rise >= 0.50
            and downstream_rise <= 0.10
        ):

            severity = max(
                severity,
                2
            )

            reasons.append(
                "Upstream-downstream flow anomaly"
            )


        if landslide_possible:

            severity = max(
                severity,
                2
            )

            reasons.append(
                "Possible landslide signature"
            )


        if (
            susceptibility["class"] == "HIGH"
            and severity == 1
        ):

            severity = 2

            reasons.append(
                "High terrain susceptibility"
            )

        elif (
            susceptibility["class"] == "HIGH"
            and severity >= 2
        ):

            reasons.append(
                "High terrain susceptibility"
            )


        if (
            susceptibility["class"] == "MODERATE"
            and severity >= 1
        ):

            reasons.append(
                "Moderate terrain susceptibility"
            )


        if blockage_possible:

            severity = 3

            reasons.append(
                "Possible river blockage"
            )


        if surge_possible:

            severity = 3

            reasons.append(
                "Possible sudden downstream surge"
            )


        levels = [
            "LOW",
            "MODERATE",
            "HIGH",
            "CRITICAL"
        ]


        alert_level = levels[
            severity
        ]


        downstream_warnings = []


        if blockage_possible:

            zones = self.downstream_zones(
                zone_id,
                3
            )

            for zone in zones:

                downstream_warnings.append(
                    {
                        "zone_id": zone,
                        "warning": "WATCH",
                        "reason": (
                            "Potential downstream surge "
                            "if blockage releases"
                        )
                    }
                )


        if surge_possible:

            zones = self.downstream_zones(
                zone_id,
                4
            )

            warning_levels = [
                "CRITICAL",
                "HIGH",
                "HIGH",
                "MODERATE"
            ]

            for index, zone in enumerate(
                zones
            ):

                downstream_warnings.append(
                    {
                        "zone_id": zone,
                        "warning": warning_levels[index],
                        "reason": (
                            "Possible downstream "
                            "surge propagation"
                        )
                    }
                )


        return {

            "zone_id": zone_id,

            "terrain": {

                "susceptibility_score": round(
                    susceptibility["score"],
                    3
                ),

                "susceptibility_class": (
                    susceptibility["class"]
                )
            },

            "sensors": {

                "rainfall_mm_h": rainfall,

                "soil_moisture": soil,

                "tilt_change_deg": tilt,

                "upstream_rise_m_10m": upstream_rise,

                "downstream_rise_m_10m": downstream_rise
            },

            "sensor_states": {

                "rainfall": rain_state,

                "soil": soil_state,

                "tilt": tilt_state,

                "upstream": upstream_state,

                "downstream": downstream_state
            },

            "cascade": {

                "possible_landslide": (
                    landslide_possible
                ),

                "possible_blockage": (
                    blockage_possible
                ),

                "possible_surge": (
                    surge_possible
                )
            },

            "alert_level": alert_level,

            "operational_status": self.operational_status(
                alert_level
            ),

            "reasons": reasons,

            "downstream_warnings": (
                downstream_warnings
            )
        }