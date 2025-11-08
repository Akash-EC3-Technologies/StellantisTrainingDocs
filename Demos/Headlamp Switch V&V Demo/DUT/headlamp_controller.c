/*
 * headlamp_controller.c
 * DUT firmware: Headlamp switch → lamp output with debounce and latency targets.
 * 
 * Compatible with libgpiod v2.x (tested 2.2.1)
 *
 * SWITCH_IN: GPIO 27 (input, default pull-up; pressed = 0)
 * LAMP_OUT : GPIO 17 (output, active high)
 *
 * Requirements covered: HL-REQ-001..006
 */

#include <gpiod.h>      // libgpiod v2.x API
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>     // usleep
#include <time.h>
#include <errno.h>

#define CHIP_PATH   "/dev/gpiochip0"   // Raspberry Pi main chip
#define GPIO_SWITCH 27            // BCM pin for headlamp switch
#define GPIO_LAMP   17            // BCM pin for lamp output
#define CONSUMER    "HEADLAMP_CTRL"

// Debounce threshold (ms)
#define DEBOUNCE_MS 5
// Loop timing in ms (for liveness requirement)
#define LOOP_DELAY_MS 2

int main(void)
{
    struct gpiod_chip *chip = NULL;
    struct gpiod_line *sw_line = NULL;
    struct gpiod_line *lamp_line = NULL;
    int ret;

    // ---- 1. Open GPIO chip ----
    chip = gpiod_chip_open(CHIP_PATH);
    if (!chip) {
        perror("Failed to open GPIO chip");
        return 1;
    }

    // ---- 2. Request the lamp output line (GPIO 17) ----
    struct gpiod_line_settings *lamp_settings = gpiod_line_settings_new();
    gpiod_line_settings_set_direction(lamp_settings, GPIOD_LINE_DIRECTION_OUTPUT);
    gpiod_line_settings_set_output_value(lamp_settings, GPIOD_LINE_VALUE_INACTIVE); // Start OFF

    struct gpiod_request_config *lamp_req_cfg = gpiod_request_config_new();
    gpiod_request_config_set_consumer(lamp_req_cfg, CONSUMER);

    struct gpiod_line_config *lamp_config = gpiod_line_config_new();
    unsigned int lamp_offset = GPIO_LAMP;
    gpiod_line_config_add_line_settings(lamp_config, &lamp_offset, 1, lamp_settings);

    struct gpiod_line_request *lamp_req =
        gpiod_chip_request_lines(chip, lamp_req_cfg, lamp_config);

    if (!lamp_req) {
        perror("Failed to request lamp line");
        gpiod_chip_close(chip);
        return 1;
    }

    // ---- 3. Request the switch input line (GPIO 27) ----
    struct gpiod_line_settings *sw_settings = gpiod_line_settings_new();
    gpiod_line_settings_set_direction(sw_settings, GPIOD_LINE_DIRECTION_INPUT);
    gpiod_line_settings_set_bias(sw_settings,GPIOD_LINE_BIAS_PULL_UP);
    
    // (HL-REQ-003: Debounce pulses shorter than 5 ms)
    gpiod_line_settings_set_debounce_period_us(sw_settings, DEBOUNCE_MS*1000);
    
    struct gpiod_request_config *sw_req_cfg = gpiod_request_config_new();
    gpiod_request_config_set_consumer(sw_req_cfg, CONSUMER);

    struct gpiod_line_config *sw_config = gpiod_line_config_new();
    unsigned int sw_offset = GPIO_SWITCH;
    gpiod_line_config_add_line_settings(sw_config, &sw_offset, 1, sw_settings);

    struct gpiod_line_request *sw_req =
        gpiod_chip_request_lines(chip, sw_req_cfg, sw_config);

    if (!sw_req) {
        perror("Failed to request switch line");
        gpiod_line_request_release(lamp_req);
        gpiod_chip_close(chip);
        return 1;
    }

    printf("Headlamp controller running: SWITCH=%u, LAMP=%u\n",
           GPIO_SWITCH, GPIO_LAMP);

    // ---- 4. Initialize states ----
    // Ensure LAMP OFF at startup (HL-REQ-004)
    gpiod_line_request_set_value(lamp_req, lamp_offset, GPIOD_LINE_VALUE_INACTIVE);

    // ---- 5. Control loop ----
    while (1) {
        int val = gpiod_line_request_get_value(sw_req, sw_offset);
        if (val < 0) {
            perror("Read switch failed");
            break;
        }

        gpiod_line_request_set_value(lamp_req, lamp_offset, (val == 0));

        // Loop at ~2 ms period (HL-REQ-005)
        usleep(LOOP_DELAY_MS * 1000);
    }

    // ---- 6. Cleanup ----
    gpiod_line_request_release(sw_req);
    gpiod_line_request_release(lamp_req);
    gpiod_chip_close(chip);

    gpiod_line_settings_free(lamp_settings);
    gpiod_line_settings_free(sw_settings);
    gpiod_line_config_free(lamp_config);
    gpiod_line_config_free(sw_config);
    gpiod_request_config_free(lamp_req_cfg);
    gpiod_request_config_free(sw_req_cfg);

    return 0;
}
