import os
import requests
import sys
import json
import argparse
import logging
from typing import Dict, Optional, Tuple, Any

# Configure logging to stderr
logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s: %(message)s',
                    stream=sys.stderr)
logger = logging.getLogger(__name__)

# Global Configuration
WORKSPACE_NAME = "nsagent-users"
ADMIN_API_KEY = os.getenv("LANGSMITH_ADMIN_API_KEY")
ORG_ID = os.getenv("LANGSMITH_ORG_ID", "d84d3d4c-f149-4cf8-98fc-421ea1bda37b")

class LangSmithManager:
    def __init__(self, api_key: str, org_id: str, base_url: str = "https://xxeucrngdl.execute-api.us-west-2.amazonaws.com"):
        self.api_key = api_key
        self.org_id = org_id
        self.base_url = base_url
        self.headers = {
            "x-api-key": api_key,
            "X-Organization-Id": org_id,
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make authenticated API request and handle errors."""
        url = f"{self.base_url}{endpoint}"
        logger.info(f"API Request: {method} {endpoint}")

        kwargs["headers"] = kwargs.get("headers", self.headers)
        resp = requests.request(method, url, **kwargs)

        if not resp.ok:
            logger.error(f"API Error {resp.status_code}: {endpoint}")
            logger.error(f"Response: {resp.text}")
            try:
                # Attempt to log JSON error details if available
                error_details = resp.json()
                logger.error(f"Error Details: {json.dumps(error_details, indent=2)}")
            except requests.exceptions.JSONDecodeError:
                pass # Ignore if response body isn't JSON
            resp.raise_for_status()
        return resp

    def list_workspaces(self) -> list[Dict]:
        """List all workspaces in organization."""
        resp = self._make_request("GET", "/api/v1/workspaces")
        return resp.json()

    def workspace_exists(self, name: str) -> Tuple[bool, Optional[str]]:
        """Check if workspace exists, return (exists, workspace_id)."""
        workspaces = self.list_workspaces()
        for ws in workspaces:
            if ws["display_name"] == name:
                logger.info(f"Workspace '{name}' found with ID: {ws['id']}")
                return True, ws["id"]
        logger.info(f"Workspace '{name}' not found.")
        return False, None

    def key_exists(self, description: str) -> Tuple[bool, Optional[str]]:
        """Check if key exists, return (exists, key_id)."""
        resp = self._make_request("GET", "/api/v1/api-key")
        keys = resp.json()

        for k in keys:
            if k["description"] == description:
                logger.info(f"API Key with description '{description}' already exists.")
                return True, k["id"]
        logger.info(f"API Key with description '{description}' does not exist.")
        return False, None

    def create_api_key(self, workspace_id: str, description: str) -> str:
        """Create service key for workspace."""
        logger.info("Fetching roles to determine role_id...")
        roles_resp = self._make_request("GET", "/api/v1/orgs/current/roles")
        roles = roles_resp.json()

        # Find the specific role required for a service key tied to a workspace
        ws_role = next((r for r in roles if r["name"] == "WORKSPACE_USER"
                         and r.get("access_scope") == "workspace"), None)

        if not ws_role:
             raise ValueError("Could not find required 'WORKSPACE_USER' role for API key creation.")

        logger.info(f"Creating API key with role ID: {ws_role['id']}")

        resp = self._make_request("POST", "/api/v1/api-key",
                            json={
                                "description": description,
                                "workspaces": [workspace_id],
                                "role_id": ws_role['id']
                            }
                        )
        key_data = resp.json()
        logger.info(f"Successfully created API key: {key_data['key'][:20]}...")
        return key_data["key"]

    def auto_create(self, description: str, workspace_name: str="nsagent-users") -> str:
        """Complete workflow: manages workspace and creates API key. Returns API Key string."""
        logger.info(f"Starting auto-creation process for key description '{description}'")

        # 1. Check Workspace Existence (Must exist for key creation)
        logger.info(f"Checking workspace '{workspace_name}' existence...")
        ws_exists, ws_id = self.workspace_exists(workspace_name)

        if not ws_exists:
            logger.error(f"Required workspace '{workspace_name}' does not exist. Cannot proceed.")
            sys.exit(1)

        # 2. Check Key Existence
        is_key, key_id = self.key_exists(description)
        if is_key:
            logger.error(f"Key with description '{description}' already exists. ID: {key_id} Operation aborted.")
            sys.exit(1)

        # 3. Create API Key
        api_key = self.create_api_key(ws_id, description)

        return api_key

def main():
    if not ADMIN_API_KEY or not ORG_ID:
        logger.error("Required environment variables are not set:")
        logger.error("export LANGSMITH_ADMIN_API_KEY='lsv2_...'")
        logger.error("export LANGSMITH_ORG_ID='org_...'")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="LangSmith Workspace API Key Creator")
    parser.add_argument(
        "-d",
        "--description",
        required=True,
        help="Description (branch_name from jira) of the new API service key"
    )
    args = parser.parse_args()
    description = args.description

    manager = LangSmithManager(ADMIN_API_KEY, ORG_ID)

    try:
        # The auto_create function now returns only the API key string
        api_key = manager.auto_create(description, WORKSPACE_NAME)

        # Print ONLY the API key to stdout for easy capture by calling scripts
        print(api_key)

    except Exception as e:
        logger.critical(f"A critical exception occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
