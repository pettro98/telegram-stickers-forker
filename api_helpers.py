# Pyrogram API wrappers for telegram-stickers-forker
# Copyright Pettro98 (https://github.com/pettro98)

from hashlib import md5
from typing import cast

import pyrogram as pg
import pyrogram.raw.types as pg_t
import pyrogram.raw.types.messages as pg_msg_t
import pyrogram.raw.functions.messages as pg_msg_f
import pyrogram.raw.types.upload as pg_up_t
import pyrogram.raw.functions.upload as pg_up_f
import pyrogram.raw.functions.stickers as pg_st_f
import pyrogram.raw.types.stickers as pg_st_t

from tg_utils import randint32, StickerUploadInfo

UPLOAD_CHUNK_SIZE = 512 * 1024
DOWNLOAD_CHUNK_SIZE = 1 * 1024 * 1024


async def find_installed_stickerset(
        app: pg.Client,
        stickerset_id: int | None = None,
        stickerset_short_name: str | None = None,
        stickerset_title: str | None = None,
) -> pg_msg_t.StickerSet:
    """Finds stickerset among all installed stickersets. One and only one of filters should be specified."""

    all_stickers: pg_msg_t.AllStickers = await app.invoke(pg_msg_f.GetAllStickers(hash=randint32()))
    all_stickerset_descs = all_stickers.sets

    selected_stickerset_desc: pg_t.StickerSet

    try:
        if stickerset_id is not None:
            selected_stickerset_desc = next(filter(lambda x: x.id == stickerset_id, all_stickerset_descs))
        elif stickerset_short_name is not None:
            selected_stickerset_desc = next(
                filter(lambda x: x.short_name == stickerset_short_name, all_stickerset_descs))
        elif stickerset_title is not None:
            selected_stickerset_desc = next(filter(lambda x: x.title == stickerset_title, all_stickerset_descs))
        else:
            raise TypeError("None of expected filters is provided")
    except StopIteration:
        raise RuntimeError("Cannot find specified stickerset")

    selected_stickerset = await app.invoke(pg_msg_f.GetStickerSet(
        stickerset=pg_t.InputStickerSetID(
            id=selected_stickerset_desc.id,
            access_hash=selected_stickerset_desc.access_hash),
        hash=randint32()))

    if not isinstance(selected_stickerset, pg_msg_t.StickerSet):
        raise RuntimeError("Received unexpected stickerset type")
    return selected_stickerset


async def download_file(
        app: pg.Client,
        file_id: int,
        file_reference: bytes,
        file_access_hash: int,
        file_size: int
) -> bytes:
    """Downloads file to bytes"""

    offset = 0
    blob = bytes()
    while offset < file_size:
        file: pg_up_t.File = await app.invoke(pg_up_f.GetFile(
            location=pg_t.InputDocumentFileLocation(
                id=file_id,
                access_hash=file_access_hash,
                file_reference=file_reference,
                thumb_size=""),
            offset=offset,
            limit=DOWNLOAD_CHUNK_SIZE))
        blob += file.bytes
        offset += DOWNLOAD_CHUNK_SIZE
    return blob


async def upload_file(app: pg.Client, contents: bytes, mime_type: str) -> pg_t.Document:
    """Uploads file from bytes. File size must not be over 10MB. Returns associated Document"""

    upload_id = randint32()
    offset = 0
    uploaded_count = 0
    while offset < len(contents):
        chunk = contents[offset:offset + UPLOAD_CHUNK_SIZE]
        if not await app.invoke(pg_up_f.SaveFilePart(file_id=upload_id, file_part=uploaded_count, bytes=chunk)):
            raise RuntimeError(f"Could not upload file chunk [{offset} - {offset + UPLOAD_CHUNK_SIZE}]")
        uploaded_count += 1
        offset += UPLOAD_CHUNK_SIZE

    uploaded_media = await app.invoke(pg_msg_f.UploadMedia(
        peer=pg_t.InputPeerSelf(),
        media=pg_t.InputMediaUploadedDocument(
            file=pg_t.InputFile(
                id=upload_id,
                parts=uploaded_count,
                name="",
                md5_checksum=md5(contents, usedforsecurity=False).hexdigest()),
            mime_type=mime_type,
            attributes=[])))

    if not isinstance(uploaded_media, pg_t.MessageMediaDocument):
        raise RuntimeError("Received unexpected MessageMedia type")
    return uploaded_media.document


async def check_stickerset_short_name(app: pg.Client, stickerset_short_name: str) -> bool:
    return await app.invoke(pg_st_f.CheckShortName(short_name=stickerset_short_name))


async def get_suggested_stickerset_short_name(app: pg.Client, stickerset_title: str) -> str:
    return cast(pg_st_t.SuggestedShortName,
                await app.invoke(pg_st_f.SuggestShortName(title=stickerset_title))).short_name


async def create_stickerset(
        app: pg.Client,
        stickers: list[StickerUploadInfo],
        stickerset_title: str,
        stickerset_short_name: str
) -> pg_msg_t.StickerSet:
    input_stickers = [
        pg_t.InputStickerSetItem(
            document=pg_t.InputDocument(
                id=sticker.id,
                access_hash=sticker.access_hash,
                file_reference=sticker.file_reference
            ),
            emoji=sticker.first_emoji + "".join(sticker.all_emojis)
        ) for sticker in stickers]

    stickerset_desc: pg_msg_t.StickerSet = await app.invoke(
        pg_st_f.CreateStickerSet(
            user_id=pg_t.InputUserSelf(),
            title=stickerset_title,
            short_name=stickerset_short_name,
            stickers=input_stickers))

    await app.invoke(pg_msg_f.InstallStickerSet(
        stickerset=pg_t.InputStickerSetID(
            id=stickerset_desc.set.id,
            access_hash=stickerset_desc.set.hash),
        archived=False))

    return stickerset_desc
