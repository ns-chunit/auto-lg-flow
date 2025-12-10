import os
import argparse
import subprocess
import sys

# --- Configuration ---
# Define required environment variables
REQUIRED_ENV_VARS = [
    "APISIX_ADMIN_API_KEY",
    "LANGSMITH_ADMIN_API_KEY",
    "LANGSMITH_ORG_ID",
]

LG_AUTO_KEY_SCRIPT = "lg/auto_key.py"
ONEPASSWORD_AUTO_SCRIPT = "1password/auto_1password.py"
APISIX_AUTO_SCRIPT = "apisix/auto_as_add.py"


def run_command(command_list, check=True, capture_output=False, text=True):
    """
    Execute an external command and handle its result.
    """
    try:
        # sys.executable ensures the script is run with the same Python interpreter
        # that is running the main script.
        result = subprocess.run(
            command_list,
            check=check,  # Raises CalledProcessError if return code is non-zero
            capture_output=capture_output,  # Capture stdout and stderr
            text=text,  # Decode stdout/stderr as strings
            encoding='utf-8'
        )
        return result
    except subprocess.CalledProcessError as e:
        print(f"❌ Command execution failed: {' '.join(command_list)}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ Command not found: {command_list[0]}. Please ensure it is installed and in your PATH.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ An unknown error occurred: {e}")
        sys.exit(1)


def check_prerequisites():
    """
    Performs checks: 1Password CLI sign-in status and environment variables.
    """
    print("--- Checking 1Password CLI (op) Sign-in Status ---")
    # Check 1Password CLI sign-in status (using op whoami)
    try:
        run_command(["op", "whoami"], check=True, capture_output=True)
        print("✅ 1Password CLI (op) is signed in.")
    except subprocess.CalledProcessError:
        print("❌ 1Password CLI sign-in check failed. Please sign in using `op signin`.")
        sys.exit(1)

    print("\n--- Checking Environment Variables ---")
    # Check required environment variables
    all_env_ok = True
    for var in REQUIRED_ENV_VARS:
        if os.environ.get(var):
            print(f"✅ Environment variable {var} is set.")
        else:
            print(f"❌ Missing environment variable {var}.")
            all_env_ok = False

    if not all_env_ok:
        print("\n🚨 Missing required environment variables. Please set them and try again.")
        sys.exit(1)

    print("✅ All environment variables check passed.")


def parse_arguments():
    """
    Parse email and branch_name arguments.
    """
    epilog_text = """
Prerequisites:
1. 1Password CLI (op) must be signed in using `eval $(op signin)`.
2. The following environment variables must be set:
   - APISIX_ADMIN_API_KEY
   - LANGSMITH_ADMIN_API_KEY
   - LANGSMITH_ORG_ID
"""
    parser = argparse.ArgumentParser(
        description="Integrated script to run multiple automation tasks.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=epilog_text
    )
    parser.add_argument(
        "-e", "--email",
        required=True,
        help="User's email address."
    )
    parser.add_argument(
        "-b", "--branch_name",
        required=True,
        help="Project's branch name."
    )
    return parser.parse_args()


def main():
    args = parse_arguments()
    email = args.email
    branch_name = args.branch_name

    # Perform all necessary checks
    check_prerequisites()

    lg_key = None
    sharing_link = None

    print("\n--- Executing lg/auto_key.py to get lg_key ---")
    cmd_lg = [sys.executable, LG_AUTO_KEY_SCRIPT, "-d", branch_name]
    result_lg = run_command(cmd_lg, capture_output=True)

    # Get lg_key, assuming it is the last line of stdout
    output_lines_lg = result_lg.stdout.strip().split('\n')
    if output_lines_lg:
        lg_key = output_lines_lg[-1].strip()
        print(f"✅ lg/auto_key.py executed successfully. Acquired lg_key: {lg_key[:5]}...{lg_key[-5:]}")
    else:
        print("❌ Failed to acquire lg_key from lg/auto_key.py output.")
        sys.exit(1)

    print("\n--- Executing auto_1password.py to get sharing link ---")
    cmd_1p = [sys.executable, ONEPASSWORD_AUTO_SCRIPT, branch_name, lg_key, email]
    result_1p = run_command(cmd_1p, capture_output=True)

    # Get sharing link, assuming it is the last line of stdout
    output_lines_1p = result_1p.stdout.strip().split('\n')
    if output_lines_1p:
        sharing_link = output_lines_1p[-1].strip()
        print(f"✅ 1password/auto_1password.py executed successfully. Acquired sharing link: {sharing_link}")
    else:
        print("❌ Failed to acquire sharing link from 1password/auto_1password.py output.")
        sys.exit(1)

    print("\n--- Executing apisix/auto_as_add.py ---")
    cmd_apisix = [sys.executable, APISIX_AUTO_SCRIPT, branch_name]
    run_command(cmd_apisix)
    print("✅ apisix/auto_as_add.py executed successfully.")

    print("\n====================================")
    print("Script Execution Complete!")
    print("====================================")
    print(f"  lg_key:        {lg_key}")
    print(f"  Sharing Link:  {sharing_link}")
    print("====================================")


if __name__ == "__main__":
    main()

