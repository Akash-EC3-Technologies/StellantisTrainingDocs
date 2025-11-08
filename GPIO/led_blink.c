/*
 * led_blink.c
 * Simple example to blink an LED connected to GPIO 17 using libgpiod.
 */

#include <stdio.h>
#include <stdlib.h>
#include <gpiod.h>      // Library for GPIO operations
#include <unistd.h>     // For sleep()
#include <signal.h>     // For signal handling

#define LED_GPIO 17     // The GPIO number connected to the LED
#define CONSUMER "LED_BLINK_APP"

// Signal handler for Ctrl+C
static volatile int keep_running = 1; // Flag to control main loop
void handle_sigint(int sig)
{
    printf("\nCaught SIGINT (Ctrl+C). Cleaning up and exiting...\n");
    keep_running = 0;  // Stop main loop
}

void exit_with_error(const char* msg){
    perror(msg);
    exit(1);
}

int main(void)
{
    struct gpiod_chip *chip;                    // Handle to the GPIO chip
    struct gpiod_line_request *line;            // Handle to the specific GPIO line
    struct gpiod_request_config *req_cfg;       
    struct gpiod_line_config *line_cfg;
    struct gpiod_line_settings *line_setting;
    const unsigned int line_offsets[1]={LED_GPIO};
    int ret;

    // Register signal handler
    signal(SIGINT, handle_sigint);

    // Open GPIO chip
    chip = gpiod_chip_open("/dev/gpiochip0");
    if (!chip) {
       exit_with_error("gpiochip0 open failed");
    }

    // Create new Line Config
    line_cfg=gpiod_line_config_new();

    // Create a new line Setting
    line_setting=gpiod_line_settings_new();
    // Set output direction
    ret=gpiod_line_settings_set_direction(line_setting,GPIOD_LINE_DIRECTION_OUTPUT);
    if (ret < 0) {
        gpiod_chip_close(chip);
        exit_with_error("line setting set direction to output failed");
    }
    // Set initial value for the output pin
    ret=gpiod_line_settings_set_output_value(line_setting,GPIOD_LINE_VALUE_INACTIVE);
    if (ret < 0) {
        gpiod_chip_close(chip);
        exit_with_error("line setting set value to inactive failed");
    }
    // add the setting to the line config
    ret=gpiod_line_config_add_line_settings(line_cfg, line_offsets,1,line_setting);
    if (ret < 0) {
        gpiod_chip_close(chip);
        exit_with_error("line config add line setting failed");
    }
    
    // Create new Request Config
    req_cfg=gpiod_request_config_new();
    gpiod_request_config_set_consumer(req_cfg, CONSUMER);

    
    // Get the GPIO line corresponding to the LED
    line = gpiod_chip_request_lines(chip,req_cfg,line_cfg);
    if (!line) {
        gpiod_chip_close(chip);
        exit_with_error("Get line request failed");
    }
    // Free up the settings and config objects
    gpiod_line_settings_free(line_setting);
    gpiod_line_config_free(line_cfg);
    gpiod_request_config_free(req_cfg);

    printf("Blinking LED on GPIO %d...\n", LED_GPIO);
    while (keep_running) {
        // Turn LED on
        gpiod_line_request_set_value(line,LED_GPIO, GPIOD_LINE_VALUE_ACTIVE);
        printf("LED ON\n");
        sleep(1); // wait 1 second

        // Turn LED off
        gpiod_line_request_set_value(line,LED_GPIO, GPIOD_LINE_VALUE_INACTIVE);
        printf("LED OFF\n");
        sleep(1); // wait 1 second
    }

    // Release resources
    gpiod_line_request_set_value(line, LED_GPIO,0);
    gpiod_line_request_release(line);
    gpiod_chip_close(chip);
    return 0;
}
