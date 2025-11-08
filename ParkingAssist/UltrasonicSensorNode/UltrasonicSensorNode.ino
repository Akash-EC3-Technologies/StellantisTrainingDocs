/*
  Ultrasonic_Sensor_Node.ino
  -------------------------
  Reads an HC-SR04 ultrasonic sensor and sends the reading periodically over CAN
  using an MCP2515 module. Each CAN frame (ID 0x100) is 8 bytes:
    bytes 0..1: distance (mm, big-endian)
    byte 2    : counter (wrap 0..255)
    byte 3    : status (0=OK,1=timeout,2=out_of_range)
    bytes 4..6: reserved (0)
    byte 7    : CRC8 over bytes 0..6 (poly 0x07)

  Requirements:
  - Install MCP_CAN library (e.g. "MCP_CAN by Cory J.")
  - Connect HC-SR04 and MCP2515 per WIRING_DIAGRAM.txt
*/

#include <SPI.h>
#include "mcp_can.h"

// === Configurable pins ===
#define CS_PIN 10        // MCP2515 CS pin
#define HC_TRIG 8        // HC-SR04 TRIG pin
#define HC_ECHO 7        // HC-SR04 ECHO pin

// === CAN object ===
MCP_CAN CAN(CS_PIN);     // Create CAN object with CS pin

// transmit counter increments every send
uint8_t counter = 0;

// ----------------------------------------------------------------------------
// CRC-8 (polynomial 0x07) function
// Computes CRC8 over `len` bytes starting at `data`.
// The CRC is computed with MSB-first bit order.
uint8_t crc8(const uint8_t *data, uint8_t len) {
  uint8_t crc = 0;
  for (uint8_t i = 0; i < len; ++i) {
    crc ^= data[i];
    // process 8 bits
    for (uint8_t b = 0; b < 8; ++b) {
      if (crc & 0x80) crc = (uint8_t)((crc << 1) ^ 0x07);
      else crc <<= 1;
    }
  }
  return crc;
}
// ----------------------------------------------------------------------------

// Setup: initialize Serial communication, pins, and MCP2515 CAN controller
void setup() {
  Serial.begin(115200);
  // Setup HC-SR04 pins
  pinMode(HC_TRIG, OUTPUT);
  pinMode(HC_ECHO, INPUT);
  digitalWrite(HC_TRIG, LOW);
  delay(50);

  // Initialize MCP2515
  if (CAN.begin(MCP_ANY, CAN_125KBPS, MCP_8MHZ) == CAN_OK) {
    Serial.println("MCP2515 initialized successfully");
  } else {
    Serial.println("MCP2515 init fail - check wiring");
    // If CAN init fails, halt here to avoid sending garbage on the bus.
    while (1);
  }

  // Set to normal mode to enable sending and receiving
  CAN.setMode(MCP_NORMAL);
  Serial.println("Ready to send ultrasonic data over CAN (ID 0x100)");
}

// read_hc: triggers the HC-SR04 and measures echo pulse width.
//
// Returns:
//   - distance in millimeters (uint16_t) on success
//   - 0xFFFF on timeout (no echo within timeout)
uint16_t read_hc() {
  // ensure trigger low for a short time
  digitalWrite(HC_TRIG, LOW);
  delayMicroseconds(2);

  // 10 microsecond trigger pulse
  digitalWrite(HC_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(HC_TRIG, LOW);

  // wait for echo pulse; timeout after 30000 microseconds (30 ms)
  unsigned long duration = pulseIn(HC_ECHO, HIGH, 30000UL);
  if (duration == 0) {
    // No echo detected within timeout
    return 0xFFFF;
  }
  // Convert microseconds to mm.
  // Approx conversion: distance_cm = duration_us / 58
  // therefore distance_mm = duration_us / 58 * 10 = duration_us / 5.8
  // Using integer math: use duration / 58 to get cm, then *10 for mm might overflow for large durations.
  // Simpler: distance_mm = duration_us / 58
  uint16_t mm = (uint16_t)(duration58UL * 0.1715);
  return mm;
}

// ----------------------------------------------------------------------------
// main loop: take a measurement every 100 ms, pack into CAN frame, compute CRC and send.
void loop() {
  uint16_t dist = read_hc();   // read distance
  Serial.print("dist(mm): ");
  Serial.println(dist);
  uint8_t status = 0;          // default: OK

  // set status based on result
  if (dist == 0xFFFF) {
    status = 1; // timeout
    dist = 0;   // store 0 in payload to avoid 0xFFFF confusion on receiver side
  } else if (dist > 4000) {
    status = 2; // out of range
  }
  // build 8-byte frame
  uint8_t frame[8];
  frame[0] = (uint8_t)((dist >> 8) & 0xFF); // high byte
  frame[1] = (uint8_t)(dist & 0xFF);        // low byte
  frame[2] = counter++;                     // data counter, increments each send
  frame[3] = status;                        // status code
  frame[4] = 0; frame[5] = 0; frame[6] = 0; // reserved bytes
  // compute CRC8 over bytes 0..6 and store in byte 7
  frame[7] = crc8(frame, 7);

  // send CAN message with ID 0x100, standard frame (not extended)
  unsigned char sendStat = CAN.sendMsgBuf(0x100, 0, 8, frame);
  if (sendStat == CAN_OK) {
    // Log to serial for debugging
    Serial.print("Sent dist(mm): ");
    Serial.print(dist);
    Serial.print("  cnt: ");
    Serial.print(frame[2] - 1); // counter was post-incremented
    Serial.print("  status: ");
    Serial.print(status);
    Serial.print("  crc: 0x");
    Serial.println(frame[7], HEX);
  } else {
    Serial.println("CAN send failed");
  }

  // Wait ~100 ms between transmissions
  delay(100);
}
