"""CascadeGuard API.

Wraps RiskEngine (per-zone risk evaluation) and PacketGateway (CRC-framed
hardware packet ingestion) behind a FastAPI service, and keeps a live
in-memory snapshot per zone so the dashboard can poll instead of running
its own simulation in the browser.

Run from the project root with the backend virtualenv, e.g.:
    .venv/Scripts/python.exe -m uvicorn backend.main:app --reload --port 8000
"""

import asyncio
import random
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(BASE_DIR / "backend"))
sys.path.insert(0, str(BASE_DIR / "gateway"))

from risk_engine import RiskEngine  # noqa: E402
from packet_gateway import PacketGateway  # noqa: E402


STATUS_RANK = {"SAFE": 0, "WATCH": 1, "CRITICAL": 2}

# (packet sensor type, RiskEngine field, display unit) — mirrors
# gateway.PacketGateway.SENSOR_MAP and the dashboard's live sensor cards.
SENSOR_NODES = [
    ("RAIN", "rainfall_mm_h", "mm/h"),
    ("SOIL", "soil_moisture", ""),
    ("TILT", "tilt_change_deg", "deg"),
    ("UP_RISE", "upstream_rise_m_10m", "m/10min"),
    ("DOWN_RISE", "downstream_rise_m_10m", "m/10min"),
]

TICK_INTERVAL_SECONDS = 3.5

# MEL_Z03 is seeded already mid-cascade so the dashboard has something
# interesting to show the moment it starts, matching the old frontend mock.
DEMO_BLOCKAGE_ZONE = "MEL_Z03"
DEMO_BLOCKAGE_SCENARIO = {
    "rainfall_mm_h": 46,
    "soil_moisture": 0.84,
    "tilt_change_deg": 1.60,
    "upstream_rise_m_10m": 0.82,
    "downstream_rise_m_10m": 0.04,
}

SEED_EVENTS = [
    (-95, "MEL_Z03 rainfall entered HIGH range"),
    (-80, "Soil saturation detected at MEL_Z03"),
    (-62, "Abnormal slope movement detected at MEL_Z03"),
    (-48, "Possible landslide detected at MEL_Z03"),
    (-31, "Possible river blockage detected at MEL_Z03"),
    (-18, "MEL_Z04-Z06 placed on WATCH"),
]


def round2(value):
    return round(value, 2)


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def jitter(spread):
    return (random.random() - 0.5) * spread


def baseline_sensors(susceptibility_class):
    if susceptibility_class == "HIGH":
        base = {"rainfall_mm_h": 4, "soil_moisture": 0.42, "tilt_change_deg": 0.15,
                 "upstream_rise_m_10m": 0.08, "downstream_rise_m_10m": 0.05}
    elif susceptibility_class == "MODERATE":
        base = {"rainfall_mm_h": 3, "soil_moisture": 0.35, "tilt_change_deg": 0.10,
                 "upstream_rise_m_10m": 0.06, "downstream_rise_m_10m": 0.04}
    else:
        base = {"rainfall_mm_h": 2, "soil_moisture": 0.30, "tilt_change_deg": 0.08,
                 "upstream_rise_m_10m": 0.04, "downstream_rise_m_10m": 0.03}

    return {
        "rainfall_mm_h": max(0.0, round2(base["rainfall_mm_h"] + jitter(1.5))),
        "soil_moisture": clamp(round2(base["soil_moisture"] + jitter(0.04)), 0, 1),
        "tilt_change_deg": max(0.0, round2(base["tilt_change_deg"] + jitter(0.04))),
        "upstream_rise_m_10m": max(0.0, round2(base["upstream_rise_m_10m"] + jitter(0.02))),
        "downstream_rise_m_10m": max(0.0, round2(base["downstream_rise_m_10m"] + jitter(0.02))),
    }


def jitter_existing(sensors):
    return {
        "rainfall_mm_h": max(0.0, round2(sensors["rainfall_mm_h"] + jitter(0.6))),
        "soil_moisture": clamp(round2(sensors["soil_moisture"] + jitter(0.01)), 0, 1),
        "tilt_change_deg": max(0.0, round2(sensors["tilt_change_deg"] + jitter(0.02))),
        "upstream_rise_m_10m": max(0.0, round2(sensors["upstream_rise_m_10m"] + jitter(0.01))),
        "downstream_rise_m_10m": max(0.0, round2(sensors["downstream_rise_m_10m"] + jitter(0.01))),
    }


def warning_to_status(warning):
    return "CRITICAL" if warning == "CRITICAL" else "WATCH"


def max_status(a, b):
    return b if STATUS_RANK[b] > STATUS_RANK[a] else a


def now_ms():
    return time.time() * 1000


class DashboardState:
    """Single shared in-memory snapshot: live per-zone readings, the
    aggregated risk view, and the event log. One RiskEngine instance is
    shared between the simulation loop and the packet gateway so blockage
    memory never diverges between a simulated zone and a hardware-fed one.
    """

    def __init__(self):
        self.engine = RiskEngine()
        self.zone_ids = sorted(self.engine.susceptibility.keys())

        self.gateway = PacketGateway()
        self.gateway.engine = self.engine

        self.raw = {}
        self.overridden = {}
        self.sequences = {}

        for zone_id in self.zone_ids:
            self.raw[zone_id] = self._initial_reading(zone_id)
            self.overridden[zone_id] = False
            self.sequences[zone_id] = 0

        self.zones = {}
        self.events = []
        self.system_online = True
        self.gateway_connected = True
        self.last_sensor_update = now_ms()

        self.lock = asyncio.Lock()

        self._seed_events(now_ms())
        self._compute_all(now_ms())

    def _initial_reading(self, zone_id):
        if zone_id == DEMO_BLOCKAGE_ZONE:
            return dict(DEMO_BLOCKAGE_SCENARIO)
        susceptibility_class = self.engine.susceptibility[zone_id]["class"]
        return baseline_sensors(susceptibility_class)

    def _seed_events(self, timestamp_ms):
        self.events = [
            {"id": f"seed-{i}", "timestamp": timestamp_ms + offset * 1000, "message": message}
            for i, (offset, message) in enumerate(SEED_EVENTS)
        ]

    def _push_event(self, message, timestamp_ms):
        event = {
            "id": f"{int(timestamp_ms)}-{random.randint(100000, 999999)}",
            "timestamp": timestamp_ms,
            "message": message,
        }
        self.events = [event, *self.events[:79]]

    def _compute_all(self, timestamp_ms):
        results = {
            zone_id: self.engine.evaluate({"zone_id": zone_id, **self.raw[zone_id]})
            for zone_id in self.zone_ids
        }

        incoming = {}
        for zone_id in self.zone_ids:
            for warning in results[zone_id]["downstream_warnings"]:
                status = warning_to_status(warning["warning"])
                existing = incoming.get(warning["zone_id"])
                if existing is None or STATUS_RANK[status] > STATUS_RANK[existing["status"]]:
                    incoming[warning["zone_id"]] = {
                        "status": status,
                        "reason": warning["reason"],
                        "from_zone": zone_id,
                        "warning_level": warning["warning"],
                    }

        previous_zones = self.zones
        next_zones = {}

        for zone_id in self.zone_ids:
            result = results[zone_id]
            incoming_warning = incoming.get(zone_id)
            final_status = max_status(
                result["operational_status"],
                incoming_warning["status"] if incoming_warning else "SAFE",
            )

            sensor_nodes = [
                {
                    "node": f"{node}_{zone_id[-2:]}",
                    "type": node,
                    "value": self.raw[zone_id][field],
                    "unit": unit,
                    "online": True,
                    "sequence": self.sequences[zone_id],
                    "crc_valid": True,
                }
                for node, field, unit in SENSOR_NODES
            ]

            next_zones[zone_id] = {
                **result,
                "operational_status": final_status,
                "incoming_warning": incoming_warning,
                "overridden": self.overridden[zone_id],
                "sensor_nodes": sensor_nodes,
                "last_updated": timestamp_ms,
            }

            prev = previous_zones.get(zone_id)
            if prev:
                if prev["operational_status"] != final_status:
                    self._push_event(f"{zone_id} status changed to {final_status}", timestamp_ms)
                if not prev["cascade"]["possible_landslide"] and result["cascade"]["possible_landslide"]:
                    self._push_event(f"Possible landslide detected at {zone_id}", timestamp_ms)
                if not prev["cascade"]["possible_blockage"] and result["cascade"]["possible_blockage"]:
                    self._push_event(f"Possible river blockage detected at {zone_id}", timestamp_ms)
                if not prev["cascade"]["possible_surge"] and result["cascade"]["possible_surge"]:
                    self._push_event(f"Downstream surge detected — propagating from {zone_id}", timestamp_ms)
                if not prev["incoming_warning"] and incoming_warning:
                    self._push_event(
                        f"{zone_id} placed on {incoming_warning['status']} ({incoming_warning['reason']})",
                        timestamp_ms,
                    )

        self.zones = next_zones
        self.last_sensor_update = timestamp_ms

    def tick(self):
        timestamp_ms = now_ms()
        for zone_id in self.zone_ids:
            if not self.overridden[zone_id]:
                self.raw[zone_id] = jitter_existing(self.raw[zone_id])
                self.sequences[zone_id] = (self.sequences[zone_id] + 1) % 256
        self._compute_all(timestamp_ms)

    def reset(self):
        for zone_id in self.zone_ids:
            self.raw[zone_id] = self._initial_reading(zone_id)
            self.overridden[zone_id] = False
            self.sequences[zone_id] = 0

        self.engine.blockage_memory = {}
        self.gateway = PacketGateway()
        self.gateway.engine = self.engine

        timestamp_ms = now_ms()
        self._seed_events(timestamp_ms)
        self.zones = {}
        self._compute_all(timestamp_ms)

    def set_override(self, zone_id, partial):
        self.overridden[zone_id] = True
        self.raw[zone_id] = {**self.raw[zone_id], **partial}
        self.sequences[zone_id] = (self.sequences[zone_id] + 1) % 256
        self._compute_all(now_ms())

    def clear_override(self, zone_id):
        self.overridden[zone_id] = False
        self._compute_all(now_ms())

    def apply_ingest(self, zone_id, field, value, sequence):
        # A real hardware reading takes over that zone from the simulator,
        # exactly like a manual override does.
        self.overridden[zone_id] = True
        self.raw[zone_id][field] = value
        self.sequences[zone_id] = sequence
        self._compute_all(now_ms())


state = DashboardState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async def simulation_loop():
        while True:
            await asyncio.sleep(TICK_INTERVAL_SECONDS)
            async with state.lock:
                state.tick()

    task = asyncio.create_task(simulation_loop())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(
    title="CascadeGuard API",
    description="Flash flood & cascade early-warning API for the Melamchi corridor.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SensorOverride(BaseModel):
    rainfall_mm_h: Optional[float] = Field(default=None, ge=0, le=500)
    soil_moisture: Optional[float] = Field(default=None, ge=0, le=1)
    tilt_change_deg: Optional[float] = Field(default=None, ge=0, le=90)
    upstream_rise_m_10m: Optional[float] = Field(default=None, ge=0, le=50)
    downstream_rise_m_10m: Optional[float] = Field(default=None, ge=0, le=50)

    @model_validator(mode="after")
    def require_at_least_one_field(self):
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("Provide at least one sensor field to override.")
        return self

    def provided_fields(self):
        return {key: value for key, value in self.model_dump().items() if value is not None}


class IngestRequest(BaseModel):
    packet: str = Field(min_length=1, description="Raw SOF|...|EOF framed sensor packet.")


def require_known_zone(zone_id: str):
    if zone_id not in state.zone_ids:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zone_id}' not found. Known zones: {', '.join(state.zone_ids)}.",
        )


@app.get("/")
async def root():
    return {"service": "CascadeGuard API", "status": "ONLINE", "docs": "/docs"}


@app.get("/health")
async def health():
    return {
        "status": "ONLINE" if state.system_online else "OFFLINE",
        "gateway": "CONNECTED" if state.gateway_connected else "DISCONNECTED",
        "last_sensor_update": state.last_sensor_update,
        "message": "CascadeGuard API is running.",
    }


@app.get("/zones")
async def list_zones():
    return [state.zones[zone_id] for zone_id in state.zone_ids]


@app.get("/latest-risk")
async def latest_risk():
    return [state.zones[zone_id] for zone_id in state.zone_ids]


@app.get("/zones/{zone_id}")
async def get_zone(zone_id: str):
    require_known_zone(zone_id)
    return state.zones[zone_id]


@app.get("/events")
async def get_events():
    return state.events


@app.post("/reset")
async def reset_demo():
    async with state.lock:
        state.reset()
    return {"status": "RESET", "message": "Demo state reset to baseline readings."}


@app.post("/zones/{zone_id}/override")
async def override_zone(zone_id: str, payload: SensorOverride):
    require_known_zone(zone_id)
    async with state.lock:
        state.set_override(zone_id, payload.provided_fields())
        zone = state.zones[zone_id]
    return {
        "status": "OVERRIDE_APPLIED",
        "message": f"Manual override applied to {zone_id}; simulation paused for this zone.",
        "zone": zone,
    }


@app.delete("/zones/{zone_id}/override")
async def clear_zone_override(zone_id: str):
    require_known_zone(zone_id)
    async with state.lock:
        state.clear_override(zone_id)
        zone = state.zones[zone_id]
    return {
        "status": "OVERRIDE_CLEARED",
        "message": f"Override cleared for {zone_id}; resuming simulated live feed.",
        "zone": zone,
    }


@app.post("/ingest")
async def ingest_packet(payload: IngestRequest, response: Response):
    async with state.lock:
        result = state.gateway.process_packet(payload.packet)
        status = result["status"]

        if status == "REJECTED":
            raise HTTPException(status_code=400, detail=f"Packet rejected: {result['reason']}")

        if status == "DUPLICATE":
            return {
                "status": "DUPLICATE",
                "message": (
                    f"Duplicate packet ignored — sequence {result['sequence']} "
                    f"already processed for node {result['node_id']}."
                ),
                **result,
            }

        if status == "WAITING":
            zone_id = result["zone_id"]
            field = state.gateway.SENSOR_MAP[result["sensor_type"]]
            state.apply_ingest(zone_id, field, result["value"], result["sequence"])
            response.status_code = 202
            return {
                "status": "WAITING",
                "message": (
                    f"Reading accepted for {zone_id}; waiting on "
                    f"{len(result['missing'])} more sensor field(s) before evaluation."
                ),
                **result,
            }

        # EVALUATED
        zone_id = result["result"]["zone_id"]
        field = state.gateway.SENSOR_MAP[result["updated_sensor"]]
        value = state.gateway.zone_state[zone_id][field]
        state.apply_ingest(zone_id, field, value, result["sequence"])
        return {
            "status": "EVALUATED",
            "message": f"{zone_id} evaluated — alert level {result['result']['alert_level']}.",
            **result,
        }
