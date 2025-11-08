/*
 * led_button.c
 * Turn an LED on/off based on a button press using libgpiod.
 *
 * Button: GPIO 27 (configured as input with internal pull-up)
 * LED:    GPIO 17 (output)
 * When button pressed  -> LED ON
 * When button released -> LED OFF
 */

#include <stdio.h>
#include <stdlib.h>
#include <gpiod.h>      // Library for GPIO operations
#include <unistd.h>     // For sleep()
#include <signal.h>     // For signal handling

#define LED_GPIO 17     // The GPIO number connected to the LED
#define BUTTON_GPIO 27  // The GPIO number connected to the BUTTON
#define CONSUMER "LED_BUTTON_APP"

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
    struct gpiod_chip *chip;
    struct gpiod_line_request *line_request;            // Handle to the specific GPIO line
    struct gpiod_request_config *req_cfg;       
    struct gpiod_line_config *line_cfg;
    struct gpiod_line_settings *led_line_setting,*button_line_setting;
    int ret, button_state;

    // Register signal handler
    signal(SIGINT, handle_sigint);
    
    // Open GPIO chip
    chip = gpiod_chip_open("/dev/gpiochip0");
    if (!chip) {
       exit_with_error("gpiochip0 open failed");
    }

    // Create new Line Config
    line_cfg=gpiod_line_config_new();

    // Create a new line setting for LED
    led_line_setting=gpiod_line_settings_new();
    // Set output direction
    ret=gpiod_line_settings_set_direction(led_line_setting,GPIOD_LINE_DIRECTION_OUTPUT);
    if (ret < 0) {
        gpiod_chip_close(chip);
        exit_with_error("led line setting set direction to output failed");
    }
    // Set initial value for the output pin
    ret=gpiod_line_settings_set_output_value(led_line_setting,GPIOD_LINE_VALUE_INACTIVE);
    if (ret < 0) {
        gpiod_chip_close(chip);
        exit_with_error("led line setting set value to inactive failed");
    }

    // add the led line setting to line config
    ret=gpiod_line_config_add_line_settings(line_cfg, (unsigned int[]){LED_GPIO},1,led_line_setting);
    if (ret < 0) {
        gpiod_chip_close(chip);
        exit_with_error("line config add button line setting failed");
    }

    // Create a new line setting for BUTTON
    button_line_setting=gpiod_line_settings_new();
    // Set direction as input
    ret=gpiod_line_settings_set_direction(button_line_setting,GPIOD_LINE_DIRECTION_INPUT);
    if (ret < 0) {
        gpiod_chip_close(chip);
        exit_with_error("button line setting set direction to output failed");
    }
    // Set line bias to internal pull up
    ret=gpiod_line_settings_set_bias(button_line_setting,GPIOD_LINE_BIAS_PULL_UP);
    if (ret < 0) {
        gpiod_chip_close(chip);
        exit_with_error("button line setting set bias to internal pull up failed");
    }
    // add the button line setting to line config
    ret=gpiod_line_config_add_line_settings(line_cfg, (unsigned int[]){BUTTON_GPIO},1,button_line_setting);
    if (ret < 0) {
        gpiod_chip_close(chip);
        exit_with_error("line config add button line setting failed");
    }
    
    // Create new Request Config
    req_cfg=gpiod_request_config_new();
    gpiod_request_config_set_consumer(req_cfg, CONSUMER);

    // Get the GPIO line request corresponding to the LED and BUTTON
    line_request = gpiod_chip_request_lines(chip,req_cfg,line_cfg);
    if (!line_request) {
        gpiod_chip_close(chip);
        exit_with_error("Get line request failed");
    }
    // Free up the settings and config objects
    gpiod_line_settings_free(led_line_setting);
    gpiod_line_settings_free(button_line_setting);
    gpiod_line_config_free(line_cfg);
    gpiod_request_config_free(req_cfg);

    printf("Press the button on GPIO %d to turn LED on GPIO %d ON.\n", BUTTON_GPIO, LED_GPIO);

    while (keep_running) {
        // Read button state (1 = not pressed, 0 = pressed)
        button_state = gpiod_line_request_get_value(line_request,BUTTON_GPIO);
        if (button_state < 0) {
            perror("Read button state failed");
            break;
        }

        // LED should be ON when button is pressed (button_state = 0)
        gpiod_line_request_set_value(line_request,LED_GPIO, !button_state);

        // Small delay to debounce and reduce CPU usage
        usleep(100000); // 100 ms
    }

    // Release resources
    gpiod_line_request_set_value(line_request, LED_GPIO,0);
    gpiod_line_request_release(line_request);
    gpiod_chip_close(chip);

    return 0;
}
