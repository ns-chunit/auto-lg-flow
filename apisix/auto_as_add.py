import argparse
import requests
import os
import json
import sys
import logging
from typing import Any, Dict

# --- Logging Configuration ---
# Configure logging to stderr for all output (INFO level for progress, ERROR for failures)
logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s: %(message)s',
                    stream=sys.stderr)
logger = logging.getLogger(__name__)


# --- Configuration ---
BASE_URL = "https://64e21r5vvh.execute-api.us-west-2.amazonaws.com/apisix/admin"
ROUTE_ID = "00000000000000000020"


def get_admin_key() -> str:
    """Fetches the APISIX_ADMIN_API_KEY from environment variables."""
    admin_key = os.environ.get("APISIX_ADMIN_API_KEY")
    if not admin_key:
        logger.error("🚨 ERROR: Environment variable APISIX_ADMIN_API_KEY is not set.")
        logger.error("Please run first: export APISIX_ADMIN_API_KEY='your_key'")
        sys.exit(1)
    return admin_key


def create_consumer_and_key_auth(session: requests.Session, username: str):
    """
    Creates the Consumer and configures the key-auth plugin via a PUT request.
    """
    logger.info(f"🚀 Creating Consumer '{username}' and configuring Key-Auth...")

    consumer_url = f"{BASE_URL}/consumers/{username}"

    # JSON data for creating the Consumer
    data = {
        "username": username,
        "plugins": {
            "key-auth": {
                "key": username  # Use the username as the API Key
            }
        }
    }

    try:
        response = session.put(consumer_url, json=data)
        response.raise_for_status()
        logger.info(f"✅ Consumer '{username}' created/updated successfully! API Key set to '{username}'.")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Consumer creation failed! Error: {e}")
        response_text = locals().get('response').text if 'response' in locals() and locals().get('response') is not None else 'No response content'
        logger.error(f"Response content: {response_text}")
        sys.exit(1)


def update_route_whitelist(session: requests.Session, username_to_add: str):
    """
    Updates the consumer-restriction whitelist on the specified Route.
    CRITICAL: Retrieves the full plugin configuration before updating to ensure preservation.
    """
    route_url = f"{BASE_URL}/routes/{ROUTE_ID}"
    logger.info(f"\n⚙️ Fetching existing configuration from Route '{ROUTE_ID}'...")

    try:
        get_response = session.get(route_url)
        get_response.raise_for_status()
        route_config = get_response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Failed to fetch Route configuration! Error: {e}")
        sys.exit(1)

    # Extract plugins, initialize if missing (should not happen for APISIX routes)
    existing_plugins: Dict[str, Any] = route_config.get('value', {}).get('plugins', {})
    consumer_restriction = existing_plugins.get('consumer-restriction', {})
    old_whitelist = consumer_restriction.get('whitelist', [])
    logger.info(f"   -> Number of existing consumers in whitelist: {len(old_whitelist)}")

    if username_to_add in old_whitelist:
        logger.warning(f"⚠️ '{username_to_add}' is already in the whitelist. Update skipped.")
        return

    new_whitelist = old_whitelist + [username_to_add]
    logger.info(f"   -> Adding '{username_to_add}'. New total consumers: {len(new_whitelist)}.")

    consumer_restriction['whitelist'] = new_whitelist

    patch_data = {
        "plugins": existing_plugins
    }

    logger.info(f"🔄 Sending PATCH request to update Route '{ROUTE_ID}' with FULL plugin list...")

    try:
        patch_response = session.patch(route_url, json=patch_data)
        patch_response.raise_for_status()
        logger.info("✅ Route whitelist updated successfully!")
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Route whitelist update failed! Error: {e}")
        response_text = locals().get('patch_response').text if 'patch_response' in locals() and locals().get('patch_response') is not None else 'No response content'
        logger.error(f"Response content: {response_text}")
        sys.exit(1)


def main():
    """Main function, handles arguments and calls API functions."""
    parser = argparse.ArgumentParser(
        description="APISIX Consumer & Route Management Tool.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "consumer_name",
        type=str,
        help="The name of the Consumer to create (also serves as the Key-Auth secret).\nExample: 'team-test'"
    )

    args = parser.parse_args()
    admin_key = get_admin_key()

    session = requests.Session()
    session.headers.update({
        "X-API-KEY": admin_key,
        "Content-Type": "application/json"
    })

    logger.info("--- APISIX Consumer/Route Configuration Script Started ---")
    logger.info(f"Target Consumer Name: {args.consumer_name}")
    logger.info(f"Target Route ID: {ROUTE_ID}")

    create_consumer_and_key_auth(session, args.consumer_name)
    update_route_whitelist(session, args.consumer_name)

    logger.info(f"\n🎉 All tasks completed! Consumer '{args.consumer_name}' created and added to Route '{ROUTE_ID}' whitelist.")
    logger.info("💡 Usage: Use Header: 'apikey: {consumer_name}' to authenticate API requests.")


if __name__ == "__main__":
    main()

