# test_led_button_no_ssh.py
#
# Pytest to validate DUT's led_button.c behavior using the test bed Pi's GPIO.
# Converted to modern libgpiod python bindings (v2.x): LineSettings + Chip.request_lines
#
# DUT (Pi #1): runs led_button with LED on GPIO17, Button on GPIO27 (pull-up).
# Test Bed (Pi #2): drives DUT's button via TB_GPIO_PRESS and reads DUT's LED via TB_GPIO_SENSE.
#
# Wiring (include 1 kΩ series resistors and common ground):
#   TestBed GPIO5  --1k-->  DUT GPIO27      (button line)
#   DUT GPIO17     --1k-->  TestBed GPIO6   (LED sense)
#   GND <-------------------------------> GND
#
# Behavior checked:
#   - Release (TB high-Z): LED should be OFF (0)
#   - Press   (TB drives LOW): LED should be ON (1)
#   - Release again: LED should be OFF (0)

import os
import time
import contextlib
import pytest

try:
    import gpiod  # Python bindings for libgpiod (v2.x)
except Exception as e:
    pytest.skip(f"python3-libgpiod not available: {e}", allow_module_level=True)

# ---------------------------- Configurable pins ----------------------------
TB_GPIOCHIP_NAME = os.getenv("TB_GPIOCHIP_NAME", "gpiochip0")  # test bed chip (e.g. "gpiochip0" or "/dev/gpiochip0")
TB_GPIO_PRESS = int(os.getenv("TB_GPIO_PRESS", "5"))           # drives DUT button
TB_GPIO_SENSE = int(os.getenv("TB_GPIO_SENSE", "6"))           # reads DUT LED

# Docs only (don’t affect test bed configuration)
DUT_BUTTON_GPIO = 27
DUT_LED_GPIO = 17

# Timing (tune if needed to match DUT loop/usleep)
SETTLE_S = float(os.getenv("SETTLE_S", "0.15"))  # allow DUT to observe change
RETRIES = int(os.getenv("RETRIES", "5"))
RETRY_DELAY_S = float(os.getenv("RETRY_DELAY_S", "0.05"))
STABILIZE_S = float(os.getenv("STABILIZE_S", "0.05"))

# ----------------------------- gpiod helpers ------------------------------

def _chip_path(chip_name: str) -> str:
    """Return a filesystem path for the chip name (accepts either 'gpiochip0' or '/dev/gpiochip0')."""
    if chip_name.startswith("/dev/"):
        return chip_name
    return f"/dev/{chip_name}"

@contextlib.contextmanager
def open_chip(chip_name: str):
    chip = gpiod.Chip(path=_chip_path(chip_name))
    try:
        yield chip
    finally:
        chip.close()

def _value_to_int(val) -> int:
    """Convert a gpiod.Value (ACTIVE/INACTIVE) to an int 0/1.
    ACTIVE -> 1, INACTIVE -> 0. If an int-like is passed, coerce to int."""
    try:
        # gpiod.Value.ACTIVE / INACTIVE are Enum-like
        if val == gpiod.Value.ACTIVE:
            return 1
        if val == gpiod.Value.INACTIVE:
            return 0
    except Exception:
        pass
    # fallback: try numeric conversion
    try:
        return int(val)
    except Exception:
        # if unknown, return 0 to be conservative
        return 0

def request_output_low(chip: gpiod.Chip, line_num: int) -> gpiod.LineRequest:
    """Request a line as OUTPUT driven LOW (simulate 'press').

    Returns the LineRequest object (caller must call .release()).
    """
    settings = gpiod.LineSettings(direction=gpiod.line.Direction.OUTPUT)
    # Request the line and set its output value to INACTIVE (logical 0)
    req = chip.request_lines(
        config={line_num: settings},
        consumer="pytest-led-button",
        output_values={line_num: gpiod.Value.INACTIVE},
    )
    return req

def request_input(chip: gpiod.Chip, line_num: int) -> gpiod.LineRequest:
    """Request a line as INPUT (high-Z from the test bed side; simulate 'release').

    Returns the LineRequest object (caller must call .release()).
    """
    settings = gpiod.LineSettings(direction=gpiod.line.Direction.INPUT)
    req = chip.request_lines(config={line_num: settings}, consumer="pytest-led-button")
    return req

def read_input_from_request(req: gpiod.LineRequest, line: int) -> int:
    """Read a single logical value (0/1) from a LineRequest for a line offset."""
    v = req.get_value(line)
    return _value_to_int(v)

def sample_led(chip: gpiod.Chip) -> int:
    """One-shot sample of DUT LED level via the sense pin.

    Requests the sense line as INPUT, reads it, then releases.
    """
    req = request_input(chip, TB_GPIO_SENSE)
    try:
        time.sleep(STABILIZE_S)
        return read_input_from_request(req, TB_GPIO_SENSE)
    finally:
        req.release()

# ------------------------------- Fixtures ---------------------------------

@pytest.fixture(scope="module")
def tb_chip():
    with open_chip(TB_GPIOCHIP_NAME) as chip:
        yield chip

# -------------------------------- Tests -----------------------------------

@pytest.mark.timeout(15)
def test_led_follows_press_and_release(tb_chip):
    """
    Sequence:
      1) Release (TB high-Z): expect LED OFF (0)
      2) Press   (TB LOW):   expect LED ON  (1)
      3) Release again:      expect LED OFF (0)
    """

    # ---- Step 1: Release (TB high-Z) ----
    rel = request_input(tb_chip, TB_GPIO_PRESS)  # high-Z on TB -> DUT sees pull-up (1)
    try:
        time.sleep(SETTLE_S)
        off_seen = False
        last = None
        for _ in range(RETRIES):
            last = sample_led(tb_chip)
            if last == 0:
                off_seen = True
                break
            time.sleep(RETRY_DELAY_S)
        assert off_seen, f"Expected LED OFF (0) when released; last read {last}"
    finally:
        rel.release()

    # ---- Step 2: Press (TB drives LOW) ----
    press_req = request_output_low(tb_chip, TB_GPIO_PRESS)  # drive low -> DUT reads 0 (pressed)
    try:
        # NOTE: We intentionally keep the request active for the duration of the "press".
        time.sleep(SETTLE_S)
        on_seen = False
        last = None
        for _ in range(RETRIES):
            last = sample_led(tb_chip)
            if last == 1:
                on_seen = True
                break
            time.sleep(RETRY_DELAY_S)
        assert on_seen, f"Expected LED ON (1) when pressed; last read {last}"
    finally:
        press_req.release()

    # ---- Step 3: Release again (TB high-Z) ----
    rel2 = request_input(tb_chip, TB_GPIO_PRESS)
    try:
        time.sleep(SETTLE_S)
        off_again = False
        last = None
        for _ in range(RETRIES):
            last = sample_led(tb_chip)
            if last == 0:
                off_again = True
                break
            time.sleep(RETRY_DELAY_S)
        assert off_again, f"Expected LED OFF (0) after release; last read {last}"
    finally:
        rel2.release()
