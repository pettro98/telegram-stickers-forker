# Utility functions for telegram-stickers-forker
# Copyright Pettro98 (https://github.com/pettro98)

import random
import json
from dataclasses import dataclass, is_dataclass, asdict
import pyrogram.raw.types as pg_t


def randint32() -> int:
    return random.randint(0, 0x1_00_00)


def create_sticker_to_emojis_map(emoji_map: list[pg_t.StickerPack]) -> dict[int, list[str]]:
    sticker2emoji_map = {}
    for emoji_mapping in emoji_map:
        for sticker_id in emoji_mapping.documents:
            sticker2emoji_map.setdefault(sticker_id, []).append(emoji_mapping.emoticon)
    return sticker2emoji_map


@dataclass
class StickerInfo:
    id: int
    mime_type: str
    first_emoji: str
    all_emojis: list[str]


@dataclass
class StickerDownloadInfo(StickerInfo):
    access_hash: int = 0
    file_reference: bytes = b""
    file_size: int = 0


@dataclass
class StickerUploadInfo(StickerDownloadInfo):
    file_path: str = ""


def convert_to_sticker_info(obj: StickerDownloadInfo):
    return StickerInfo(
        id=obj.id,
        mime_type=obj.mime_type,
        first_emoji=obj.first_emoji,
        all_emojis=obj.all_emojis)


class StickerInfoJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, StickerDownloadInfo):
            return asdict(convert_to_sticker_info(o))
        return super().default(o)
