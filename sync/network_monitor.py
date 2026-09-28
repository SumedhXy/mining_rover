from __future__ import annotations

import logging
import socket
import urllib.error
import urllib.request
from typing import Callable, List, Optional

logger = logging.getLogger("sync.network_monitor")


class NetworkMonitor:
    """
    Determines whether the remote synchronization endpoint or network is reachable.
    Designed with an offline-first architecture: non-blocking probes, quick timeouts,
    and mockable override hooks for controlled testing.
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        check_timeout: float = 2.0,
        probe_host: str = "8.8.8.8",
        probe_port: int = 53,
    ):
        self.endpoint_url = endpoint_url
        self.check_timeout = check_timeout
        self.probe_host = probe_host
        self.probe_port = probe_port

        self._override_status: Optional[bool] = None
        self._last_status: bool = False
        self._listeners: List[Callable[[bool], None]] = []

    def set_override(self, status: Optional[bool]) -> None:
        """Explicitly override network status (useful for simulated disconnection tests)."""
        prev = self._last_status
        self._override_status = status
        current = self.is_online()
        if prev != current:
            self._notify_listeners(current)

    def add_listener(self, listener: Callable[[bool], None]) -> None:
        """Register callback for online/offline state transitions."""
        if listener not in self._listeners:
            self._listeners.append(listener)

    def _notify_listeners(self, is_online: bool) -> None:
        for callback in self._listeners:
            try:
                callback(is_online)
            except Exception as e:
                logger.warning(f"Error in network monitor listener: {e}")

    def is_online(self) -> bool:
        """Return cached or active reachability state."""
        if self._override_status is not None:
            return self._override_status

        status = self.check_reachability()
        if status != self._last_status:
            logger.info(f"Network state changed: {'ONLINE' if status else 'OFFLINE'}")
            self._last_status = status
            self._notify_listeners(status)

        return status

    def check_reachability(self) -> bool:
        """Actively probe reachability with strict timeout."""
        if self._override_status is not None:
            return self._override_status

        # 1. If an HTTP endpoint is defined, probe it first
        if self.endpoint_url:
            try:
                req = urllib.request.Request(
                    self.endpoint_url,
                    headers={"User-Agent": "MiningRover-SyncMonitor/1.0"},
                    method="HEAD",
                )
                with urllib.request.urlopen(req, timeout=self.check_timeout) as resp:
                    return resp.status < 500
            except urllib.error.HTTPError as e:
                # Even 4xx responses mean the remote server is reached and network is alive
                return e.code < 500
            except Exception:
                pass

        # 2. Fast socket probe fallback
        try:
            sock = socket.create_connection(
                (self.probe_host, self.probe_port),
                timeout=self.check_timeout,
            )
            sock.close()
            return True
        except Exception:
            return False


__all__ = ["NetworkMonitor"]
