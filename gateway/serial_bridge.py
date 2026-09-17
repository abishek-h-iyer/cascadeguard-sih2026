import json
import serial
import requests

SERIAL_PORT = "COM6"
BAUD_RATE = 9600
API_URL = "http://127.0.0.1:8000/ingest"


def main():
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        print(f"Listening on {SERIAL_PORT} at {BAUD_RATE} baud")
        print(f"Forwarding packets to {API_URL}")

        while True:
            raw = ser.readline()

            if not raw:
                continue

            packet = raw.decode("utf-8", errors="replace").strip()

            if not packet:
                continue

            print(f"\nRX: {packet}")

            try:
                response = requests.post(
                    API_URL,
                    json={"packet": packet},
                    timeout=3
                )

                print(f"HTTP {response.status_code}")

                try:
                    data = response.json()
                    print(json.dumps(data, indent=2))
                except ValueError:
                    print(response.text)

            except requests.RequestException as error:
                print(f"API ERROR: {error}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBridge stopped.")