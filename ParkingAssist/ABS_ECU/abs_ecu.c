/*
 abs_ecu.c

 ABS ECU daemon for Raspberry Pi (C):
 - Listens on SocketCAN interface for ultrasonic frames (CAN ID 0x100)
 - Validates CRC8 (poly 0x07) over bytes 0..6
 - Computes brake percentage when distance < threshold and applies PWM percentage
   using sysfs PWM interface: /sys/class/pwm/pwmchip<N>/pwm<M>/
 - Sends braking info frame on CAN ID 0x200: [state(0/1), percent(0-100)]
 - Cleans up PWM on exit.

 Build:
   gcc abs_ecu.c -o abs_ecu

 Run (example):
   sudo ./abs_ecu --can can0 --pwmchip 0 --pwm 0 --period 1000000 --threshold 300 --min-distance 50

 Note: requires root (access to /sys/class/pwm and CAN socket)
*/

#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <errno.h>
#include <ctype.h>

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <time.h>

/* SocketCAN headers */
#include <sys/socket.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <net/if.h>
#include <sys/ioctl.h>

/* Default parameters */
#define DEFAULT_CAN_IF "can0"
#define DEFAULT_PWMCHIP 0
#define DEFAULT_PWM 0
#define DEFAULT_PERIOD_NS 1000000UL   /* 1 kHz */
#define DEFAULT_THRESHOLD_MM 300
#define DEFAULT_MIN_DISTANCE_MM 50
#define BRAKE_CAN_ID 0x200
#define ULTRASONIC_CAN_ID 0x100

/* Global state for cleanup */
static int exported_by_us = 0;  /* whether we exported the pwm channel */
static int pwm_enabled = 0;
static char pwm_base_path[256] = {0};

/* ---------- CRC8 poly 0x07 implementation (MSB-first) ---------- */
static uint8_t crc8(const uint8_t *data, uint8_t len) {
    uint8_t crc = 0;
    for (uint8_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (uint8_t b = 0; b < 8; ++b) {
            if (crc & 0x80) crc = (uint8_t)((crc << 1) ^ 0x07);
            else crc <<= 1;
        }
    }
    return crc;
}

/* ---------- Sysfs PWM helpers ---------- */

/* Write a text value to a sysfs file */
static int write_sysfs(const char *path, const char *value) {
    int fd = open(path, O_WRONLY);
    if (fd < 0) {
        return -1;
    }
    ssize_t w = write(fd, value, strlen(value));
    close(fd);
    return (w == (ssize_t)strlen(value)) ? 0 : -1;
}

/* Helper to check file exists */
static int path_exists(const char *path) {
    struct stat st;
    return (stat(path, &st) == 0);
}

/* Export pwm channel if not already present */
static int pwm_ensure_exported(int chip, int channel) {
    char buf[256];
    snprintf(buf, sizeof(buf), "/sys/class/pwm/pwmchip%d/pwm%d", chip, channel);
    if (path_exists(buf)) {
        /* already exported */
        return 0;
    }
    /* export it */
    char export_path[256];
    snprintf(export_path, sizeof(export_path), "/sys/class/pwm/pwmchip%d/export", chip);
    char ch_str[32];
    snprintf(ch_str, sizeof(ch_str), "%d", channel);
    if (write_sysfs(export_path, ch_str) < 0) {
        fprintf(stderr, "Failed to export PWM channel: %s (errno=%d)\n", export_path, errno);
        return -1;
    }
    /* mark that we exported it so we can unexport later */
    exported_by_us = 1;
    /* wait for pwm channel directory to appear (short timeout) */
    int waited = 0;
    while (!path_exists(buf) && waited < 50) {
        usleep(10000); // 10ms
        waited++;
    }
    if (!path_exists(buf)) {
        fprintf(stderr, "Timeout waiting for pwm sysfs to appear: %s\n", buf);
        return -1;
    }
    return 0;
}

/* Compose path into pwm_base_path global: /sys/class/pwm/pwmchip<chip>/pwm<channel>/ */
static void pwm_set_base(int chip, int channel) {
    snprintf(pwm_base_path, sizeof(pwm_base_path), "/sys/class/pwm/pwmchip%d/pwm%d/", chip, channel);
}

/* Set PWM period (ns) */
static int pwm_set_period_ns(unsigned long period_ns) {
    char path[512];
    snprintf(path, sizeof(path), "%speriod", pwm_base_path);
    char tmp[64];
    snprintf(tmp, sizeof(tmp), "%lu", period_ns);
    return write_sysfs(path, tmp);
}

/* Set PWM duty cycle (ns) */
static int pwm_set_duty_ns(unsigned long duty_ns) {
    char path[512];
    snprintf(path, sizeof(path), "%sduty_cycle", pwm_base_path);
    char tmp[64];
    snprintf(tmp, sizeof(tmp), "%lu", duty_ns);
    return write_sysfs(path, tmp);
}

/* Enable or disable PWM */
static int pwm_set_enable(int enable) {
    char path[512];
    snprintf(path, sizeof(path), "%senable", pwm_base_path);
    char tmp[16];
    snprintf(tmp, sizeof(tmp), "%d", enable ? 1 : 0);
    int rc = write_sysfs(path, tmp);
    if (rc == 0) pwm_enabled = (enable ? 1 : 0);
    return rc;
}

/* Unexport PWM if we exported it earlier */
static void pwm_cleanup_unexport(int chip, int channel) {
    if (!exported_by_us) return;
    char unexport_path[256];
    snprintf(unexport_path, sizeof(unexport_path), "/sys/class/pwm/pwmchip%d/unexport", chip);
    char ch_str[32];
    snprintf(ch_str, sizeof(ch_str), "%d", channel);
    write_sysfs(unexport_path, ch_str);
}

/* Gracefully disable PWM */
static void pwm_cleanup_disable(void) {
    if (pwm_enabled) {
        pwm_set_enable(0);
    }
}

/* ---------- CAN helpers ---------- */

/* Create and bind a SocketCAN RAW socket on interface name (e.g., "can0") */
static int can_setup_socket(const char *ifname) {
    int s;
    struct ifreq ifr;
    struct sockaddr_can addr;

    if ((s = socket(PF_CAN, SOCK_RAW, CAN_RAW)) < 0) {
        perror("socket PF_CAN");
        return -1;
    }

    strncpy(ifr.ifr_name, ifname, IFNAMSIZ-1);
    if (ioctl(s, SIOCGIFINDEX, &ifr) < 0) {
        perror("ioctl SIOCGIFINDEX");
        close(s);
        return -1;
    }

    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;

    if (bind(s, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind can socket");
        close(s);
        return -1;
    }

    return s;
}

/* Send a brake info CAN frame (ID 0x200, 2 bytes: state, percent) */
static int can_send_brake(int sock, uint8_t state, uint8_t percent) {
    struct can_frame frame;
    memset(&frame, 0, sizeof(frame));
    frame.can_id = BRAKE_CAN_ID;
    frame.can_dlc = 2;
    frame.data[0] = state ? 0x01 : 0x00;
    frame.data[1] = percent;
    ssize_t n = write(sock, &frame, sizeof(struct can_frame));
    return (n == sizeof(struct can_frame)) ? 0 : -1;
}

/* ---------- Signal handling for clean exit ---------- */
static volatile int keep_running = 1;
static int g_pwm_chip = DEFAULT_PWMCHIP;
static int g_pwm_channel = DEFAULT_PWM;

static void handle_sigint(int sig) {
    (void)sig;
    keep_running = 0;
}

/* ---------- Utility: parse args ---------- */
static void usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s [--can <ifname>] [--pwmchip N] [--pwm M] [--period ns] [--threshold mm] [--min-distance mm] [--verbose]\n"
        "Defaults: --can can0 --pwmchip 0 --pwm 0 --period 1000000 --threshold 300 --min-distance 50\n",
        prog);
}

/* ---------- Main logic ---------- */
int main(int argc, char **argv) {
    const char *can_if = DEFAULT_CAN_IF;
    unsigned long period_ns = DEFAULT_PERIOD_NS;
    int threshold_mm = DEFAULT_THRESHOLD_MM;
    int min_distance_mm = DEFAULT_MIN_DISTANCE_MM;
    int verbose = 0;

    /* parse simple CLI args */
    for (int i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--can") && i+1 < argc) {
            can_if = argv[++i];
        } else if (!strcmp(argv[i], "--pwmchip") && i+1 < argc) {
            g_pwm_chip = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--pwm") && i+1 < argc) {
            g_pwm_channel = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--period") && i+1 < argc) {
            period_ns = strtoul(argv[++i], NULL, 10);
        } else if (!strcmp(argv[i], "--threshold") && i+1 < argc) {
            threshold_mm = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--min-distance") && i+1 < argc) {
            min_distance_mm = atoi(argv[++i]);
        } else if (!strcmp(argv[i], "--verbose")) {
            verbose = 1;
        } else if (!strcmp(argv[i], "--help") || !strcmp(argv[i], "-h")) {
            usage(argv[0]);
            return 0;
        } else {
            fprintf(stderr, "Unknown arg: %s\n", argv[i]);
            usage(argv[0]);
            return 1;
        }
    }

    if (threshold_mm <= min_distance_mm) {
        fprintf(stderr, "threshold must be > min-distance\n");
        return 1;
    }

    /* Setup signal handlers */
    signal(SIGINT, handle_sigint);
    signal(SIGTERM, handle_sigint);

    /* Prepare PWM sysfs */
    if (pwm_ensure_exported(g_pwm_chip, g_pwm_channel) < 0) {
        fprintf(stderr, "Failed to export PWM channel. Are you root?\n");
        return 1;
    }
    pwm_set_base(g_pwm_chip, g_pwm_channel);

    /* set period (may need to disable before changing on some kernels) */
    pwm_set_enable(0); /* try disable first */
    if (pwm_set_period_ns(period_ns) < 0) {
        fprintf(stderr, "Failed to set pwm period\n");
        /* continue but warn */
    }

    /* start with 0% */
    pwm_set_duty_ns(0);
    if (pwm_set_enable(1) < 0) {
        fprintf(stderr, "Failed to enable PWM\n");
    } else {
        pwm_enabled = 1;
    }

    /* Setup CAN socket */
    int can_sock = can_setup_socket(can_if);
    if (can_sock < 0) {
        fprintf(stderr, "Failed to setup CAN socket on %s\n", can_if);
        pwm_cleanup_disable();
        pwm_cleanup_unexport(g_pwm_chip, g_pwm_channel);
        return 1;
    }
    if (verbose) fprintf(stderr, "Listening on CAN interface %s\n", can_if);

    /* Main loop: read CAN frames, handle ultrasonic frames */
    struct can_frame frame;
    ssize_t n;
    while (keep_running) {
        n = read(can_sock, &frame, sizeof(struct can_frame));
        if (n < 0) {
            if (errno == EINTR) continue;
            perror("CAN read");
            break;
        } else if (n < (ssize_t)sizeof(struct can_frame)) {
            /* partial read? ignore */
            continue;
        }

        /* Only handle standard frames 0x100 with 8 bytes */
        if ((frame.can_id & CAN_EFF_FLAG) || (frame.can_dlc != 8)) {
            continue;
        }
        if ((frame.can_id & CAN_SFF_MASK) != ULTRASONIC_CAN_ID) {
            continue;
        }

        uint8_t data[8];
        memcpy(data, frame.data, 8);
        uint8_t computed = crc8(data, 7);
        if (computed != data[7]) {
            if (verbose) fprintf(stderr, "CRC mismatch: got 0x%02X expected 0x%02X\n", data[7], computed);
            /* invalid frame -> set brake OFF for safety */
            if (pwm_enabled) {
                pwm_set_duty_ns(0);
            }
            can_send_brake(can_sock, 0, 0);
            continue;
        }

        /* parse */
        uint16_t dist = (uint16_t)(((uint16_t)data[0] << 8) | data[1]);
        uint8_t counter = data[2];
        uint8_t status = data[3];

        if (verbose) fprintf(stderr, "ULTRASONIC dist=%u mm counter=%u status=%u\n", dist, counter, status);

        /* decide braking */
        uint8_t brake_state = 0;
        uint8_t brake_percent = 0;

        if (status != 0) {
            /* timeout or out_of_range -> no braking */
            brake_state = 0;
            brake_percent = 0;
        } else {
            if (dist < (uint16_t)threshold_mm) {
                /* linear mapping: dist <= min_distance => 100%
                   dist >= threshold_mm => 0%
                   between min_distance..threshold => scale 100..0
                */
                if (dist <= (uint16_t)min_distance_mm) {
                    brake_percent = 100;
                } else {
                    double frac = (double)(threshold_mm - dist) / (double)(threshold_mm - min_distance_mm);
                    if (frac < 0.0) frac = 0.0;
                    if (frac > 1.0) frac = 1.0;
                    brake_percent = (uint8_t)(frac * 100.0 + 0.5);
                }
                brake_state = (brake_percent > 0) ? 1 : 0;
            } else {
                brake_state = 0;
                brake_percent = 0;
            }
        }

        /* Apply PWM */
        unsigned long duty_ns = (unsigned long)(((unsigned long long)period_ns * (unsigned long long)brake_percent) / 100ULL);
        if (pwm_set_duty_ns(duty_ns) < 0) {
            if (verbose) fprintf(stderr, "Failed to set duty cycle\n");
        }

        /* send brake info on CAN */
        if (can_send_brake(can_sock, brake_state, brake_percent) < 0) {
            if (verbose) fprintf(stderr, "Failed to send brake CAN frame\n");
        }

        /* Optionally log */
        if (verbose) {
            fprintf(stderr, "Applied brake_state=%u percent=%u duty_ns=%lu\n", brake_state, brake_percent, duty_ns);
        }
    } /* main loop */

    /* cleanup */
    if (verbose) fprintf(stderr, "Shutting down: disabling PWM and unexporting\n");
    pwm_cleanup_disable();
    pwm_cleanup_unexport(g_pwm_chip, g_pwm_channel);
    close(can_sock);
    return 0;
}
