/*
  can_recv_udp.c

  SocketCAN receiver for Ultrasonic CAN frames (ID 0x100).
  - Listens on can0
  - Validates CRC8 (poly 0x07) over bytes 0..6, compares to byte 7
  - On valid frame: parses distance (bytes 0..1 big-endian), counter (byte 2), status (byte 3)
  - Logs to stdout and forwards distance as ASCII "<mm>\n" to UDP 127.0.0.1:5005

  Compile:
    gcc can_recv_udp.c -o can_recv_udp

  Run (may need sudo/capabilities):
    sudo ./can_recv_udp
*/

#define _DEFAULT_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <fcntl.h>

#include <net/if.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <linux/can.h>
#include <linux/can/raw.h>

/* CRC-8 (poly 0x07) implementation.
   This matches the CRC used by the Arduino sender (MSB-first bit processing).
   Computes CRC over `len` bytes starting at `data`. */
uint8_t crc8(const uint8_t *data, uint8_t len) {
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

int main() {
    int can_sock;
    struct sockaddr_can addr;
    struct ifreq ifr;
    struct can_frame frame;

    /* Create a raw CAN socket (PF_CAN / SOCK_RAW / CAN_RAW) */
    if ((can_sock = socket(PF_CAN, SOCK_RAW, CAN_RAW)) < 0) {
        perror("Error creating CAN socket");
        return 1;
    }

    /* Locate the interface index for "can0" */
    memset(&ifr, 0, sizeof(ifr));
    strncpy(ifr.ifr_name, "can0", IFNAMSIZ - 1);
    if (ioctl(can_sock, SIOCGIFINDEX, &ifr) < 0) {
        perror("ioctl SIOCGIFINDEX failed (is can0 configured?)");
        close(can_sock);
        return 1;
    }

    /* Bind the socket to can0 */
    addr.can_family = AF_CAN;
    addr.can_ifindex = ifr.ifr_ifindex;
    if (bind(can_sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind failed");
        close(can_sock);
        return 1;
    }

    /* Create UDP socket to forward parsed distance to 127.0.0.1:5005 */
    int udp_sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (udp_sock < 0) {
        perror("Failed to create UDP socket");
        close(can_sock);
        return 1;
    }
    struct sockaddr_in udp_dst;
    memset(&udp_dst, 0, sizeof(udp_dst));
    udp_dst.sin_family = AF_INET;
    udp_dst.sin_port = htons(5005);
    inet_pton(AF_INET, "127.0.0.1", &udp_dst.sin_addr);

    printf("Listening on can0...\n");

    /* Main loop: read CAN frames and process */
    while (1) {
        ssize_t nbytes = read(can_sock, &frame, sizeof(struct can_frame));
        if (nbytes < 0) {
            perror("CAN read failed");
            break;
        }

        /* Filter: expect standard ID 0x100 and 8 bytes payload */
        if ((frame.can_id & CAN_EFF_FLAG) || frame.can_dlc != 8) {
            /* either extended frame or not 8 bytes - ignore */
            continue;
        }

        if ((frame.can_id & CAN_SFF_MASK) != 0x100) {
            /* not the ultrasonic ID we expect */
            continue;
        }

        uint8_t buf[8];
        memcpy(buf, frame.data, 8);

        /* Validate CRC8 computed over bytes 0..6 matches byte 7 */
        uint8_t computed = crc8(buf, 7);
        if (computed != buf[7]) {
            fprintf(stderr, "CRC mismatch: frame_crc=0x%02X computed=0x%02X\n", buf[7], computed);
            continue; /* drop frame */
        }

        /* Parse distance (big-endian), counter and status */
        uint16_t dist = (uint16_t)(((uint16_t)buf[0] << 8) | (uint16_t)buf[1]);
        uint8_t counter = buf[2];
        uint8_t status = buf[3];

        /* Log parsed values to stdout */
        printf("ULTRASONIC dist=%u mm counter=%u status=%u\n", (unsigned)dist, (unsigned)counter, (unsigned)status);
        fflush(stdout);

        /* Forward distance as ASCII "<dist>\n" to UDP 127.0.0.1:5005 */
        char msg[32];
        int len = snprintf(msg, sizeof(msg), "%u\n", (unsigned)dist);
        if (len > 0) {
            ssize_t sent = sendto(udp_sock, msg, (size_t)len, 0, (struct sockaddr *)&udp_dst, sizeof(udp_dst));
            if (sent < 0) {
                perror("UDP sendto failed");
                /* continue nevertheless */
            }
        }
    }

    close(udp_sock);
    close(can_sock);
    return 0;
}
