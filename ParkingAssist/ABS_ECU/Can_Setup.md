# Setup CAN in Raspberry Pi

## Prerequisites

-   Raspberry Pi5
-   MCP2515 CAN module (8MHz oscillator)
-   Jumper wires

## Hardware Connections

### MCP2515 to Raspberry Pi Connection

| MCP2515 Pin      | Raspberry Pi GPIO Pin  | Physical Pin Number |
| ---------------- | ---------------------- | ------------------- |
| VCC              | 5V Power               | Pin 4               |
| GND              | Ground                 | Pin 6               |
| CS (Chip Select) | GPIO8 (SPI CE0)        | Pin 24              |
| SO (MISO)        | GPIO9 (MISO)           | Pin 21              |CAN/BrakePedal/README.md
| SI (MOSI)        | GPIO10 (MOSI)          | Pin 19              |
| SCK (Clock)      | GPIO11 (SCLK)          | Pin 23              |
| INT              | GPIO25                 | Pin 22              |
| CANH             | (To other CAN devices) | -                   |
| CANL             | (To other CAN devices) | -                   |

**Termination Resistor Connection:**

```
CANH ───╮
        │ 120Ω
CANL ───╯
```

**Pinout Reference**:

```text
Raspberry Pi 5 GPIO Header (J8)
┌─────────┬──────────┐
│ 1 3.3V  │ 2 5V     │
│ 3 GPIO2 │ 4 5V     │
│ 5 GPIO3 │ 6 GND    │
│ ...     │ ...      │
│ 19 MOSI │ 20 GND   │
│ 21 MISO │ 22 GPIO25|
│ 23 SCLK │ 24 CE0   │
└─────────┴──────────┘
```

## Instructions to setup Raspberry pi

### 1. Configure System

```bash
# Install dependencies
sudo apt update
sudo apt install -y can-utils vim
```

### 2. Enable SPI Interface

```bash
sudo raspi-config # Navigate to Interface Options → SPI → Enable
```

### 3. Load device tree overlay for the MCP2515 CAN

-   open /boot/firmware/config.txt

```bash
sudo vim /boot/firmware/config.txt
```

-   Add this to the bottom of the config.txt:

```text
dtoverlay=mcp2515-can0,oscillator=8000000,interrupt=25,spimaxfrequency=1000000
```

-   Reboot

```
sudo reboot
```

### 4. Configure CAN Interface

```bash
# Bring down interface if up
sudo ip link set can0 down

sudo ip link set can0 up type can bitrate 125000

# Verify interface
ip -d link show can0
# Should show "state ERROR-ACTIVE"
```
