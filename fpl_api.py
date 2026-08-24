"""
FPL API Client: Supports both modern OIDC (Bearer / X-Api-Authorization) and legacy Cookie authentication.
"""
import json
import logging
from datetime import datetime, timezone
import requests

from config import FPL_BASE_URL

logger = logging.getLogger("FPLBot")

class FPLClient:
    def __init__(self, team_id: int, auth_token: str = ""):
        self.team_id = team_id
        self.auth_token = auth_token.strip()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://fantasy.premierleague.com/",
            "Origin": "https://fantasy.premierleague.com",
            "Accept": "application/json, text/plain, */*",
        })
        self._setup_auth()

    def _setup_auth(self):
        """Configures authentication headers based on provided auth token or JSON string."""
        if not self.auth_token:
            return

        # Check if auth_token is an OIDC JSON object (from localStorage oidc.user)
        if "{" in self.auth_token and "}" in self.auth_token:
            try:
                data = json.loads(self.auth_token)
                access_token = data.get("access_token") or data.get("id_token")
                if access_token:
                    self.session.headers.update({
                        "X-Api-Authorization": f"Bearer {access_token}",
                        "Authorization": f"Bearer {access_token}"
                    })
                    logger.info("Configured modern OIDC Bearer token authentication.")
                    return
            except Exception as e:
                logger.warning(f"Could not parse auth token as JSON: {e}")

        # Check if raw JWT Bearer token
        if self.auth_token.startswith("eyJ"):
            self.session.headers.update({
                "X-Api-Authorization": f"Bearer {self.auth_token}",
                "Authorization": f"Bearer {self.auth_token}"
            })
            logger.info("Configured Bearer token authentication.")
            return

        # Legacy cookie fallback
        cookie_val = self.auth_token if "pl_profile=" in self.auth_token or "=" in self.auth_token else f"pl_profile={self.auth_token}"
        self.session.headers.update({"Cookie": cookie_val})

    def get_bootstrap(self) -> dict:
        """Fetches core game data: all players, clubs, gameweeks, and positions."""
        url = f"{FPL_BASE_URL}/bootstrap-static/"
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_fixtures(self, event_id: int = None) -> list:
        """Fetches upcoming fixtures and difficulty ratings."""
        url = f"{FPL_BASE_URL}/fixtures/"
        params = {"event": event_id} if event_id else {}
        resp = self.session.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()

    def get_next_event(self, bootstrap: dict) -> tuple[dict, datetime]:
        """Identifies the next active gameweek and its deadline time."""
        events = bootstrap.get("events", [])
        next_events = [e for e in events if e.get("is_next")]
        if not next_events:
            next_events = [e for e in events if not e.get("finished")]
        
        if not next_events:
            raise ValueError("No upcoming gameweek event found in FPL data.")
        
        next_event = next_events[0]
        deadline_str = next_event["deadline_time"]
        deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        return next_event, deadline

    def get_current_picks(self, bootstrap: dict) -> tuple[list, dict]:
        """
        Retrieves the team's current 15 picks and financial summary.
        Attempts authenticated /my-team/ endpoint first; falls back to public /picks/ if unauthenticated.
        """
        if self.auth_token:
            url = f"{FPL_BASE_URL}/my-team/{self.team_id}/"
            try:
                resp = self.session.get(url, timeout=15)
                if resp.status_code == 200:
                    data = resp.json()
                    transfers_info = data.get("transfers", {})
                    summary = {
                        "bank": transfers_info.get("bank", 0),
                        "value": transfers_info.get("value", 1000),
                        "free_transfers": transfers_info.get("limit", 1) - transfers_info.get("made", 0),
                        "authenticated": True
                    }
                    return data.get("picks", []), summary
                else:
                    logger.warning(f"Authenticated my-team request returned status {resp.status_code}. Using public data fallback.")
            except Exception as e:
                logger.warning(f"Failed to fetch authenticated team data: {e}. Falling back to public data.")

        # Fallback to public endpoints
        events = bootstrap.get("events", [])
        current_or_prev_events = [e for e in events if e.get("is_current") or e.get("is_previous")]
        event_id = current_or_prev_events[-1]["id"] if current_or_prev_events else 1

        picks_url = f"{FPL_BASE_URL}/entry/{self.team_id}/event/{event_id}/picks/"
        entry_url = f"{FPL_BASE_URL}/entry/{self.team_id}/"

        picks_resp = self.session.get(picks_url, timeout=15)
        picks_resp.raise_for_status()
        picks_data = picks_resp.json()

        entry_resp = self.session.get(entry_url, timeout=15)
        entry_resp.raise_for_status()
        entry_data = entry_resp.json()

        history = picks_data.get("entry_history", {})
        summary = {
            "bank": history.get("bank", 0),
            "value": history.get("value", 1000),
            "free_transfers": 1,
            "authenticated": False
        }
        return picks_data.get("picks", []), summary

    def update_lineup(self, picks_payload: list) -> bool:
        """Submits updated Starting XI, bench order, Captain, and Vice-Captain."""
        if not self.auth_token:
            logger.error("Cannot submit lineup update: No auth token provided.")
            return False

        url = f"{FPL_BASE_URL}/my-team/{self.team_id}/"
        body = {
            "chip": None,
            "picks": picks_payload
        }
        resp = self.session.post(url, json=body, timeout=15)
        if resp.status_code == 200:
            logger.info("Successfully updated Starting XI, bench order, and captaincy on FPL!")
            return True
        else:
            logger.error(f"Failed to update lineup. Status {resp.status_code}: {resp.text}")
            return False

    def execute_transfers(self, transfers_list: list, event_id: int) -> bool:
        """Executes player transfers on FPL API."""
        if not self.auth_token:
            logger.error("Cannot execute transfers: No auth token provided.")
            return False

        url = f"{FPL_BASE_URL}/transfers/"
        body = {
            "chip": None,
            "entry": self.team_id,
            "event": event_id,
            "transfers": transfers_list
        }
        resp = self.session.post(url, json=body, timeout=15)
        if resp.status_code == 200:
            logger.info("Successfully executed transfers on FPL!")
            return True
        else:
            logger.error(f"Failed to execute transfers. Status {resp.status_code}: {resp.text}")
            return False
