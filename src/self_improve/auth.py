"""Forge CLI authentication — reuse Claude Code's OAuth token from macOS Keychain.

Priority order:
1. macOS Keychain (Claude Code credentials) — zero config!
2. FORGE_API_KEY env var
3. ANTHROPIC_API_KEY env var
"""

from __future__ import annotations

import json
import logging
import os
import platform
import subprocess
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

KEYCHAIN_SERVICE = "Claude Code-credentials"
TOKEN_EXPIRY_BUFFER_SECS = 300  # refresh 5 min before expiry


@dataclass
class ForgeAuth:
    """Authenticate using Claude Code's OAuth token or env vars."""

    access_token: str
    refresh_token: str | None = None
    expires_at: int | None = None  # epoch ms
    source: str = "unknown"  # "keychain", "env:FORGE_API_KEY", "env:ANTHROPIC_API_KEY"
    plan: str | None = None

    @classmethod
    def load(cls) -> ForgeAuth:
        """Load credentials. Tries Keychain first, then env vars."""
        # 1. Try macOS Keychain
        if platform.system() == "Darwin":
            auth = cls._from_keychain()
            if auth is not None:
                return auth

        # 2. Try FORGE_API_KEY
        key = os.environ.get("FORGE_API_KEY")
        if key:
            return cls(access_token=key, source="env:FORGE_API_KEY")

        # 3. Try ANTHROPIC_API_KEY
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key:
            return cls(access_token=key, source="env:ANTHROPIC_API_KEY")

        raise RuntimeError(
            "No API key found. Install Claude Code (Keychain auto-detected) "
            "or set FORGE_API_KEY / ANTHROPIC_API_KEY."
        )

    @classmethod
    def _from_keychain(cls) -> ForgeAuth | None:
        """Read Claude Code OAuth credentials from macOS Keychain."""
        try:
            username = os.environ.get("USER") or subprocess.check_output(
                ["whoami"], text=True
            ).strip()

            result = subprocess.run(
                [
                    "security",
                    "find-generic-password",
                    "-s", KEYCHAIN_SERVICE,
                    "-a", username,
                    "-w",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode != 0:
                logger.debug("No Claude Code credentials in Keychain")
                return None

            data = json.loads(result.stdout.strip())
            oauth = data.get("claudeAiOauth", {})
            access_token = oauth.get("accessToken")
            if not access_token:
                logger.debug("Keychain entry found but no accessToken")
                return None

            return cls(
                access_token=access_token,
                refresh_token=oauth.get("refreshToken"),
                expires_at=oauth.get("expiresAt"),
                source="keychain",
                plan=oauth.get("subscriptionType"),
            )

        except (subprocess.SubprocessError, json.JSONDecodeError, OSError) as exc:
            logger.debug("Keychain read failed: %s", exc)
            return None

    def is_expired(self) -> bool:
        """Check if the token is expired or about to expire."""
        if self.expires_at is None:
            return False
        now_ms = int(time.time() * 1000)
        return now_ms >= (self.expires_at - TOKEN_EXPIRY_BUFFER_SECS * 1000)

    def refresh(self) -> bool:
        """Attempt to refresh the OAuth token. Returns True on success."""
        if not self.refresh_token:
            logger.warning("No refresh token available")
            return False

        try:
            import urllib.request
            import urllib.parse

            data = urllib.parse.urlencode({
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": "claude-code",
            }).encode()

            req = urllib.request.Request(
                "https://console.anthropic.com/v1/oauth/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read())

            new_token = result.get("access_token")
            if new_token:
                self.access_token = new_token
                # Update expiry if provided
                expires_in = result.get("expires_in")
                if expires_in:
                    self.expires_at = int(time.time() * 1000) + expires_in * 1000
                if result.get("refresh_token"):
                    self.refresh_token = result["refresh_token"]
                logger.info("Token refreshed successfully")
                return True

        except Exception as exc:
            logger.warning("Token refresh failed: %s", exc)

        return False

    def get_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        if self.is_expired() and self.refresh_token:
            self.refresh()
        return self.access_token

    def masked_token(self) -> str:
        """Return a masked version of the token for display."""
        t = self.access_token
        if len(t) > 12:
            return f"{t[:8]}...{t[-4:]}"
        return "****"

    def status_dict(self) -> dict:
        """Return a dict suitable for CLI status display."""
        expires_str = "n/a"
        if self.expires_at:
            remaining = (self.expires_at / 1000) - time.time()
            if remaining > 0:
                hours = int(remaining // 3600)
                mins = int((remaining % 3600) // 60)
                expires_str = f"{hours}h {mins}m remaining"
            else:
                expires_str = "EXPIRED"

        return {
            "source": self.source,
            "token": self.masked_token(),
            "expires": expires_str,
            "plan": self.plan or "unknown",
            "has_refresh": self.refresh_token is not None,
        }
