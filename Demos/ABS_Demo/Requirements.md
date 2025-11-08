# ABS ECU Demo — Requirements (Extract)

**Bitrate:** 125 kbit/s (SocketCAN `can0`)
**GPIO:** libgpiod v2.2.3 (Python bindings `gpiod`)
**PWM Target:** 500 Hz (demo LED)
**CAN IDs:** Command `0x180`, Heartbeat `0x280`

## Functional

* **F-1:** Subscribe to `0x180` (Brake_Req_Level).
* **F-2:** Payload:

  * Byte0 = `Level` (0–100)
  * Byte1 = `RollingCounter` (0–15)
  * Byte2 = `Checksum` (8-bit, complement of `(Level + Counter)`),
  * Bytes3–7 = `0x00`.
* **F-3:** Map `Level` → PWM duty % linearly.
* **F-4:** PWM frequency = **500 Hz ± 10 %**.
* **F-5:** Apply new duty within **5 ms** after valid frame.
* **F-6:** Heartbeat `0x280` every **200 ms ± 50 ms**:

  * Byte0 = `AliveCounter` (0–255, wraps)
  * Byte1 = `FaultBits`
  * Bytes2–7 = `0x00`.

## Performance

* **P-1:** End-to-end latency ≤ 5 ms (95th percentile).
* **P-2:** Update jitter ≤ 2 ms (95th percentile).
* **P-3:** PWM duty accuracy ≤ 2 % (for mid-range levels), ≤ 3 % at extremes.
* **P-4:** ECU operates without frame loss or false faults at ≤ 70 % CAN bus load.

## Robustness

* **S-1:** **Timeout > 500 ms** → force duty 0 %, set **Timeout** fault bit; clear when valid frame received.
* **S-2:** **Level > 100** → clamp to 100 %, set **Range** fault bit for **500 ms**.
* **S-3:** **Bad checksum** → ignore frame; set **ChkFail** fault bit for **500 ms**, then clear.
* **S-4:** **RollingCounter jump > 1 (mod 16)** → log discontinuity (non-latching).
* **S-5:** **Bus-off** → force duty 0 %, set **BusOff** bit until bus recovery.
* **S-6:** **Power-on** ≤ 100 ms → LED 0 %, heartbeat active.

## Diagnostics

* **D-1:** Log `Timeout`, `ChkFail`, `Range`, `BusOff`, and `Counter-Jump` events with timestamps.
* **D-2:** On startup, log build ID and configuration parameters (bitrate, CAN IDs, GPIO, timeouts).
