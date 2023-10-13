"""This library wraps the librespot-java API for use with Home Assistant."""
from __future__ import annotations

__version__ = "0.1.1"
import asyncio
import logging
from typing import Any, Callable, Coroutine, Mapping

import aiohttp

_LOGGER = logging.getLogger(__name__)


def _debug_string(string_base: str, status: int) -> str:
    """Helper for logger debug strings."""
    if status == 204:
        return string_base + " No active session"
    if status == 500:
        return string_base + " Invalid session"
    if status == 503:
        return string_base + " Session is reconnecting"
    return ""


class LibrespotJavaAPI:
    """Class for interfacing with librespot-java API."""

    def __init__(
        self, websession: aiohttp.ClientSession, ip_address: str, api_port: int
    ):
        self._ip_address = ip_address
        self._api_port = api_port
        self._websession = websession

    async def post_request(
        self, endpoint: str, data: Mapping[str, Any] | None = None
    ) -> aiohttp.ClientResponse:
        """Helper function to put to endpoint."""
        url = f"http://{self._ip_address}:{self._api_port}/{endpoint}"
        _LOGGER.debug("POST request to %s with payload %s.", url, data)
        response = await self._websession.post(url=url, data=data)
        return response

    async def start_websocket_handler(
        self,
        update_callback: Callable[[Mapping[str, Any]], Coroutine[Any, Any, None]],
        websocket_reconnect_time: float,
    ) -> None:
        """Websocket handler daemon."""
        _LOGGER.debug("Starting websocket handler")
        url = f"http://{self._ip_address}:{self._api_port}/events"
        while True:
            try:
                async with self._websession.ws_connect(url) as ws:
                    async for msg in ws:
                        json = msg.json()
                        _LOGGER.debug("Message received: %s", json)
                        await update_callback(json)
                _LOGGER.debug(
                    "WebSocket disconnected, will retry in %s seconds.",
                    websocket_reconnect_time,
                )
                await asyncio.sleep(websocket_reconnect_time)
            except (asyncio.TimeoutError, aiohttp.ClientError):
                _LOGGER.error(
                    "Can not connect to WebSocket at %s, will retry in %s seconds.",
                    url,
                    websocket_reconnect_time,
                )
                await asyncio.sleep(websocket_reconnect_time)
                continue

    async def player_load(self, uri: str, play: bool) -> int:
        """Load track from URI."""
        resp = await self.post_request(
            endpoint="player/load", data={"uri": uri, "play": play}
        )
        if resp.status in [204, 500, 503]:
            _LOGGER.debug(_debug_string("Unable to load track.", resp.status))
        return resp.status

    async def player_pause(self) -> int:
        """Pause playback."""
        resp = await self.post_request(endpoint="player/pause")
        if resp.status in [204, 500, 503]:
            _LOGGER.debug(_debug_string("Unable to pause player.", resp.status))
        return resp.status

    async def player_resume(self) -> int:
        """Resume playback."""
        resp = await self.post_request(endpoint="player/resume")
        if resp.status in [204, 500, 503]:
            _LOGGER.debug(_debug_string("Unable to resume player.", resp.status))
        return resp.status

    async def player_next(self) -> int:
        """Skip to next track."""
        resp = await self.post_request(endpoint="player/next")
        if resp.status in [204, 500, 503]:
            _LOGGER.debug(
                _debug_string("Unable to skip to the next track.", resp.status)
            )
        return resp.status

    async def player_prev(self) -> int:
        """Skip to previous track."""
        resp = await self.post_request(endpoint="player/prev")
        if resp.status in [204, 500, 503]:
            _LOGGER.debug(
                _debug_string("Unable to skip to the previous track.", resp.status)
            )
        return resp.status

    async def player_set_volume(self, volume: int) -> int:
        """Set volume to a given volume between 0 and 65536."""
        resp = await self.post_request(
            endpoint="player/set-volume", data={"volume": volume}
        )
        if resp.status in [204, 500, 503]:
            _LOGGER.debug(_debug_string("Unable to set the volume.", resp.status))
        return resp.status

    async def player_volume_up(self) -> int:
        """Turn up the volume a little bit."""
        resp = await self.post_request(endpoint="player/volume-up")
        if resp.status in [204, 500, 503]:
            _LOGGER.debug(_debug_string("Unable to turn the volume up.", resp.status))
        return resp.status

    async def player_volume_down(self) -> int:
        """Turn down the volume a little bit."""
        resp = await self.post_request(endpoint="player/volume-down")
        if resp.status in [204, 500, 503]:
            _LOGGER.debug(_debug_string("Unable to turn the volume down.", resp.status))
        return resp.status

    async def player_current(self) -> dict:
        """Retrieve information about the current track."""
        resp = await self.post_request(endpoint="player/current")
        if resp.status in [204, 500, 503]:
            _LOGGER.debug(
                _debug_string(
                    "Unable to retrieve information about the current track.",
                    resp.status,
                )
            )
        json = await resp.json(content_type=None)
        return json

    async def metadata(self, uri: str) -> dict:
        """Retrieve metadata."""
        resp = await self.post_request(endpoint=f"metadata/{uri}")
        if resp.status in [204, 500, 503]:
            _LOGGER.debug(
                _debug_string(f"Unable to get metadata for {uri}.", resp.status)
            )
        json = await resp.json(content_type=None)
        return json

    async def search(self, query: str) -> dict:
        """Make a search."""
        resp = await self.post_request(endpoint=f"search/{query}")
        if resp.status in [204, 500, 503]:
            _LOGGER.debug(_debug_string(f"Unable to search for {query}.", resp.status))
        json = await resp.json(content_type=None)
        return json

    async def token(self, scope: str) -> dict:
        """Request an access token for a specific scope."""
        resp = await self.post_request(endpoint=f"token/{scope}")
        if resp.status in [204, 500, 503]:
            _LOGGER.debug(
                _debug_string(f"Unable to get token for {scope}.", resp.status)
            )
        json = await resp.json(content_type=None)
        return json
