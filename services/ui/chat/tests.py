import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Generator

import pytest
import requests
from playwright.sync_api import Page, expect

# This test does not require database access.

API_ROOT = Path(__file__).resolve().parent.parent.parent / "api"
UI_ROOT = Path(__file__).resolve().parent.parent.parent / "ui"
API_PORT = 8010
UI_PORT = 8011
API_URL = f"http://127.0.0.1:{API_PORT}"
UI_URL = f"http://127.0.0.1:{UI_PORT}"


@pytest.fixture(scope="module")  # type: ignore[misc]
def api_server() -> Generator[None, None, None]:
    """Fixture to start and stop the FastAPI server."""
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "services.api.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(API_PORT),
    ]
    env = os.environ.copy()
    project_root = str(API_ROOT.parent.parent)
    src_path = os.path.join(project_root, "src")
    env["PYTHONPATH"] = f"{project_root}{os.pathsep}{src_path}"
    process = subprocess.Popen(
        command,
        cwd=project_root,  # Run from the project root
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    start_time = time.time()
    timeout = 30
    while True:
        try:
            response = requests.get(f"{API_URL}/healthz", timeout=1)
            if response.status_code == 200:
                break
        except requests.ConnectionError:
            if time.time() - start_time > timeout:
                process.terminate()
                stdout, stderr = process.communicate()
                raise RuntimeError(
                    f"API server failed to start within {timeout} seconds.\n"
                    f"STDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
                )
            time.sleep(0.5)
    yield
    process.terminate()
    process.wait()


@pytest.fixture(scope="module")  # type: ignore[misc]
def django_ui_server() -> Generator[None, None, None]:
    """Fixture to start and stop the Django development server."""
    manage_py_path = UI_ROOT / "manage.py"
    project_root = UI_ROOT.parent.parent

    command = [
        sys.executable,
        str(manage_py_path),
        "runserver",
        f"127.0.0.1:{UI_PORT}",
    ]
    env = os.environ.copy()
    # Pass the API_URL to the Django settings
    env["API_URL"] = f"{API_URL}/invoke"
    # Add project root and src to PYTHONPATH so Django can find its settings
    src_path = project_root / "src"
    env["PYTHONPATH"] = f"{project_root}{os.pathsep}{src_path}"

    process = subprocess.Popen(
        command,
        cwd=str(project_root),  # Run from the project root
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for the server to be ready
    start_time = time.time()
    timeout = 30
    while True:
        try:
            # Try to connect to the server to see if it's up
            with socket.create_connection(("127.0.0.1", UI_PORT), timeout=1):
                break
        except (socket.timeout, ConnectionRefusedError):
            if time.time() - start_time > timeout:
                process.terminate()
                stdout, stderr = process.communicate()
                raise RuntimeError(
                    f"Django UI server failed to start within {timeout} seconds.\n"
                    f"STDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
                )
            time.sleep(0.5)

    yield
    process.terminate()
    process.wait()


def test_real_ui_api_integration(
    api_server: Any, django_ui_server: Any, page: Page
) -> None:
    """
    A true end-to-end test that runs the real Django UI and FastAPI backend,
    ensuring they can communicate correctly.
    """
    # 1. Navigate to the running Django UI service
    # The URL is defined in chat/urls.py, which is at the root of the app
    page.goto(f"{UI_URL}/", wait_until="networkidle")

    # 2. Find the input and send a message
    input_box = page.locator("#chat-message-input")
    expect(input_box).to_be_visible()
    input_box.fill(
        "Subject: Quarterly Report\n\nHi team, here is the quarterly report."
    )
    input_box.press("Enter")

    # 3. Wait for the response from the REAL API and verify it
    # The key is to ensure the "Error communicating" message does NOT appear.
    expect(page.locator("body")).not_to_contain_text(
        "Error communicating with the API", timeout=5000
    )

    # 4. Check that an assistant message appeared.
    # The exact content depends on the default graph state, but a response should exist.
    response_box = page.locator(".message.assistant").first
    expect(response_box).to_contain_text("Assistant:", timeout=30000)

    # Print the assistant's output for review
    assistant_output = response_box.inner_text()
    print(f"\nAssistant output:\n{assistant_output}\n")

    # 5. Verify the response does not contain an error message.
    expect(response_box).not_to_contain_text("Error")


def test_conversation_flow(api_server: Any, django_ui_server: Any, page: Page) -> None:
    """
    Tests a multi-step conversation to ensure the backend handles
    stateful interactions correctly, including refinement and ending.
    """
    # 1. Navigate to the UI
    page.goto(f"{UI_URL}/", wait_until="networkidle")
    input_box = page.locator("#chat-message-input")
    expect(input_box).to_be_visible()

    # 2. Start the conversation
    input_box.fill("Subject: Hello\n\nHi there, can you write a reply?")
    input_box.press("Enter")

    # 3. Wait for the tone prompt
    expect(page.locator("body")).to_contain_text(
        "Enter the desired tone for the draft", timeout=10000
    )

    # 4. Provide the tone
    input_box.fill("formal")
    input_box.press("Enter")

    # 5. Verify the first draft
    expect(page.locator("body")).not_to_contain_text(
        "Error communicating with the API", timeout=5000
    )
    expect(page.locator(".message.assistant").last).to_contain_text(
        "Here's a draft", timeout=30000
    )

    # 6. Ask for a refinement
    input_box.fill("Make it more friendly")
    input_box.press("Enter")

    # 7. Verify the refined draft
    expect(page.locator("body")).not_to_contain_text(
        "Error communicating with the API", timeout=5000
    )
    expect(page.locator(".message.assistant").last).to_contain_text(
        "Here's a revised draft", timeout=30000
    )

    # 8. End the conversation
    input_box.fill("Looks good, thanks!")
    input_box.press("Enter")

    # 9. Verify the closing message
    expect(page.locator("body")).not_to_contain_text(
        "Error communicating with the API", timeout=5000
    )
    expect(page.locator(".message.assistant").last).to_contain_text(
        "You're welcome!", timeout=30000
    )
