#!/usr/bin/env python3

import os
import sys
import shutil
import socket
import subprocess
import zipfile
import logging


SERVER_NAME = "vmserver"
REFERENCE_PATH = "/opt/easy-rsa"
TARGET_PATH = os.path.join(REFERENCE_PATH, "client-configs")
EXPORT_PATH = "/opt/easy-rsa/exports"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def get_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]

    except Exception as e:
        raise RuntimeError(f"Failed to determine external IP: {e}")


def create_zip(zip_filename, files):
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for file in files:
            if os.path.isfile(file):
                zipf.write(file, arcname=os.path.basename(file))

            else:
                logger.warning(f"File missing for zip: {file}")

    logger.info(f"ZIP archive created at: {zip_filename}")


def main(client, id):
    try:
        client_path = os.path.join(TARGET_PATH, client, id)
        os.makedirs(client_path, exist_ok=True)

        os.makedirs(EXPORT_PATH, exist_ok=True)

        pki_path = os.path.join(REFERENCE_PATH, "pki")
        issued_path = os.path.join(pki_path, "issued")
        private_path = os.path.join(pki_path, "private")

        ca_crt = os.path.join(pki_path, "ca.crt")
        id_crt = os.path.join(issued_path, f"{id}.crt")
        id_key = os.path.join(private_path, f"{id}.key")
        id_pem = os.path.join(private_path, f"{id}.pem")
        id_ovpn = os.path.join(client_path, f"{id}.ovpn")

        logger.info(f"Generating certificate request for {id}")
        subprocess.run(
            ["./easyrsa", "--batch", "gen-req", id, "nopass"],
            cwd=REFERENCE_PATH,
            check=True,
        )

        logger.info(f"Signing certificate for {id}")
        subprocess.run(
            ["./easyrsa", "--batch", "sign-req", "client", id],
            cwd=REFERENCE_PATH,
            check=True,
        )

        logger.info(f"Creating TLS Crypt v2 Key for {id}")
        subprocess.run(
            [
                "/usr/sbin/openvpn",
                "--tls-crypt-v2",
                f"private/{SERVER_NAME}.pem",
                "--genkey",
                "tls-crypt-v2-client",
                f"private/{id}.pem",
            ],
            cwd=pki_path,
            check=True,
        )

        for required_file in [ca_crt, id_crt, id_key, id_pem]:
            if not os.path.isfile(required_file):
                raise FileNotFoundError(f"Missing required file: {required_file}")

        ip = get_ip()

        logger.info("Creating .ovpn configuration")
        with open(id_ovpn, "w") as f:
            f.write(f"""client
proto udp
dev tun
remote {ip} 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
cipher AES-256-GCM
#user nobody
#group nobody
verb 3

ca ca.crt
cert {id}.crt
key {id}.key
tls-crypt-v2 {id}.pem
""")

        for src in [ca_crt, id_crt, id_key, id_pem]:
            shutil.copy(src, client_path)

        zip_name = os.path.join(EXPORT_PATH, f"{client}_{id}.zip")
        create_zip(zip_name, [ca_crt, id_crt, id_key, id_pem, id_ovpn])

        logger.info(f"Client config package ready at: {zip_name}")
        print(f"Client config package ready at: {zip_name}")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Error during client certificate creation: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: create_certificate_client.py <client_name> <id>")
        sys.exit(1)

    main(sys.argv[1], sys.argv[2])
