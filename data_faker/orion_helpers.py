"""Shared helpers for talking to the Orion Context Broker (NGSI v2)."""

from dataclasses import dataclass
from typing import Any, Dict

import requests


@dataclass
class OrionClient:
    """Lightweight client encapsulating Orion URLs and common request helpers."""

    base_url: str
    service_path: str
    request_timeout: int = 5

    @property
    def entities_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/v2/entities"

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "FIWARE-ServicePath": self.service_path,
        }

    @property
    def headers_no_body(self) -> Dict[str, str]:
        return {
            "FIWARE-ServicePath": self.service_path,
        }

    @staticmethod
    def response_detail(response: requests.Response) -> str:
        """Extract Orion error description for logging."""
        try:
            data = response.json()
            error = data.get("error", "")
            description = data.get("description", "")
            detail = " ".join(part for part in (error, description) if part)
            return detail or response.text
        except ValueError:
            return response.text

    def is_entity_exists_err(self, response: requests.Response) -> bool:
        """Return True if Orion reports the entity already exists."""
        detail = self.response_detail(response).lower()
        return "already exists" in detail

    def delete_entity(self, session: requests.Session, entity_id: str) -> bool:
        """Delete an existing entity to allow recreation."""
        try:
            resp = session.delete(
                f"{self.entities_url}/{entity_id}",
                headers=self.headers_no_body,
                timeout=self.request_timeout,
            )
        except requests.RequestException as exc:
            print(f"[error] delete {entity_id} failed: {exc}")
            return False

        if resp.status_code in (204, 404):
            print(f"[delete] {entity_id} removed before recreation")
            return True

        print(f"[error] delete {entity_id} failed: {resp.status_code} {self.response_detail(resp)}")
        return False

    def send_entity(self, session: requests.Session, entity: Dict[str, Dict[str, Any]], action: str) -> bool:
        """Send create or update payloads to Orion, mirroring the lab templates."""
        try:
            if action == "create":
                response = session.post(
                    self.entities_url,
                    json=entity,
                    headers=self.headers,
                    timeout=self.request_timeout,
                )
                if response.status_code == 422 and self.is_entity_exists_err(response):
                    if self.delete_entity(session, entity["id"]):
                        response = session.post(
                            self.entities_url,
                            json=entity,
                            headers=self.headers,
                            timeout=self.request_timeout,
                        )
                        print(f"[debug] send_to_orion create response: {response.status_code} {response.text} {response.headers}")
                expected = 201
            else:
                attrs = {k: v for k, v in entity.items() if k not in ("id", "type")}
                response = session.patch(
                    f"{self.entities_url}/{entity['id']}/attrs",
                    json=attrs,
                    headers=self.headers,
                    timeout=self.request_timeout,
                )
                expected = 204
        except requests.RequestException as exc:
            print(f"[error]  {action} {entity['id']} failed: {exc}")
            return False

        if response.status_code != expected:
            detail = self.response_detail(response)
            print(f"[error] send_to_orion {action} {entity['id']} failed: {response.status_code} {detail}")
            return False

        return True
