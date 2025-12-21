"""HTTP server for managing and receiving scoped Orion subscriptions."""

import argparse
import atexit
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from debug import print_context  # noqa: F401

import requests
from flask import Flask, Response, request

from backend import config

DEFAULT_ORION_URL = config.ORION_URL
DEFAULT_SERVICE = config.FIWARE_SERVICE
DEFAULT_SERVICE_PATH = config.FIWARE_SERVICE_PATH
DEFAULT_ENTITY_TYPE = "TrafficAccident"
REQUEST_TIMEOUT = 5

app = Flask(__name__)
subscription_id: Optional[str] = None


def _headers(service: str, service_path: str) -> Dict[str, str]:
    """Return Orion headers for the given service scope."""
    return {
        "Content-Type": "application/json",
        "FIWARE-Service": service,
        "FIWARE-ServicePath": service_path,
    }


def _existing_subscription(
    orion_url: str,
    service: str,
    service_path: str,
    description: str,
    callback_url: str,
) -> Optional[str]:
    """Return the id of an existing subscription that matches our needs."""
    try:
        resp = requests.get(
            f"{orion_url}/v2/subscriptions",
            headers=_headers(service, service_path),
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"[error] Failed to list subscriptions: {exc}")
        return None

    for sub in resp.json():
        if sub.get("description") != description:
            continue
        url = sub.get("notification", {}).get("http", {}).get("url")
        if url == callback_url:
            return sub.get("id")
    return None


def _create_subscription(
    orion_url: str,
    service: str,
    service_path: str,
    description: str,
    callback_url: str,
    entity_type: str,
) -> Optional[str]:
    """Create a new subscription for our service path and return its id."""
    payload = {
        "description": description,
        "subject": {
            "entities": [{"idPattern": ".*", "type": entity_type}],
        },
        "notification": {
            "http": {"url": DEFAULT_ORION_URL},
            "attrs": ["severity", "status", "location", "dateObserved"],
            "metadata": ["dateCreated", "dateModified"],
        },
    }
    try:
        resp = requests.post(
            f"{orion_url}/v2/subscriptions",
            headers=_headers(service, service_path),
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        
        print(f"[debug] Subscription creation response: {resp.status_code} {resp.text}")
        if resp.status_code != 201:
            print(f"[error] Subscription creation failed: {resp.status_code} {resp.text}")
            return None
    except requests.RequestException as exc:
        print(f"[error] Subscription creation failed: {exc}")
        return None

    location = resp.headers.get("Location")
    sub_id = location.rsplit("/", 1)[-1] if location else None
    if not sub_id:
        print("[warn] Subscription created but no Location header returned")
    else:
        print(f"[orion] Subscription created with id {sub_id}")
    return sub_id


def _delete_subscription(orion_url: str, service: str, service_path: str, sub_id: str) -> None:
    """Delete our subscription on shutdown."""
    try:
        resp = requests.delete(
            f"{orion_url}/v2/subscriptions/{sub_id}",
            headers=_headers(service, service_path),
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code not in (204, 404):
            print(f"[warn] Failed to delete subscription {sub_id}: {resp.status_code} {resp.text}")
        else:
            print(f"[orion] Subscription {sub_id} removed")
    except requests.RequestException as exc:
        print(f"[warn] Failed to delete subscription {sub_id}: {exc}")


def ensure_subscription(args) -> Optional[str]:
    """Find or create the subscription and return its id."""
    existing = _existing_subscription(
        args.orion_url,
        args.fiware_service,
        args.service_path,
        args.description,
        args.callback_url,
    )
    if existing:
        print(f"[orion] Reusing existing subscription {existing}")
        return existing
    return _create_subscription(
        args.orion_url,
        args.fiware_service,
        args.service_path,
        args.description,
        args.callback_url,
        args.entity_type,
    )


@app.route("/orion", methods=["POST"])
def receive_notification() -> Response:
    """Receive Orion notifications (JSON with a `data` array)."""
    payload: Optional[Dict[str, Any]] = request.get_json(silent=True)
    if not payload:
        print("[warn] Notification missing JSON payload")
        return Response(status=400)

    print(f"[notify] {json.dumps(payload, indent=2)}")
    return Response(status=204)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scoped Orion subscription receiver")
    parser.add_argument("--orion-url", default=DEFAULT_ORION_URL, help="Orion Context Broker base URL")
    parser.add_argument("--fiware-service", default=DEFAULT_SERVICE, help="FIWARE service header")
    parser.add_argument("--service-path", default=DEFAULT_SERVICE_PATH, help="FIWARE service path header")
    parser.add_argument("--entity-type", default=DEFAULT_ENTITY_TYPE, help="Entity type to subscribe to")
    parser.add_argument("--callback-url", default=config.SUBSCRIPTION_CALLBACK_URL, help="Public URL for Orion notifications")
    parser.add_argument("--description", default="Scoped accident subscription", help="Subscription description label")
    parser.add_argument("--host", default="0.0.0.0", help="Host interface for the local Flask server")
    parser.add_argument("--port", type=int, default=8080, help="Port for the local Flask server")
    parser.add_argument("--delete-on-exit", action="store_true", help="Delete the subscription when the process exits")
    return parser.parse_args()


def main() -> None:
    global subscription_id
    args = parse_args()

    subscription_id = ensure_subscription(args)
    if not subscription_id:
        print("[error] Unable to ensure subscription, exiting", file=sys.stderr)
        sys.exit(1)

    if args.delete_on_exit:
        atexit.register(_delete_subscription, args.orion_url, args.fiware_service, args.service_path, subscription_id)

    print(f"[server] Listening on {args.host}:{args.port}, expecting callbacks at {args.callback_url}")
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
