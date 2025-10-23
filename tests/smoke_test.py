import os
import sys

import requests


def run_smoke_tests():
    """
    Runs smoke tests against the deployed UI and API services.
    Expects the service URLs to be in environment variables.
    """
    ui_url = os.environ.get("UI_URL")
    api_url = os.environ.get("API_URL")

    if not ui_url or not api_url:
        print("Error: UI_URL and API_URL environment variables must be set.")
        sys.exit(1)

    errors = []

    # Test UI health
    try:
        response = requests.get(ui_url, timeout=60)
        if response.status_code == 200:
            print(f"UI health check PASSED ({ui_url})")
        else:
            errors.append(
                f"UI health check FAILED ({ui_url}): Status code {response.status_code}"
            )
    except requests.RequestException as e:
        errors.append(f"UI health check FAILED ({ui_url}): {e}")

    # Test API health
    try:
        health_url = f"{api_url}/healthz"
        response = requests.get(health_url, timeout=60)
        if response.status_code == 200 and response.json().get("status") == "ok":
            print(f"API health check PASSED ({health_url})")
        else:
            errors.append(
                (
                    f"API health check FAILED ({health_url}): "
                    f"Status {response.status_code}, Body {response.text}"
                )
            )
    except requests.RequestException as e:
        errors.append(f"API health check FAILED ({health_url}): {e}")

    if errors:
        print("\n--- Smoke Test Failures ---")
        for error in errors:
            print(error)
        print("---------------------------")
        sys.exit(1)
    else:
        print("\nAll smoke tests passed!")


if __name__ == "__main__":
    run_smoke_tests()
