#!/usr/bin/env python3
"""
Constant Contact v3 minimal Python client for adding contacts & managing lists.

Setup:
  1) Copy this file somewhere in your project, e.g. cc_client.py
  2) Create a .env file next to it (or set environment variables):
       CC_CLIENT_ID=14140efd-c5c5-4240-996f-e58fc1089ee0
       CC_REFRESH_TOKEN=PUT_YOUR_REFRESH_TOKEN_HERE
     (Optional) To persist rotating refresh tokens back to disk, also set:
       CC_ENV_PATH=.env

Usage examples (from the command line):
  $ python cc_client.py lists
  $ python cc_client.py upsert jane@example.com "Jane" "LIST_ID"
  $ python cc_client.py create-contact john@example.com "John" "LIST_ID"

Programmatic use:
  from cc_client import ConstantContactClient
  cc = ConstantContactClient()
  cc.upsert_contact(email="jane@example.com", first_name="Jane", list_ids=["LIST_ID"])
"""
import os
import json
import time
import argparse
from typing import List, Optional, Dict, Any

try:
    import requests
except ImportError as e:
    raise SystemExit("This script requires the 'requests' package. Install it with: pip install requests") from e

AUTH_BASE = "https://authz.constantcontact.com/oauth2/default/v1"
API_BASE = "https://api.cc.email/v3"

class ConstantContactClient:
    def __init__(self,
                 client_id: Optional[str] = None,
                 refresh_token: Optional[str] = None,
                 env_path: Optional[str] = None):
        # Load from env
        self.client_id = client_id or os.getenv("CC_CLIENT_ID")
        self.refresh_token = refresh_token or os.getenv("CC_REFRESH_TOKEN")
        # Optional: where to persist the rotated refresh token
        self.env_path = env_path or os.getenv("CC_ENV_PATH")

        if not self.client_id or not self.refresh_token:
            raise ValueError("Missing CC_CLIENT_ID or CC_REFRESH_TOKEN. Set them as env vars or in a .env file.")

        self.access_token: Optional[str] = None
        self.access_expiry: float = 0.0  # epoch seconds

    # -------- Token handling --------
    def _save_rotated_refresh_token(self, new_refresh: str) -> None:
        """Persist rotated refresh token back to the .env file if CC_ENV_PATH is set."""
        self.refresh_token = new_refresh
        if not self.env_path:
            return  # nothing to persist
        path = Path(self.env_path)
        # Read current .env (if exists), replace CC_REFRESH_TOKEN line, otherwise append
        lines = []
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                lines = f.read().splitlines()

        replaced = False
        for i, line in enumerate(lines):
            if line.startswith("CC_REFRESH_TOKEN="):
                lines[i] = f"CC_REFRESH_TOKEN={new_refresh}"
                replaced = True
                break
        if not replaced:
            lines.append(f"CC_REFRESH_TOKEN={new_refresh}")

        # Ensure CLIENT_ID is present as well for convenience
        if self.client_id and not any(l.startswith("CC_CLIENT_ID=") for l in lines):
            lines.append(f"CC_CLIENT_ID={self.client_id}")

        with path.open("w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def _refresh_access_token(self) -> None:
        """Use refresh_token to obtain a new access token (and rotated refresh token)."""
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "refresh_token": self.refresh_token,
        }
        r = requests.post(f"{AUTH_BASE}/token",
                          headers={"Content-Type": "application/x-www-form-urlencoded"},
                          data=data,
                          timeout=30)
        if r.status_code != 200:
            raise RuntimeError(f"Failed to refresh token: {r.status_code} {r.text}")
        j = r.json()
        self.access_token = j["access_token"]
        # access tokens commonly include an 'expires_in' field (seconds); default to 1 hour if absent.
        self.access_expiry = time.time() + float(j.get("expires_in", 3600)) * 0.9  # refresh a bit early
        # Rotating refresh token: save the new one
        new_refresh = j.get("refresh_token")
        if new_refresh:
            self._save_rotated_refresh_token(new_refresh)

    def _ensure_token(self) -> None:
        """Ensure there is a valid, non-expired access token."""
        if not self.access_token or time.time() > self.access_expiry:
            self._refresh_access_token()

    # -------- API helpers --------
    def _headers(self) -> Dict[str, str]:
        self._ensure_token()
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    # Lists
    def list_contact_lists(self) -> Dict[str, Any]:
        r = requests.get(f"{API_BASE}/contact_lists", headers=self._headers(), timeout=30)
        if r.status_code == 401:
            # try one refresh then retry
            self._refresh_access_token()
            r = requests.get(f"{API_BASE}/contact_lists", headers=self._headers(), timeout=30)
        r.raise_for_status()
        return r.json()

    def create_list(self, name: str, favorite: bool = False, description: Optional[str] = None) -> Dict[str, Any]:
        payload = {"name": name, "favorite": favorite}
        if description:
            payload["description"] = description
        r = requests.post(f"{API_BASE}/contact_lists", headers=self._headers(), json=payload, timeout=30)
        if r.status_code == 401:
            self._refresh_access_token()
            r = requests.post(f"{API_BASE}/contact_lists", headers=self._headers(), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    # Contacts
    def create_contact(self,
                       email: str,
                       first_name: Optional[str] = None,
                       last_name: Optional[str] = None,
                       list_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        payload = {
            "create_source": "Account",
            "email_address": {"address": email},
        }
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if list_ids:
            payload["list_memberships"] = list_ids
        r = requests.post(f"{API_BASE}/contacts", headers=self._headers(), json=payload, timeout=30)
        if r.status_code == 401:
            self._refresh_access_token()
            r = requests.post(f"{API_BASE}/contacts", headers=self._headers(), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

    def upsert_contact(self,
                       email: str,
                       first_name: Optional[str] = None,
                       last_name: Optional[str] = None,
                       list_ids: Optional[List[str]] = None,
                       sms_subscriber: Optional[bool] = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "email_address": email,
        }
        if first_name:
            payload["first_name"] = first_name
        if last_name:
            payload["last_name"] = last_name
        if list_ids:
            payload["list_memberships"] = list_ids
        if sms_subscriber is not None:
            payload["sms_subscriber"] = sms_subscriber
        r = requests.post(f"{API_BASE}/contacts/sign_up_form", headers=self._headers(), json=payload, timeout=30)
        if r.status_code == 401:
            self._refresh_access_token()
            r = requests.post(f"{API_BASE}/contacts/sign_up_form", headers=self._headers(), json=payload, timeout=30)
        r.raise_for_status()
        return r.json()

def _cli():
    parser = argparse.ArgumentParser(description="Constant Contact v3 helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("lists", help="List contact lists")

    p_create_list = sub.add_parser("create-list", help="Create a new list")
    p_create_list.add_argument("name")
    p_create_list.add_argument("--favorite", action="store_true")
    p_create_list.add_argument("--description")

    p_create_contact = sub.add_parser("create-contact", help="Create a new contact")
    p_create_contact.add_argument("email")
    p_create_contact.add_argument("--first")
    p_create_contact.add_argument("--last")
    p_create_contact.add_argument("--list", action="append", dest="list_ids", help="List ID (repeatable)")

    p_upsert = sub.add_parser("upsert", help="Create or update a contact (sign_up_form)")
    p_upsert.add_argument("email")
    p_upsert.add_argument("--first")
    p_upsert.add_argument("--last")
    p_upsert.add_argument("--list", action="append", dest="list_ids", help="List ID (repeatable)")
    p_upsert.add_argument("--sms", action="store_true", help="Mark as SMS subscriber")

    args = parser.parse_args()

    cc = ConstantContactClient()

    if args.cmd == "lists":
        print(json.dumps(cc.list_contact_lists(), indent=2))
    elif args.cmd == "create-list":
        print(json.dumps(cc.create_list(args.name, favorite=args.favorite, description=args.description), indent=2))
    elif args.cmd == "create-contact":
        print(json.dumps(cc.create_contact(args.email, first_name=args.first, last_name=args.last, list_ids=args.list_ids), indent=2))
    elif args.cmd == "upsert":
        print(json.dumps(cc.upsert_contact(args.email, first_name=args.first, last_name=args.last, list_ids=args.list_ids, sms_subscriber=args.sms), indent=2))

if __name__ == "__main__":
    _cli()
