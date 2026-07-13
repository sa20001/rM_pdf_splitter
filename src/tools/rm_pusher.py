import json
import sys
from pathlib import Path

import paramiko
from loguru import logger


def _resource_path(*parts: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return base_path.joinpath(*parts)


def push_template_to_rm(hostname: str, username: str, password: str = None, key_filename: str = None):
    """
    Push the custom template to the reMarkable device.
    """

    if password is None and key_filename is None:
        logger.error("Push requested without password or key file.")
        raise ValueError("Either password or key_filename must be provided.")

    template_path = _resource_path("templates", "templates.json")
    with template_path.open("r", encoding="utf-8") as file_handle:
        template_key = json.load(file_handle)

    logger.info(
        "Preparing to push template {} to {} as {} using {} authentication.",
        template_key.get("filename", "<unknown>"),
        hostname,
        username,
        "password" if password is not None else "key file",
    )

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    if password is not None:
        logger.debug("Connecting with password authentication.")
        ssh.connect(
            hostname=hostname,
            username=username,
            password=password
        )
    else:
        logger.debug("Connecting with key file: {}", key_filename)
        ssh.connect(
            hostname=hostname,
            username=username,
            key_filename=key_filename,
        )

    logger.success("SSH connection established to {}.", hostname)

    # Save a backup of the templates.json file (if not already present)
    _, stdout, stderr = ssh.exec_command(
        "cp -n /usr/share/remarkable/templates/templates.json ~/templates.json.backup"
    )
    data = stdout.read()
    error = stderr.read()
    backup_stdout = data.decode("utf-8").strip()
    backup_stderr = error.decode("utf-8").strip()
    if backup_stdout:
        logger.info("Backup command output: {}", backup_stdout)
    if backup_stderr:
        logger.warning("Backup command stderr: {}", backup_stderr)
    else:
        logger.debug("Backup command completed without stderr output.")


    # Append a new template to the templates.json file
    sftp = ssh.open_sftp()

    remote_file = "/usr/share/remarkable/templates/templates.json"

    # Read remote JSON
    with sftp.open(remote_file, "r") as file_handle:
        data = json.load(file_handle)

    # Check if key already exists in the templates list
    exists = any(
        t["filename"] == template_key["filename"]
        for t in data["templates"]
    )

    if not exists:
        # Append key to rm2 template
        data["templates"].append(template_key)
        logger.info("Template {} not present on device; appending entry.", template_key["filename"])

        # Write back
        with sftp.open(remote_file, "w") as file_handle:
            json.dump(data, file_handle, indent=4)
    else:
        logger.info("Template {} already exists in templates.json.", template_key["filename"])


    # Create custom template folder if it doesn't exist
    ssh.exec_command(
        "mkdir -p /usr/share/remarkable/templates/my_templates/"
    )

    # Copy template to rm
    template_name = "LS Dotted S A4.template"
    sftp.put(
        str(_resource_path("templates", template_name)),
        f"/usr/share/remarkable/templates/my_templates/{template_name}"  # remote file
    )
    logger.success(f"Template {template_name} copied to reMarkable.")
    sftp.close()

    # Restaet the UI
    ssh.exec_command(
        "systemctl restart xochitl"
    )

    logger.info("Restarting xochitl UI on the device.")

    # Close the SSH connection
    ssh.close()
    logger.success("Template push completed successfully.")