from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
import httpx
import xmltodict
from xml.etree import ElementTree
import logging

logger = logging.getLogger(__name__)

class BoseClientError(Exception):
    """Base exception for BoseClient errors"""
    pass

class KeyValue(str, Enum):
    PLAY = "PLAY"
    PAUSE = "PAUSE"
    POWER = "POWER"
    PREV_TRACK = "PREV_TRACK"
    NEXT_TRACK = "NEXT_TRACK"
    THUMBS_UP = "THUMBS_UP"
    THUMBS_DOWN = "THUMBS_DOWN"
    PRESET_1 = "PRESET_1"
    PRESET_2 = "PRESET_2"
    PRESET_3 = "PRESET_3"
    PRESET_4 = "PRESET_4"
    PRESET_5 = "PRESET_5"
    PRESET_6 = "PRESET_6"

class KeyState(str, Enum):
    PRESS = "press"
    RELEASE = "release"

@dataclass
class NowPlayingContentItem:
    source: str
    content_type: Optional[str]
    location: Optional[str]
    is_presetable: bool
    name: Optional[str]
    container_art: Optional[str]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            source=data.get('@source'),
            content_type=data.get('@type'),
            location=data.get('@location'),
            is_presetable=data.get('@isPresetable', False),
            name=data.get('itemName'),
            container_art=data.get('containerArt')
        )

@dataclass
class NowPlaying:
    device_id: str
    source: str
    source_account: Optional[str]
    content_item: NowPlayingContentItem
    track: Optional[str]
    artist: Optional[str]
    album: Optional[str]
    station_name: Optional[str]

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            device_id=data.get('@deviceID'),
            source=data.get('@source'),
            source_account=data.get('@sourceAccount'),
            content_item=NowPlayingContentItem.from_dict(data.get('ContentItem', {})),
            track=data.get('track'),
            artist=data.get('artist'),
            album=data.get('album'),
            station_name=data.get('stationName')
        )

@dataclass
class Volume:
    target: int
    actual: int

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            target=int(data.get('targetvolume', 0)),
            actual=int(data.get('actualvolume', 0))
        )

class BoseClient:
    def __init__(self, hostname: str):
        self.hostname = hostname
        self.base_url = f"http://{hostname}:8090"
        self.client = httpx.AsyncClient(timeout=10.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def _post_xml(self, endpoint: str, xml_data: str) -> None:
        url = f"{self.base_url}/{endpoint}"
        logger.debug("POST %s with body: %s", url, xml_data)
        try:
            response = await self.client.post(url, content=xml_data)
            response.raise_for_status()
            logger.debug("POST response status: %d", response.status_code)
        except httpx.HTTPError as e:
            raise BoseClientError(f"HTTP error occurred: {e}")

    async def _get_xml(self, endpoint: str) -> dict:
        url = f"{self.base_url}/{endpoint}"
        logger.debug("GET %s", url)
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            logger.debug("GET response status: %d, body: %s", response.status_code, response.text)
            return xmltodict.parse(response.text)
        except httpx.HTTPError as e:
            raise BoseClientError(f"HTTP error occurred: {e}")

    def _create_key_xml(self, key: KeyValue, state: KeyState) -> str:
        root = ElementTree.Element("key")
        root.set("state", state.value)
        root.set("sender", "Gabbo")
        root.text = key.value
        return ElementTree.tostring(root, encoding='unicode')

    async def press_and_release_key(self, key: KeyValue) -> None:
        press_xml = self._create_key_xml(key, KeyState.PRESS)
        release_xml = self._create_key_xml(key, KeyState.RELEASE)
        
        await self._post_xml("key", press_xml)
        await self._post_xml("key", release_xml)

    async def play(self) -> None:
        await self.press_and_release_key(KeyValue.PLAY)

    async def pause(self) -> None:
        await self.press_and_release_key(KeyValue.PAUSE)

    async def power(self) -> None:
        await self.press_and_release_key(KeyValue.POWER)

    async def get_status(self) -> NowPlaying:
        response = await self._get_xml("now_playing")
        return NowPlaying.from_dict(response['nowPlaying'])

    async def get_volume(self) -> Volume:
        response = await self._get_xml("volume")
        return Volume.from_dict(response['volume'])

    async def set_volume(self, value: int) -> None:
        if not 0 <= value <= 100:
            raise ValueError("Volume must be between 0 and 100")
        
        root = ElementTree.Element("volume")
        root.text = str(value)
        xml_data = ElementTree.tostring(root, encoding='unicode')
        await self._post_xml("volume", xml_data)

    async def set_preset(self, value: int) -> None:
        if not 1 <= value <= 6:
            raise BoseClientError(f"{value} is not a valid preset (1-6).")
        
        preset_key = getattr(KeyValue, f"PRESET_{value}")
        await self.press_and_release_key(preset_key) 