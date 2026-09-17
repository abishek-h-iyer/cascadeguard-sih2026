import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import json
import serial
import requests
import time

SERIAL_PORT = "COM5"
BAUD_RATE = 9600
API_URL = "http://127.0.0.1:8000"

SENSORS = [
    ("RAIN", "Rainfall", "mm/h"),
    ("SOIL", "Soil Moisture", ""),
    ("TILT", "Tilt Change", "°"),
    ("UP_RISE", "Upstream Rise", "m/10min"),
    ("DOWN_RISE", "Downstream Rise", "m/10min"),
]

PRESETS = {
    "NORMAL": {
        "RAIN": 3.0,
        "SOIL": 0.38,
        "TILT": 0.10,
        "UP_RISE": 0.05,
        "DOWN_RISE": 0.04,
    },
    "HEAVY RAIN": {
        "RAIN": 32.0,
        "SOIL": 0.73,
        "TILT": 0.20,
        "UP_RISE": 0.25,
        "DOWN_RISE": 0.22,
    },
    "BLOCKAGE": {
        "RAIN": 46.0,
        "SOIL": 0.84,
        "TILT": 1.60,
        "UP_RISE": 0.82,
        "DOWN_RISE": 0.04,
    },
    "SURGE": {
        "RAIN": 28.0,
        "SOIL": 0.82,
        "TILT": 0.60,
        "UP_RISE": 0.18,
        "DOWN_RISE": 1.05,
    },
}

NORMAL_OVERRIDE = {
    "rainfall_mm_h": 3.0,
    "soil_moisture": 0.38,
    "tilt_change_deg": 0.10,
    "upstream_rise_m_10m": 0.05,
    "downstream_rise_m_10m": 0.04,
}


def crc8(data):
    crc = 0

    for byte in data.encode("utf-8"):
        crc ^= byte

        for _ in range(8):
            if crc & 0x80:
                crc = ((crc << 1) ^ 0x07) & 0xFF
            else:
                crc = (crc << 1) & 0xFF

    return crc


class CascadeGuardSimulator:
    def __init__(self, root):
        self.root = root
        self.root.title("CascadeGuard Virtual Sensor Station")
        self.root.geometry("1100x850")

        self.serial_connection = None
        self.last_surge_time = None

        self.zone_var = tk.StringVar(value="03")
        self.sequence_var = tk.IntVar(value=30)
        self.connection_var = tk.StringVar(value="DISCONNECTED")
        self.scenario_var = tk.StringVar(value="NORMAL")

        self.sensor_vars = {
            "RAIN": tk.DoubleVar(value=3.0),
            "SOIL": tk.DoubleVar(value=0.38),
            "TILT": tk.DoubleVar(value=0.10),
            "UP_RISE": tk.DoubleVar(value=0.05),
            "DOWN_RISE": tk.DoubleVar(value=0.04),
        }

        self.build_ui()
        self.connect_serial()
        self.apply_preset("NORMAL")

    def build_ui(self):
        tk.Label(
            self.root,
            text="CASCADEGUARD",
            font=("Segoe UI", 24, "bold"),
        ).pack(pady=(15, 0))

        tk.Label(
            self.root,
            text="Virtual Multi-Sensor Field Station",
            font=("Segoe UI", 12),
        ).pack(pady=(0, 15))

        connection_frame = ttk.LabelFrame(
            self.root,
            text="Communication",
        )
        connection_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(
            connection_frame,
            text="Serial Port:",
        ).grid(row=0, column=0, padx=8, pady=8)

        tk.Label(
            connection_frame,
            text=SERIAL_PORT,
            font=("Consolas", 11, "bold"),
        ).grid(row=0, column=1, padx=8)

        tk.Label(
            connection_frame,
            text="Baud Rate:",
        ).grid(row=0, column=2, padx=8)

        tk.Label(
            connection_frame,
            text=str(BAUD_RATE),
            font=("Consolas", 11, "bold"),
        ).grid(row=0, column=3, padx=8)

        tk.Label(
            connection_frame,
            text="Status:",
        ).grid(row=0, column=4, padx=8)

        tk.Label(
            connection_frame,
            textvariable=self.connection_var,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=5, padx=8)

        ttk.Button(
            connection_frame,
            text="Reconnect",
            command=self.connect_serial,
        ).grid(row=0, column=6, padx=12)

        config_frame = ttk.LabelFrame(
            self.root,
            text="Sensor Station",
        )
        config_frame.pack(fill="x", padx=20, pady=5)

        tk.Label(
            config_frame,
            text="Zone ID",
        ).grid(row=0, column=0, padx=10, pady=10)

        ttk.Entry(
            config_frame,
            textvariable=self.zone_var,
            width=10,
        ).grid(row=0, column=1)

        tk.Label(
            config_frame,
            text="Sequence",
        ).grid(row=0, column=2, padx=10)

        ttk.Entry(
            config_frame,
            textvariable=self.sequence_var,
            width=10,
        ).grid(row=0, column=3)

        tk.Label(
            config_frame,
            text="Current Scenario",
        ).grid(row=0, column=4, padx=10)

        tk.Label(
            config_frame,
            textvariable=self.scenario_var,
            font=("Segoe UI", 10, "bold"),
        ).grid(row=0, column=5)

        sensors_frame = ttk.LabelFrame(
            self.root,
            text="Live Sensor Values",
        )
        sensors_frame.pack(fill="x", padx=20, pady=5)

        for index, (sensor_type, label, unit) in enumerate(SENSORS):
            tk.Label(
                sensors_frame,
                text=label,
                width=18,
                anchor="w",
            ).grid(
                row=index,
                column=0,
                padx=10,
                pady=6,
            )

            ttk.Entry(
                sensors_frame,
                textvariable=self.sensor_vars[sensor_type],
                width=15,
            ).grid(
                row=index,
                column=1,
                padx=5,
            )

            tk.Label(
                sensors_frame,
                text=unit,
                width=10,
                anchor="w",
            ).grid(
                row=index,
                column=2,
                padx=5,
            )

        preset_frame = ttk.LabelFrame(
            self.root,
            text="Demo Scenarios",
        )
        preset_frame.pack(fill="x", padx=20, pady=5)

        for index, preset in enumerate(PRESETS):
            ttk.Button(
                preset_frame,
                text=preset,
                command=lambda p=preset: self.apply_preset(p),
                width=18,
            ).grid(
                row=0,
                column=index,
                padx=8,
                pady=10,
            )

        action_frame = ttk.Frame(self.root)
        action_frame.pack(fill="x", padx=20, pady=8)

        ttk.Button(
            action_frame,
            text="SEND ALL SENSORS",
            command=self.send_all,
        ).pack(side="left", padx=5)

        ttk.Button(
            action_frame,
            text="RESET SYSTEM",
            command=self.reset_system,
        ).pack(side="left", padx=5)

        ttk.Button(
            action_frame,
            text="CLEAR LOG",
            command=self.clear_log,
        ).pack(side="left", padx=5)

        eta_demo_frame = ttk.LabelFrame(
            self.root,
            text="Adaptive ETA Demo",
        )
        eta_demo_frame.pack(fill="x", padx=20, pady=5)

        ttk.Button(
            eta_demo_frame,
            text="SIMULATE Z04 ARRIVAL (+9 MIN)",
            command=self.simulate_z04_arrival,
            width=32,
        ).pack(side="left", padx=10, pady=10)

        ttk.Button(
            eta_demo_frame,
            text="SIMULATE Z05 ARRIVAL (+21 MIN)",
            command=self.simulate_z05_arrival,
            width=32,
        ).pack(side="left", padx=10, pady=10)

        tk.Label(
            eta_demo_frame,
            text="Demo fast-forward only — represents downstream sensor timestamps.",
            font=("Segoe UI", 9),
        ).pack(side="left", padx=10)

        packet_frame = ttk.LabelFrame(
            self.root,
            text="Packet Monitor",
        )
        packet_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=5,
        )

        self.log_box = tk.Text(
            packet_frame,
            height=18,
            font=("Consolas", 10),
            wrap="none",
        )
        self.log_box.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8,
        )

    def connect_serial(self):
        try:
            if (
                self.serial_connection
                and self.serial_connection.is_open
            ):
                self.serial_connection.close()

            self.serial_connection = serial.Serial(
                SERIAL_PORT,
                BAUD_RATE,
                timeout=1,
            )

            self.connection_var.set("CONNECTED")
            self.log("Serial connection established")

        except Exception as error:
            self.connection_var.set("DISCONNECTED")
            self.log(f"SERIAL ERROR: {error}")

    def apply_preset(self, preset):
        values = PRESETS[preset]

        for sensor_type, value in values.items():
            self.sensor_vars[sensor_type].set(value)

        self.scenario_var.set(preset)
        self.log(f"Scenario loaded: {preset}")

    def build_packet(
        self,
        sensor_type,
        value,
        sequence,
        zone=None,
    ):
        if zone is None:
            zone = self.zone_var.get().strip()

        zone = str(zone).zfill(2)

        node_map = {
            "RAIN": f"RAIN_{zone}",
            "SOIL": f"SOIL_{zone}",
            "TILT": f"TILT_{zone}",
            "UP_RISE": f"UP_RISE_{zone}",
            "DOWN_RISE": f"DOWN_RISE_{zone}",
        }

        node_id = node_map[sensor_type]
        zone_id = f"MEL_Z{zone}"
        value_string = str(value)

        payload = (
            f"{node_id}|{zone_id}|"
            f"{sensor_type}|{value_string}|{sequence}"
        )

        crc = crc8(payload)
        crc_hex = f"{crc:02X}"

        return f"SOF|{payload}|{crc_hex}|EOF"

    def send_all(self):
        if (
            not self.serial_connection
            or not self.serial_connection.is_open
        ):
            messagebox.showerror(
                "Serial Error",
                "COM5 is not connected.",
            )
            return

        try:
            sequence = self.sequence_var.get()

            self.log("")
            self.log(
                f"===== {self.scenario_var.get()} "
                f"| SEQ {sequence} ====="
            )

            for sensor_type, label, _ in SENSORS:
                value = self.sensor_vars[sensor_type].get()

                packet = self.build_packet(
                    sensor_type,
                    value,
                    sequence,
                )

                self.serial_connection.write(
                    (packet + "\n").encode("utf-8")
                )

                self.serial_connection.flush()

                self.log(f"{label}: {value}")
                self.log(packet)

                time.sleep(0.15)

            if (
                self.scenario_var.get() == "SURGE"
                and self.zone_var.get().strip().zfill(2) == "03"
            ):
                self.last_surge_time = datetime.now()

                self.log(
                    "Z03 surge source timestamp stored for "
                    "adaptive ETA demo"
                )

            self.sequence_var.set(sequence + 1)

            self.log("ALL 5 PACKETS SENT")
            self.log("==============================")

        except Exception as error:
            self.log(f"SEND ERROR: {error}")

            messagebox.showerror(
                "Send Error",
                str(error),
            )

    def reset_system(self):
        try:
            zone = self.zone_var.get().strip().zfill(2)
            zone_id = f"MEL_Z{zone}"

            reset_response = requests.post(
                f"{API_URL}/reset",
                timeout=5,
            )

            if not reset_response.ok:
                raise RuntimeError(
                    f"/reset returned HTTP "
                    f"{reset_response.status_code}"
                )

            z03_response = requests.post(
                f"{API_URL}/zones/MEL_Z03/override",
                json=NORMAL_OVERRIDE,
                timeout=5,
            )

            if not z03_response.ok:
                raise RuntimeError(
                    "Could not place MEL_Z03 "
                    "into NORMAL baseline."
                )

            if zone_id != "MEL_Z03":
                zone_response = requests.post(
                    f"{API_URL}/zones/{zone_id}/override",
                    json=NORMAL_OVERRIDE,
                    timeout=5,
                )

                if not zone_response.ok:
                    raise RuntimeError(
                        f"Could not place {zone_id} "
                        "into NORMAL baseline."
                    )

            self.apply_preset("NORMAL")
            self.last_surge_time = None

            current_sequence = self.sequence_var.get()
            self.sequence_var.set(current_sequence + 1)

            self.log("")
            self.log("BACKEND SYSTEM RESET")
            self.log("MEL_Z03 locked to NORMAL baseline")

            if zone_id != "MEL_Z03":
                self.log(
                    f"{zone_id} locked to NORMAL baseline"
                )

            self.log(
                "Blockage, surge and ETA state cleared"
            )
            self.log(
                "Ready for a new demonstration"
            )
            self.log("")

            messagebox.showinfo(
                "CascadeGuard",
                "System reset successfully.\n"
                "Ready for a new demo.",
            )

        except Exception as error:
            self.log(f"RESET ERROR: {error}")

            messagebox.showerror(
                "Reset Error",
                str(error),
            )

    def simulate_arrival(
        self,
        observed_zone,
        minutes_after_source,
        downstream_value,
    ):
        if self.last_surge_time is None:
            messagebox.showerror(
                "Adaptive ETA",
                "Run the Z03 SURGE scenario first.",
            )
            return

        try:
            observation_time = (
                self.last_surge_time
                + timedelta(
                    minutes=minutes_after_source
                )
            )

            sequence = self.sequence_var.get()

            packet = self.build_packet(
                "DOWN_RISE",
                downstream_value,
                sequence,
                zone=observed_zone,
            )

            response = requests.post(
                f"{API_URL}/ingest",
                json={
                    "packet": packet,
                    "received_time": (
                        observation_time.isoformat()
                    ),
                },
                timeout=5,
            )

            self.sequence_var.set(sequence + 1)

            self.log("")
            self.log(
                f"FAST-FORWARD OBSERVATION: "
                f"MEL_Z{observed_zone}"
            )
            self.log(
                f"Simulated detection time: "
                f"{observation_time.strftime('%H:%M:%S')}"
            )
            self.log(packet)
            self.log(
                f"HTTP {response.status_code}"
            )

            try:
                result = response.json()

                eta_observation = result.get(
                    "eta_observation"
                )

                if eta_observation:
                    self.log(
                        "ETA RECALIBRATED SUCCESSFULLY"
                    )

                    observation = (
                        eta_observation.get(
                            "observation",
                            {},
                        )
                    )

                    speed = observation.get(
                        "observed_celerity_m_s"
                    )

                    factor = observation.get(
                        "calibration_factor"
                    )

                    if speed is not None:
                        self.log(
                            f"Observed wave speed: "
                            f"{speed} m/s"
                        )

                    if factor is not None:
                        self.log(
                            f"Calibration factor: "
                            f"{factor}"
                        )

                    predictions = (
                        eta_observation.get(
                            "predictions",
                            [],
                        )
                    )

                    for prediction in predictions:
                        self.log(
                            (
                                f"{prediction['zone_id']} "
                                f"→ "
                                f"{prediction['eta_min']} "
                                f"- "
                                f"{prediction['eta_max']}"
                            )
                        )

                else:
                    self.log(
                        json.dumps(
                            result,
                            indent=2,
                        )
                    )

            except ValueError:
                self.log(response.text)

            if not response.ok:
                messagebox.showerror(
                    "Adaptive ETA",
                    (
                        f"Backend returned "
                        f"HTTP {response.status_code}"
                    ),
                )

                return

            if result.get("eta_observation"):
                messagebox.showinfo(
                    "Adaptive ETA",
                    (
                        f"MEL_Z{observed_zone} "
                        "wave observation accepted.\n"
                        "Remaining ETA has been recalibrated."
                    ),
                )

            else:
                messagebox.showwarning(
                    "Adaptive ETA",
                    (
                        "Observation packet was accepted, "
                        "but ETA recalibration was not returned."
                    ),
                )

        except Exception as error:
            self.log(
                f"ETA DEMO ERROR: {error}"
            )

            messagebox.showerror(
                "Adaptive ETA",
                str(error),
            )

    def simulate_z04_arrival(self):
        self.simulate_arrival(
            observed_zone="04",
            minutes_after_source=9,
            downstream_value=0.95,
        )

    def simulate_z05_arrival(self):
        self.simulate_arrival(
            observed_zone="05",
            minutes_after_source=21,
            downstream_value=0.90,
        )

    def log(self, message):
        timestamp = datetime.now().strftime(
            "%H:%M:%S"
        )

        if message:
            self.log_box.insert(
                tk.END,
                f"[{timestamp}] {message}\n",
            )
        else:
            self.log_box.insert(
                tk.END,
                "\n",
            )

        self.log_box.see(tk.END)

    def clear_log(self):
        self.log_box.delete(
            "1.0",
            tk.END,
        )


root = tk.Tk()
app = CascadeGuardSimulator(root)
root.mainloop()