# YPGym IoT Scanner Simulator

The simulator calls the same HTTP contract intended for an ESP32, Raspberry Pi, or tablet scanner. It never connects to PostgreSQL.

From this directory, run the seeded local device after copying a live token from `/app/qr`:

```powershell
python -m app.main --scenario valid --token "<QR_TOKEN>"
python -m app.main --scenario duplicate --token "<QR_TOKEN>"
python -m app.main --scenario invalid-token
python -m app.main --scenario unauthorized-device --token "<QR_TOKEN>"
```

The optional Compose profile uses the same environment values:

```powershell
$env:QR_TOKEN="<QR_TOKEN>"
docker compose --profile iot run --rm iot-simulator python -m app.main --scenario valid --token $env:QR_TOKEN
```

Expired and inactive scenarios require tokens captured from an intentionally prepared development account in `EXPIRED_QR_TOKEN` or `INACTIVE_QR_TOKEN`; the simulator does not forge signed tokens.

Each attempt prints its HTTP status and structured API response. The `duplicate` scenario repeats the same scan, while `unauthorized-device` deliberately substitutes an invalid API key; both exercise server-side guards without connecting directly to PostgreSQL.
