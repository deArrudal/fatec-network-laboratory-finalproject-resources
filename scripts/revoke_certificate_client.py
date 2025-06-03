#!/usr/bin/env python3

import os
import sys
import shutil
import subprocess
import logging

REFERENCE_PATH = "/opt/easy-rsa"
TARGET_PATH = os.path.join(REFERENCE_PATH, "client-configs")
EXPORT_PATH = "/opt/easy-rsa/exports"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def revoke_certificate(client, id):
    try:
        client_path = os.path.join(TARGET_PATH, client, id)
        zip_path = os.path.join(EXPORT_PATH, f"{client}_{id}.zip")

        pki_path = os.path.join(REFERENCE_PATH, "pki")
        issued_path = os.path.join(pki_path, "issued")
        private_path = os.path.join(pki_path, "private")

        id_crt = os.path.join(issued_path, f"{id}.crt")
        id_key = os.path.join(private_path, f"{id}.key")
        id_pem = os.path.join(private_path, f"{id}.pem")

        logger.info(f"Revoking certificate for client '{id}'")
        subprocess.run(
            ["./easyrsa", "--batch", "revoke", id],
            cwd=REFERENCE_PATH,
            check=True,
        )

        logger.info("Regenerating CRL")
        subprocess.run(
            ["./easyrsa", "gen-crl"],
            cwd=REFERENCE_PATH,
            check=True,
        )

        for file in [id_crt, id_key, id_pem]:
            if os.path.exists(file):
                os.remove(file)
                logger.info(f"Deleted: {file}")

            else:
                logger.warning(f"File not found (skipped): {file}")

        if os.path.isdir(client_path):
            shutil.rmtree(client_path)
            logger.info(f"Deleted client config directory: {client_path}")

        else:
            logger.warning(f"Client directory not found: {client_path}")

        if os.path.isfile(zip_path):
            os.remove(zip_path)
            logger.info(f"Deleted ZIP archive: {zip_path}")

        else:
            logger.warning(f"ZIP archive not found: {zip_path}")

        logger.info(f"Client '{id}' successfully revoked.")
        print(f"Client '{id}' successfully revoked.")
        sys.exit(0)

    except subprocess.CalledProcessError as e:
        logger.error(f"Subprocess failed: {e}", exc_info=True)
        sys.exit(1)

    except Exception as e:
        logger.error(f"Error revoking client '{id}': {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: revoke_client.py <client_name> <id>")
        sys.exit(1)

    revoke_certificate(sys.argv[1], sys.argv[2])
