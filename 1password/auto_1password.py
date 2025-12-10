import argparse
import subprocess
import sys
import re
import logging

logging.basicConfig(level=logging.WARNING,
                    format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def run_op_command(command: list):
    """
    Executes the op CLI command, captures output, and handles errors.
    Logs execution details at INFO level.
    """
    command_str = " ".join(command)
    logger.info(f"Executing command: {command_str}")

    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        if result.stderr:
            logger.warning(f"Command STDERR Output:\n{result.stderr.strip()}")

        logger.debug(f"Command STDOUT:\n{result.stdout.strip()}")

        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        logger.error("--- Error executing 'op' command ---")
        logger.error(f"Command failed: {command_str}")
        logger.error(f"Stdout:\n{e.stdout.strip()}")
        logger.error(f"Stderr:\n{e.stderr.strip()}")
        sys.exit(1)

    except FileNotFoundError:
        logger.error("Error: The 'op' command was not found. Please ensure 1Password CLI is installed.")
        sys.exit(1)


def create_and_share_item(branch_name: str, lg_key: str, share_to: str) -> str:
    """
    Creates a 1Password item and generates a share link.
    Returns: The final sharing URL string.
    """
    VAULT_NAME = "LangGraphKeys"
    EXPIRATION = "7d"

    logger.info(f"Process started for item '{branch_name}' and sharing with '{share_to}'.")

    create_command = [
        "op", "item", "create",
        "--vault", VAULT_NAME,
        "--title", branch_name,
        "--category", "API Credential",
        f"password={lg_key}"
    ]

    logger.info(f"Step 1: Creating item in vault '{VAULT_NAME}'...")
    create_output = run_op_command(create_command)

    match = re.search(r'^ID:\s*([a-zA-Z0-9]+)', create_output, re.MULTILINE)

    if not match:
        logger.critical("Could not extract ITEM_ID from op item create output. Check op signin status.")
        raise ValueError("Could not extract ITEM_ID from op item create output. Check op signin status.")

    ITEM_ID = match.group(1)
    logger.info(f"Item created successfully. Item ID: {ITEM_ID}")

    # 3. Share the item
    share_command = [
        "op", "item", "share", ITEM_ID,
        "--emails", share_to,
        "--expires-in", EXPIRATION
    ]

    logger.info(f"Step 2: Generating share link for {EXPIRATION}...")
    share_output = run_op_command(share_command)

    logger.info("Share link generated successfully.")
    return share_output


def main():
    parser = argparse.ArgumentParser(
        description="...",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.epilog = """
    *** Important Pre-Execution Step (1Password Sign-in) ***
    This script relies on the 1Password CLI (op) Session Key to perform operations.
    Before running this script, you MUST execute the following command:
    eval $(op signin)
    """

    parser.add_argument('branch_name', type=str, help='BRANCH_NAME: Title for the item to be created in 1Password.')
    parser.add_argument('lg_key', type=str, help='LG_KEY: The API key value to be stored in the item (as the password field).')
    parser.add_argument('share_to', type=str, help='SHARE_TO: The email address of the recipient for the share link.')

    args = parser.parse_args()

    logger.setLevel(logging.WARNING)

    try:
        share_link = create_and_share_item(args.branch_name, args.lg_key, args.share_to)
        print(share_link)

    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
