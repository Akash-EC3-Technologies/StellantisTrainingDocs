# Setting up your Raspberry Pi OS with network credentials, SSH, and updates (Ubuntu Host)

## Prerequisites

-   A Raspberry Pi (e.g., Raspberry Pi 4, 5, etc.).
-   A microSD card (8GB or larger recommended, but 32GB is ideal).
-   A computer running Ubuntu.
-   A microSD card reader for your Ubuntu computer.
-   An internet connection for your Ubuntu machine to download the Imager and OS.
-   Your Wi-Fi network's name (SSID) and password (if using Wi-Fi).

## Part 1: Prepare the microSD card with Raspberry Pi Imager

1.  **Install Raspberry Pi Imager**:

    -   Open a terminal in Ubuntu: `Ctrl + Alt + T`.
    -   Install the Raspberry Pi Imager snap package (recommended on modern Ubuntu versions):
        ```bash
        sudo snap install rpi-imager
        ```
    -   Alternatively, you can download the .deb package from the official [Raspberry Pi website](https://www.raspberrypi.com/software/) and install it manually.

2.  **Launch Raspberry Pi Imager**:

    -   Find and open the "Raspberry Pi Imager" application from your applications menu.

3.  **Choose OS**:

    -   Click "CHOOSE OS".
    -   Select the desired Raspberry Pi OS e.g. "Raspberry Pi OS (64-bit)"

4.  **Choose Storage**:

    -   Insert your microSD card into the card reader on your Ubuntu computer.
    -   Click "CHOOSE STORAGE".
    -   Select your microSD card from the list (double-check you choose the correct device!).

5.  **Configure OS customization settings (Crucial Step)**:

    -   Click "Next".
    -   When prompted to apply OS customization settings, select "EDIT SETTINGS".
    -   **Set username and password**: Check this option and create a strong, unique username and password. This is important for security.
    -   **Configure wireless LAN**: Check this option, enter your Wi-Fi network's SSID,password, and select your wireless LAN country.
    -   **Enable SSH**: Go to the "SERVICES" tab and check "Enable SSH". For password-based SSH (easiest for beginners), make sure "Allow public-key authentication only" is _not_ checked.
    -   Click "SAVE".

6.  **Write the OS**:
    -   Click "YES" to confirm you want to erase the data on the microSD card and write the OS.
    -   The Imager will download (if necessary) and write the chosen Raspberry Pi OS to the card.
    -   Safely remove the microSD card when the writing and verification process is complete.

## Part 2: Boot Raspberry Pi and connect via SSH

1.  **Boot your Raspberry Pi**:

    -   Insert the prepared microSD card into the Raspberry Pi.
    -   Connect the power adapter to your Raspberry Pi.
    -   A red LED should turn on, indicating power. The Pi will begin booting.

2.  **Find the Raspberry Pi's IP address**:

    -   **Method 1: Router's Connected Devices List (Recommended for headless setup)**
        -   Log in to your Wi-Fi router's administrative interface (usually by entering the router's IP address into a web browser, e.g., `192.168.1.1` or `192.168.0.1`).
        -   Look for a section like "Connected Devices", "Device List", or "DHCP Clients".
        -   Find your Raspberry Pi in the list (it may be named "raspberrypi" by default unless you changed the hostname during setup) and note its IP address.
    -   **Method 2: Network Scanner Tool**
        -   Download and install a network scanning tool like Angry IP Scanner on your Ubuntu computer.
        -   Run the scan and look for your Raspberry Pi's IP address (it will likely have "raspberrypi" or the hostname you set as its name).
    -   **Method 3: Terminal (if connected to a screen)**
        -   If you have a monitor and keyboard connected to the Raspberry Pi, open a terminal window.
        -   Type the command `hostname -I` (capital "I") and press Enter.
        -   This will display the Raspberry Pi's IP address.

3.  **Connect to the Raspberry Pi via SSH from Ubuntu**:
    Open a terminal on your Ubuntu computer: `Ctrl + Alt + T`.
    Use the SSH command with the username you set and the Raspberry

    Pi's IP address:

    ```bash
    ssh <your_username>@<Raspberry_Pi_IP_address>
    ```

    For example: `ssh myuser@192.168.1.105`.

    The first time you connect, you might see a warning about the host's authenticity; type `yes` and press Enter to continue.

    Enter the password you created for your Raspberry Pi when prompted.

    If successful, you will be logged into the Raspberry Pi's command-line interface remotely.

## Part 3: Update Raspberry Pi's firmware and software

1.  **Update the package list cache**:

    In the SSH terminal connected to your Raspberry Pi, run the following command:

    ```bash
    sudo apt update
    ```

    This refreshes the list of available software packages.

2.  **Upgrade all installed software packages (including kernel and firmware components)**:

    Run the following command:

    ```bash
    sudo apt full-upgrade
    ```

    This command upgrades all installed packages to their latest versions. Use `full-upgrade` rather than `upgrade` in Raspberry Pi OS due to potential dependency changes.

    If prompted, press `y` and Enter to confirm the installation.

3.  **Reboot for changes to take effect**:

    After the `full-upgrade` is complete, reboot your Raspberry Pi to finalize the updates.

    ```bash
    sudo reboot
    ```

    Your SSH connection will close during the reboot. Wait a minute or two and then attempt to reconnect using the SSH command from Part 2's setp 3

4.  **Update the bootloader firmware (Raspberry Pi 4 and 5)**:

    Check for available EEPROM updates (bootloader firmware):

    ```bash
    sudo rpi-eeprom-update
    ```

    If an update is available, apply it using the following command:

    ```bash
    sudo rpi-eeprom-update -a
    ```

    **Important**: Reboot again after updating the bootloader firmware.

    ```bash
    sudo reboot
    ```

5.  **Clean up unnecessary packages**:
    (Optional but recommended) Remove packages that were installed as dependencies but are no longer needed:
    ```bash
    sudo apt autoremove
    ```
    Clean up the local package archive cache:
    ```bash
    sudo apt clean
    ```

## Reference Docs

RPi Pinout

![alt text](raspberrypi_pinout.png)