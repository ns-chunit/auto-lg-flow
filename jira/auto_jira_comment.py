import argparse
import os
import requests
import sys
import json

def add_comment_to_jira_ticket(issue_key, email, comment_text):
    """
    Sends a POST request to the Jira API to add a comment to a specified ticket.

    Args:
        issue_key (str): The key of the Jira issue (e.g., ENG-701259).
        email (str): The email address used for Jira authentication.
        comment_text (str): The text content of the comment to add.
    """
    # Retrieve API Key from Environment Variable
    api_token = os.environ.get('ATLASSIAN_API_KEY')
    if not api_token:
        print("ERROR: Environment variable 'ATLASSIAN_API_KEY' is not set.")
        print("Please set it to your generated Atlassian API token.")
        sys.exit(1)

    # Define API endpoint and authentication details
    # Base URL for netskope.atlassian.net
    base_url = "https://netskope.atlassian.net"
    api_url = f"{base_url}/rest/api/3/issue/{issue_key}/comment"

    # Basic Authentication tuple (email, API_TOKEN)
    auth = (email, api_token)

    # Construct the Request Body (using Atlassian Document Format - ADF)
    payload = {
        "body": {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "text": comment_text,
                            "type": "text"
                        }
                    ]
                }
            ]
        }
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    print(f"Attempting to add comment to Jira ticket: {issue_key}...")

    try:
        response = requests.post(
            api_url,
            auth=auth,
            headers=headers,
            data=json.dumps(payload)
        )

        if response.status_code == 201:
            print("SUCCESS: Comment added successfully.")
            # Optional: Print the newly created comment ID
            print(f"Comment ID: {response.json().get('id')}")
        else:
            print(f"ERROR: Failed to add comment. Status Code: {response.status_code}")
            # Print detailed error message from Jira API
            try:
                error_details = response.json()
                print("Jira API Response Error Details:")
                print(json.dumps(error_details, indent=2))
            except json.JSONDecodeError:
                print("Raw response content:")
                print(response.text)

            # Common status code hints
            if response.status_code == 401:
                print("Hint: Check your EMAIL and ATLASSIAN_API_KEY for correct credentials/permissions.")
            elif response.status_code == 404:
                print(f"Hint: Issue key '{issue_key}' might not exist, or the user does not have 'Browse' permission.")
            elif response.status_code == 400:
                print("Hint: The request body format might be incorrect.")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred during the request: {e}")
        sys.exit(1)


def main():
    """
    Main function to parse arguments and call the comment function.
    """
    parser = argparse.ArgumentParser(
        description="Adds a comment to a specified Jira ticket. Requires 'ATLASSIAN_API_KEY' environment variable to be set.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        '-t', '--ticket-id',
        required=True,
        dest='issue_key',
        help='The Jira ticket ID/Key (e.g., ENG-701259).'
    )
    parser.add_argument(
        '-e', '--email',
        required=True,
        help='Your Atlassian login email address.'
    )
    parser.add_argument(
        '-c', '--comment',
        required=True,
        dest='comment_text',
        help='The string content you wish to post as a comment.'
    )

    args = parser.parse_args()

    add_comment_to_jira_ticket(args.issue_key, args.email, args.comment_text)


if __name__ == "__main__":
    main()
