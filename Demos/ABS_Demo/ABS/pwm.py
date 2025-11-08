import os
import time

def pwm_path(chip: int, channel: int) -> str:
    """Return the sysfs path for the given PWM chip/channel."""
    return f"/sys/class/pwm/pwmchip{chip}/pwm{channel}"

def export_pwm(chip: int, channel: int):
    """Export the PWM channel if it's not already exported."""
    pwm_dir = pwm_path(chip, channel)
    if not os.path.exists(pwm_dir):
        with open(f"/sys/class/pwm/pwmchip{chip}/export", "w") as f:
            f.write(str(channel))
        # Give kernel time to create sysfs entries
        time.sleep(0.1)

def unexport_pwm(chip: int, channel: int):
    """Unexport the PWM channel (optional cleanup)."""
    pwm_dir = pwm_path(chip, channel)
    if os.path.exists(pwm_dir):
        with open(f"/sys/class/pwm/pwmchip{chip}/unexport", "w") as f:
            f.write(str(channel))

def enable(chip: int, channel: int, frequency_hz: float, duty_percent: float):
    """
    Enable hardware PWM with specified frequency (Hz) and duty cycle (%).
    Example: enable_pwm(0, 0, 1000, 50) → 1 kHz, 50% duty
    """
    export_pwm(chip, channel)
    pwm_dir = pwm_path(chip, channel)

    # Compute period and duty in nanoseconds
    period_ns = int(1_000_000_000 / frequency_hz)
    duty_cycle_ns = int(period_ns * (duty_percent / 100.0))

    # Disable before configuration
    with open(f"{pwm_dir}/enable", "w") as f:
        f.write("0")

    # Write period and duty cycle
    with open(f"{pwm_dir}/period", "w") as f:
        f.write(str(period_ns))

    with open(f"{pwm_dir}/duty_cycle", "w") as f:
        f.write(str(duty_cycle_ns))

    # Enable PWM
    with open(f"{pwm_dir}/enable", "w") as f:
        f.write("1")

def set_duty_cycle(chip: int, channel: int, duty_percent: float):
    """Update only the duty cycle (in %)."""
    pwm_dir = pwm_path(chip, channel)
    with open(f"{pwm_dir}/period", "r") as f:
        period_ns = int(f.read().strip())
    duty_cycle_ns = int(period_ns * (duty_percent / 100.0))

    with open(f"{pwm_dir}/duty_cycle", "w") as f:
        f.write(str(duty_cycle_ns))

def disable(chip: int, channel: int):
    """Disable PWM output."""
    pwm_dir = pwm_path(chip, channel)
    if os.path.exists(f"{pwm_dir}/enable"):
        with open(f"{pwm_dir}/enable", "w") as f:
            f.write("0")
    unexport_pwm(chip, channel)
