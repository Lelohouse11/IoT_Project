"""Shared helpers for talking to the Orion Context Broker (NGSI v2)."""

from dataclasses import dataclass
from typing import Any, Dict, Optional

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

    def get_entity(self, session: requests.Session, entity_id: str) -> Optional[Dict[str, Any]]:
        """Fetch an entity from Orion."""
        try:
            resp = session.get(
                f"{self.entities_url}/{entity_id}",
                headers=self.headers_no_body,
                timeout=self.request_timeout,
            )
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return None
            print(f"[warn] get {entity_id} failed: {resp.status_code} {self.response_detail(resp)}")
            return None
        except requests.RequestException as exc:
            print(f"[error] get {entity_id} failed: {exc}")
            return None

    def entities_are_equal(self, new_entity: Dict[str, Any], existing_entity: Dict[str, Any]) -> bool:
        """Check if new_entity is effectively the same as existing_entity."""
        ignored_keys = {"observationDateTime", "dateObserved"}
        
        for key, new_val in new_entity.items():
            if key in ignored_keys:
                continue
            
            if key not in existing_entity:
                return False
            
            existing_val = existing_entity[key]
            
            # Simple fields (id, type)
            if not isinstance(new_val, dict):
                if new_val != existing_val:
                    return False
                continue
                
            # Attributes (check value and type)
            # existing_val might have metadata, we ignore it for comparison
            if new_val.get("value") != existing_val.get("value"):
                return False
            if new_val.get("type") != existing_val.get("type"):
                return False
                
        return True

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
                    # Check if identical
                    existing = self.get_entity(session, entity["id"])
                    if existing and self.entities_are_equal(entity, existing):
                        print(f"[info] {entity['id']} already exists and is identical. Skipping.")
                        return True

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
