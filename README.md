# Network Lab Project – VPN Manager Deployment

## Project Overview

VPN Manager is a Spring Boot web application designed to manage the lifecycle of OpenVPN certificates within a secure, internal, and offline network environment.

This lab project simulates a realistic IT infrastructure consisting of isolated internal networks, a central firewall, and critical services (VPN and database) segmented across multiple VMs. The goal is to evaluate the user's ability to:

* Design a virtualized network topology using internal and DMZ-like zones
* Configure network interfaces, routing, and firewall rules
* Deploy and configure services such as OpenVPN, MySQL, and a Spring Boot web application
* Ensure security and functionality across network layers in an offline environment
* Test VPN certificate issuance and access control via a web interface

More details of the project configuration can be found in **`manual/especificacao_painelVPN.pdf`**

This repository contains all resources needed to recreate a secure internal lab network consisting of:

* Two internal subnets (`192.168.200.0/24` and `192.168.201.0/24`)
* A firewall VM connecting the two networks
* A VPN + web server VM
* A MySQL database VM
* A client VM for VPN access

## Folder Structure

```
resources/
├── diagrams/
├── firewall_rules/
│   ├── database/
│   │   ├── database_rules.txt
│   │   └── firewall.sh                     <-- script for firewall's rules
│   ├── firewall/
│   │   ├── firewall_rules.txt
│   │   └── firewall.sh
│   └── server/
│       ├── server_rules.txt
│       └── firewall.sh
├── manual/especificacao_painelVPN.pdf      <-- project description
├── scripts/                                <-- scripts for certificate's creation and revoke
│   ├── create_certificate_client.py
│   └── revoke_certificate_client.py
├── server_configuration/
│   ├── server_configuration                <-- detailed guide for the openvpn configuration
│   └── server.conf
└── README.md
```

## Base VM Preparation

Start with a **Debian 12 Netinstall ISO**, using the **"standard system utilities"** predefined software collection only.
After installation, on **each VM**:

```bash
su root
apt update
apt install sudo -y
nano /etc/sudoers
{username​} ALL=(ALL:ALL) ALL
exit
sudo apt install sudo openssh-server -y
```

## Client VM (192.168.201.2)

### Purpose:

Provides a GUI to access the VPN Manager and download certificates.

### Steps:

1. Install basic setup:

    ```bash
    sudo apt install xfce4 firefox-esr xfce4-terminal zip -y
    ```

2. Configure static IP:

    ```bash
    sudo nano /etc/network/interfaces
    ```

    Update the interface setup to:


    ```ini
    iface enp0s3 inet static
        address 192.168.201.2
        network 192.168.201.0
        netmask 255.255.255.0
        broadcast 192.168.201.255
        gateway 192.168.201.1
        dns-nameserver 8.8.8.8
    ```

3. Power off the vm.

4. Update the network settings on Virtualbox.

5. Restart the Client VM.

## Database VM (192.168.200.6)

### Purpose:

Hosts the MySQL database for the VPN Manager.

### MySQL installation:

1. Install basic setup:

    ```bash
    sudo apt install gnupg -y
    wget https://dev.mysql.com/get/mysql-apt-config-0.8.34-1_all.deb
    sudo dpkg -i mysql-apt-config-0.8.34-1_all.deb
    ```
    
    Pay attention to reply to the MySQL repository set up script prompts to install the latest database server sources.

    ```bash
    sudo apt update
    sudo apt install mysql-server -y
    ```
    
    Define a root database user password and Keep Use Strong Password Encryption (RECOMMENDED) selected to enable password authentication for all database users on the server.

2. Check the installed version.
    
    ```bash
    mysql --version
    ```

### MySQL Configuration

1. Secure the MySQL database server.

    ```bash
    sudo mysql_secure_installation
    ```

    > Configure as needed.

4. Manage the MySQL system service.

    ```bash
    sudo systemctl enable mysql
    sudo systemctl start mysql
    sudo systemctl status mysql
    ```

5. Allow remote access to MySQL.

    ```bash
    sudo nano /etc/mysql/mysql.conf.d/mysqld.conf
    ```

    Add or change the `bind-address` line to:
    
    `bind-address = 0.0.0.0`

6. Restart the MySQL service to put the changes into effect.

    ```bash
    sudo systemctl restart mysql
    ```

### Create a remote host:

1. Access the MySQL shell.

    ```bash
    mysql -u root -p
    ```

2. Create a user account that will connect from the remote host.

    ```sql
    CREATE USER '{username}'@'{vpn_server_ip}' IDENTIFIED BY '{password}';
    GRANT ALL PRIVILEGES ON *.* TO '{username}'@'{vpn_server_ip}' WITH GRANT OPTION;
    FLUSH PRIVILEGES;
    ```

    > Additionally, you can create in this step the database necessary for the Spring Boot application.

    ```sql
        CREATE DATABASE vpnmanager;
    ```

### Apply firewall rules:

1. Copy `firewall_rules/database/firewall.sh` to the VM and run:

    ```bash
    chmod +x firewall.sh
    sudo ./firewall.sh
    ```

2. Create the following `/etc/systemd/system/firewall.service`.

    ```init
    [Unit]
    Description=Custom Firewall Rules
    After=network.target

    [Service]
    ExecStart=/usr/local/sbin/firewall.sh
    
    [Install]
    WantedBy=multi-user.target
    ```

3. Make sure your firewall script is located at /usr/local/sbin/firewall.sh:

    ```bash
    sudo cp RESOURCES/firewall_rules/firewall.sh /usr/local/sbin/firewall.sh
    sudo chmod +x /usr/local/sbin/firewall.sh
    ```

4. Enable the service.

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable firewall
    sudo systemctl start firewall
    ```

### Configure the network interfaces:

1. Configure static IP:

    ```bash
    sudo nano /etc/network/interfaces
    ```

    Update the interface setup to:

    ```ini
    iface enp0s3 inet static
        address 192.168.200.6
        network 192.168.200.0
        netmask 255.255.255.0
        broadcast 192.168.200.255
        gateway 192.168.200.1
        dns-nameserver 8.8.8.8
    ```

2. Power off the vm.

3. Update the network settings on Virtualbox.

4. Restart the Database VM.


## Firewall VM (192.168.200.1 <--> 192.168.201.1)

### Purpose:

Routes and filters traffic between the networks.

> **Note** that this configuration allows interface enp0s3 connects to 192.168.201.0/24 (client side), and enp0s8 to 192.168.200.0/24 (server side).

### Enable IPv4 forwarding:

1. Persist in `/etc/sysctl.conf`:

    ```ini
    net.ipv4.ip_forward = 1
    ```

### Configure the network interfaces:

1. Configure static IP:

    ```bash
    sudo nano /etc/network/interfaces
    ```

    Update the interface setup to:


    ```ini
    /etc/network/interfaces
    iface enp0s3 inet static
        address 192.168.201.1
        network 192.168.201.0
        netmask 255.255.255.0
        broadcast 192.168.201.255

    iface enp0s8 inet static
        address 192.168.200.1
        network 192.168.200.0
        netmask 255.255.255.0
        broadcast 192.168.200.255
    ```

2. Power off the vm.

3. Update the network settings on Virtualbox.

4. Restart the Database VM.

### Firewall rules:

1. Copy `firewall_rules/firewall/firewall.sh` to the VM and run:

    ```bash
    chmod +x firewall.sh
    sudo ./firewall.sh
    ```

2. Create the following `/etc/systemd/system/firewall.service`.

    ```init
    [Unit]
    Description=Custom Firewall Rules
    After=network.target

    [Service]
    ExecStart=/usr/local/sbin/firewall.sh
    
    [Install]
    WantedBy=multi-user.target
    ```

3. Make sure your firewall script is located at /usr/local/sbin/firewall.sh:

    ```bash
    sudo cp RESOURCES/firewall_rules/firewall.sh /usr/local/sbin/firewall.sh
    sudo chmod +x /usr/local/sbin/firewall.sh
    ```

4. Enable the service.

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable firewall
    sudo systemctl start firewall

## VPN Server + Web App VM (192.168.200.4)

### Purpose:

Runs OpenVPN and the `vpnmanager` Java Spring Boot web app.

### Install dependencies:

```bash
sudo apt install easy-rsa openvpn openjdk-17-jdk maven -y
```

> Note that a detailed step-by-step guide for the openVPN server configuration is present in `server-configuration/server-configuration.txt`. Below we highlight only the main steps without much detail.

### openVPN setup:

* Create a Unix user that will run the application and manage the certificate scripts (e.g., `appuser`).
* Create Unix group (e.g., `certman`).
* Add `{user}` and `appuser` to this group.
* Create PKI workspace in a shared but secure location.
* Initialize PKI using `easy-rsa`.
* Copy certs to `/etc/openvpn/server/`.
* Configure `/etc/openvpn/server/server.conf`.
    > A example of this configuration file can be found in `server-configuration/server.conf` .
* Enable forwarding  on the Open VPN server.
* Start service.

### Python scripts

* Transfer python scripts to the server via `scp` or `rsync`.
* Ensure that scripts are installed in `/opt/easy-rsa/`.
* Set up permissions.
* Test scripts - optional.

### Java App setup (Offline server):

> A detailed step-by-step guide for the application configuration is present in `https://github.com/deArrudal/api-vpnmanager`. Below we highlight only the main steps without much detail.

* Transfer project to the server via `scp` or `rsync`.
* Build the project.
* Create deployment directory and move project.
* Create `/etc/systemd/system/vpnmanager.service`.
* Enable and start the service.
* Generate self-signed certificate.
* Allow Java to bind to port 443.
* Create systemd service.
* Enable and start service.
* Seed the Database.

### Firewall rules:

1. Copy `firewall_rules/server/firewall.sh` to the VM and run:

    ```bash
    chmod +x firewall.sh
    sudo ./firewall.sh
    ```

2. Create the following `/etc/systemd/system/firewall.service`.

    ```init
    [Unit]
    Description=Custom Firewall Rules
    After=network.target

    [Service]
    ExecStart=/usr/local/sbin/firewall.sh
    
    [Install]
    WantedBy=multi-user.target
    ```

3. Make sure your firewall script is located at /usr/local/sbin/firewall.sh:

    ```bash
    sudo cp RESOURCES/firewall_rules/firewall.sh /usr/local/sbin/firewall.sh
    sudo chmod +x /usr/local/sbin/firewall.sh
    ```

4. Enable the service.

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable firewall
    sudo systemctl start firewall

### Configure the network interfaces:

1. Configure static IP:

    ```bash
    sudo nano /etc/network/interfaces
    ```

    Update the interface setup to:


    ```ini
    /etc/network/interfaces
    iface enp0s3 inet static
        address 192.168.200.4
        network 192.168.200.0
        netmask 255.255.255.0
        broadcast 192.168.200.255
        gateway 192.168.200.1
        dns-nameserver 8.8.8.8
    ```

2. Power off the vm.

3. Update the network settings on Virtualbox.

4. Restart the Database VM.

## Final Notes

* Use the **Client VM's browser** to access the VPN Manager ([https://192.168.200.4/](https://192.168.200.4/))
* The firewall VM ensures strict access control between subnets
* The VPN server generates and manages client certificates
* All scripts and configurations are versioned inside the `RESOURCES/` folder

## Authors

 - deArruda, Lucas [@SardinhaArruda](https://twitter.com/SardinhaArruda)

## Version History

* 1.0
    * Initial Release

## License

This project is licensed under the GPL-3.0 License - see the LICENSE.md file for details
