"""This library wraps the forked-daapd API for use with Home Assistant."""
from __future__ import annotations

__version__ = "0.1.14"
import asyncio
import concurrent
import logging
from collections.abc import Callable, Coroutine, Mapping, Sequence
from http import HTTPStatus
from typing import Any, cast
from urllib.parse import urljoin

import aiohttp

_LOGGER = logging.getLogger(__name__)


class ForkedDaapdAPI:
    """Class for interfacing with forked-daapd API."""

    def __init__(
        self,
        websession: aiohttp.ClientSession,
        ip_address: str,
        api_port: int,
        api_password: str,
    ) -> None:
        """Initialize the ForkedDaapdAPI object."""
        self._ip_address = ip_address
        self._api_port = api_port
        self._websession = websession
        self._auth = (
            aiohttp.BasicAuth(login="admin", password=api_password)
            if api_password
            else None
        )
        self._api_password = api_password

    @staticmethod
    async def test_connection(
        websession: aiohttp.ClientSession, host: str, port: int, password: str
    ) -> list[str]:
        """Validate the user input."""

        try:
            url = f"http://{host}:{port}/api/config"
            auth = (
                aiohttp.BasicAuth(login="admin", password=password)
                if password
                else None
            )
            _LOGGER.debug("Trying to connect to %s with auth %s", url, auth)
            async with websession.get(
                url=url, auth=auth, timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                json = await resp.json()
                _LOGGER.debug("JSON %s", json)
                if json["websocket_port"] == 0:
                    return ["websocket_not_enabled"]
                return ["ok", json["library_name"]]
        except (
            aiohttp.ClientConnectionError,
            asyncio.TimeoutError,
            # pylint: disable=protected-access
            concurrent.futures._base.TimeoutError,
            # maybe related to https://github.com/aio-libs/aiohttp/issues/1207
            aiohttp.InvalidURL,
        ):
            return ["wrong_host_or_port"]
        except (aiohttp.ClientResponseError, KeyError):
            if resp.status == 401:
                return ["wrong_password"]
            if resp.status == 403:
                return ["forbidden"]
            return ["wrong_server_type"]

    async def get_request(
        self, endpoint: str, params: Mapping[str, Any] | None = None
    ) -> dict[str, Any] | None:
        """Get request from endpoint."""
        url = f"http://{self._ip_address}:{self._api_port}/api/{endpoint}"
        # get params not working so add params ourselves
        if params:
            url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
        try:
            async with self._websession.get(url=url, auth=self._auth) as resp:
                json = await resp.json()
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Can not get %s with params %s", url, params)
            return None
        return cast(dict[str, Any], json) if json else None

    async def put_request(
        self,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> int:
        """Put request to endpoint."""
        url = f"http://{self._ip_address}:{self._api_port}/api/{endpoint}"
        _LOGGER.debug(
            "PUT request to %s with params %s, json payload %s.", url, params, json
        )
        if params:  # convert bool to text
            params = {
                key: str(value).lower() if isinstance(value, bool) else value
                for key, value in params.items()
            }
        response = await self._websession.put(
            url=url, params=params, json=json, auth=self._auth
        )
        return response.status

    async def post_request(
        self,
        endpoint: str,
        params: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
    ) -> int:
        """Post request to endpoint."""
        url = f"http://{self._ip_address}:{self._api_port}/api/{endpoint}"
        _LOGGER.debug(
            "POST request to %s with params %s, data payload %s.", url, params, json
        )
        if params:  # convert bool to text
            params = {
                key: str(value).lower() if isinstance(value, bool) else value
                for key, value in params.items()
            }
        response = await self._websession.post(
            url=url, params=params, json=json, auth=self._auth
        )
        return response.status

    async def start_websocket_handler(
        self,
        ws_port: int,
        event_types: Sequence[str],
        update_callback: Callable[[Sequence[str]], Coroutine[Any, Any, None]],
        websocket_reconnect_time: int,
        disconnected_callback: Callable[[], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        """Websocket handler daemon."""
        _LOGGER.debug("Starting websocket handler")
        if ws_port == 0:
            _LOGGER.error(
                "This library requires a forked-daapd instance with websocket enabled."
            )
            raise Exception("forked-daapd websocket not enabled.")
        url = f"http://{self._ip_address}:{ws_port}/"
        while True:
            try:
                async with self._websession.ws_connect(
                    url, protocols=("notify",), heartbeat=websocket_reconnect_time
                ) as websocket:
                    await update_callback(
                        event_types
                    )  # send all requested updates once
                    await websocket.send_json(data={"notify": event_types})
                    _LOGGER.debug("Sent notify to %s", url)
                    async for msg in websocket:
                        updates = msg.json()["notify"]
                        _LOGGER.debug("Message JSON: %s", msg.json())
                        await update_callback(updates)
                        _LOGGER.debug("Done with callbacks %s", updates)
            except (asyncio.TimeoutError, aiohttp.ClientError) as exception:
                _LOGGER.warning(
                    "Can not connect to WebSocket at %s, will retry in %s seconds.",
                    url,
                    websocket_reconnect_time,
                )
                _LOGGER.warning("Error %s", repr(exception))
                if disconnected_callback:
                    await disconnected_callback()
                await asyncio.sleep(websocket_reconnect_time)
                continue

    async def start_playback(self) -> int:
        """Start playback."""
        status = await self.put_request(endpoint="player/play")
        if status != 204:
            _LOGGER.debug("Unable to start playback.")
        return status

    async def pause_playback(self) -> int:
        """Pause playback."""
        status = await self.put_request(endpoint="player/pause")
        if status != 204:
            _LOGGER.debug("Unable to pause playback.")
        return status

    async def stop_playback(self) -> int:
        """Stop playback."""
        status = await self.put_request(endpoint="player/stop")
        if status != 204:
            _LOGGER.debug("Unable to stop playback.")
        return status

    async def previous_track(self) -> int:
        """Previous track."""
        status = await self.put_request(endpoint="player/previous")
        if status != 204:
            _LOGGER.debug("Unable to skip to previous track.")
        return status

    async def next_track(self) -> int:
        """Next track."""
        status = await self.put_request(endpoint="player/next")
        if status != 204:
            _LOGGER.debug("Unable to skip to next track.")
        return status

    async def seek(
        self, position_ms: int | None = None, seek_ms: int | None = None
    ) -> int:
        """Seek."""
        if position_ms:
            params = {"position_ms": position_ms}
        elif seek_ms:
            params = {"seek_ms": seek_ms}
        else:
            _LOGGER.error("seek needs either position_ms or seek_ms")
            return -1
        status = await self.put_request(endpoint="player/seek", params=params)
        if status != 204:
            _LOGGER.debug(
                "Unable to seek to %s of %s.",
                next(iter(params.keys())),
                next(iter(params.values())),
            )
        return status

    async def shuffle(self, shuffle: bool) -> int:
        """Shuffle."""
        status = await self.put_request(
            endpoint="player/shuffle",
            params={"state": shuffle},
        )
        if status != 204:
            _LOGGER.debug("Unable to set shuffle to %s.", shuffle)
        return status

    async def set_enabled_outputs(self, output_ids: Sequence[str]) -> int:
        """Set enabled outputs."""
        status = await self.put_request(
            endpoint="outputs/set", json={"outputs": output_ids}
        )
        if status != 204:
            _LOGGER.debug("Unable to set enabled outputs for %s.", output_ids)
        return status

    async def set_volume(
        self,
        volume: int | None = None,
        step: int | None = None,
        output_id: str | None = None,
    ) -> int:
        """Set volume."""
        params: dict[str, int | str]
        if volume:
            params = {"volume": volume}
        elif step:
            params = {"step": step}
        else:
            _LOGGER.error("set_volume needs either volume or step")
            return HTTPStatus.BAD_REQUEST
        if output_id:
            params["output_id"] = output_id
        status = await self.put_request(endpoint="player/volume", params=params)
        if status != 204:
            _LOGGER.debug("Unable to set volume.")
        return status

    async def get_track_info(self, track_id: int) -> dict | None:
        """Get track info."""
        return await self.get_request(endpoint=f"library/tracks/{track_id}")

    async def change_output(
        self, output_id: str, selected: bool | None = None, volume: int | None = None
    ) -> int:
        """Change output."""
        json: dict[str, int | str] = {} if selected is None else {"selected": selected}
        if volume is not None:
            json["volume"] = volume
        status = await self.put_request(endpoint=f"outputs/{output_id}", json=json)
        if status != 204:
            _LOGGER.debug(
                "%s: Unable to change output %s to %s.", status, output_id, json
            )
        return status

    async def add_to_queue(
        self,
        uris: str | None = None,
        expression: str | None = None,
        playback: str | None = None,
        playback_from_position: int | None = None,
        clear: bool = False,
        shuffle: bool = False,
        position: int | None = None,
    ) -> int:
        """Add item to queue."""
        if not (uris or expression):
            _LOGGER.error("Either uris or expression must be set.")
            return HTTPStatus.BAD_REQUEST
        params: dict[str, int | str] = {}
        if uris:
            params["uris"] = uris
        else:
            assert expression
            params["expression"] = expression
        locals_dict = locals()
        params.update(
            {
                k: v
                for k, v in {
                    field: locals_dict[field]
                    for field in [
                        "playback",
                        "playback_from_position",
                        "clear",
                        "shuffle",
                        "position",
                    ]
                }.items()
                if v is not None
            }
        )
        status = await self.post_request(endpoint="queue/items/add", params=params)
        if status != 200:
            _LOGGER.debug("%s: Unable to add items to queue.", status)
        return status

    async def clear_queue(self) -> int:
        """Clear queue."""
        status = await self.put_request(endpoint="queue/clear")
        if status != 204:
            _LOGGER.debug("%s: Unable to clear queue.", status)
        return status

    def full_url(self, url: str) -> str:
        """Get full url (including basic auth) of urls such as artwork_url."""
        creds = f"admin:{self._api_password}@" if self._api_password else ""
        return urljoin(f"http://{creds}{self._ip_address}:{self._api_port}", url)

    async def get_pipes(self) -> list[dict[str, int | str]] | None:
        """Get list of pipes."""
        if not (
            pipes := await self.get_request(
                "search",
                params={"type": "tracks", "expression": "data_kind+is+pipe"},
            )
        ):
            return None
        return cast(list[dict[str, int | str]], pipes["tracks"]["items"])

    async def get_playlists(self) -> list[dict[str, int | str]] | None:
        """Get list of playlists."""
        playlists = await self.get_request("library/playlists")
        return playlists.get("items") if playlists else None

    async def get_artists(self) -> list[dict[str, int | str]] | None:
        """Get a list of artists."""
        artists = await self.get_request("library/artists")
        return artists.get("items") if artists else None

    async def get_albums(
        self, artist_id: str | None = None
    ) -> list[dict[str, int | str]] | None:
        """Get a list of albums."""
        if artist_id:
            albums = await self.get_request(f"library/artists/{artist_id}/albums")
        else:
            albums = await self.get_request("library/albums")
        return albums.get("items") if albums else None

    async def get_genres(self) -> list[dict[str, int | str]] | None:
        """Get a list of genres in library."""
        genres = await self.get_request("library/genres")
        return genres.get("items") if genres else None

    async def get_genre(
        self, genre: str, media_type: str
    ) -> list[dict[str, int | str]] | None:
        """Get artists, albums, or tracks in a given genre."""
        params = {
            "expression": f'genre+is+"{genre}"',
            "type": media_type,
        }
        result = await self.get_request("search", params=params)
        return (
            [
                item
                for sublist in [
                    items_by_type["items"] for items_by_type in result.values()
                ]
                for item in sublist
            ]
            if result
            else None
        )

    async def get_directory(
        self, directory: str | None = None
    ) -> dict[str, Any] | None:
        """Get directory contents."""
        return await self.get_request(
            "library/files", params={"directory": directory} if directory else None
        )

    async def get_tracks(
        self, album_id: str | None = None, playlist_id: str | None = None
    ) -> list[dict[str, int | str]] | None:
        """Get a list of tracks from an album or playlist or by genre."""
        item_id = album_id or playlist_id
        if item_id is None:
            return []
        tracks = await self.get_request(
            f"library/{'albums' if album_id else 'playlists'}/{item_id}/tracks",
        )
        return tracks.get("items") if tracks else None

    async def get_track(self, track_id: int) -> dict[str, int | str] | None:
        """Get track."""
        track = await self.get_request(f"library/tracks/{track_id}")
        return track if track else None

    # not used by HA

    async def consume(self, consume: bool) -> int:
        """Consume."""
        status = await self.put_request(
            endpoint="player/consume",
            params={"state": consume},
        )
        if status != 204:
            _LOGGER.debug("Unable to set consume to %s.", consume)
        return status

    async def repeat(self, repeat: str) -> int:
        """Repeat. Takes string argument of 'off','all', or 'single'."""
        status = await self.put_request(
            endpoint="player/repeat", params={"state": repeat}
        )
        if status != 204:
            _LOGGER.debug("Unable to set repeat to %s.", repeat)
        return status

    async def toggle_playback(self) -> int:
        """Toggle playback."""
        status = await self.put_request(endpoint="player/toggle")
        if status != 204:
            _LOGGER.debug("Unable to toggle playback.")
        return status

    async def get_current_queue_item(self) -> dict[str, int | str] | None:
        """Get the current queue item."""
        if not (
            queue := await self.get_request(
                endpoint="queue", params={"id": "now_playing"}
            )
        ):
            return None
        queue = cast(dict[str, Sequence], queue)
        return queue["items"][0] if queue["items"] else None
