import json
import os
import sys
import asyncio as aio
from functools import reduce
from random import randint
from typing import cast
import pyrogram
from pyrogram import Client
from pyrogram.handlers import MessageHandler
from pyrogram.types import Message
from pyrogram.raw.functions.messages import GetAllStickers, GetStickerSet, UploadMedia, InstallStickerSet
from pyrogram.raw.types.messages import StickerSet, AllStickers, StickerSetInstallResultSuccess
from pyrogram.raw.types import StickerPack, StickerSet as StickerSetDesc, InputStickerSetID, InputDocument, \
    InputUserSelf, InputStickerSetItem, InputPeerSelf, InputFile, InputMediaUploadedDocument, MessageMediaDocument, \
    DocumentAttributeImageSize
from pyrogram.raw.functions.upload import GetFile, SaveFilePart
from pyrogram.raw.types.upload import File
from pyrogram.raw.functions.stickers import CreateStickerSet

with open(".env", "r", encoding="utf-8") as env:
    api_id = int(env.readline()[len("api_id="):])
    api_hash = env.readline()[len("api_hash="):]

darushka_id = "998192468795064322"
darushka_accesshash = "-2661041318036046588"

darushka_title = "@darushka_the_best"


def m_hash():
    return randint(1, 0xff_ff_ff_ff)


async def get_sticker_set(app: Client, title: str) -> StickerSet:
    all_sets = cast(AllStickers, await app.invoke(GetAllStickers(hash=m_hash())))
    sticker_set_desc = next(filter(lambda x: x.title == title, all_sets.sets))
    return await app.invoke(
        GetStickerSet(stickerset=InputStickerSetID(id=sticker_set_desc.id, access_hash=sticker_set_desc.access_hash),
                      hash=m_hash())
    )


def invert_emoji_sticker_map(emoji_map: list[StickerPack]) -> dict[int, list[str]]:
    sticker2emoji_map = {}
    for emoji_mapping in emoji_map:
        for sticker_id in emoji_mapping.documents:
            sticker2emoji_map.setdefault(sticker_id, []).append(emoji_mapping.emoticon)
    return sticker2emoji_map


async def download_multichunk_file(app: Client, file_id: int, file_reference: bytes, file_access_hash: int,
                                   file_size: int) -> bytes:
    offset = 0
    blob = bytes()
    while offset < file_size:
        limit = min(1024 * 1024, file_size - offset)
        file: File = await app.invoke(GetFile(
            location=InputDocumentFileLocation(id=file_id, access_hash=file_access_hash, file_reference=file_reference,
                                               thumb_size=""), offset=offset, limit=limit))
        blob += bytes
        offset += limit
    return blob


async def main():
    app = Client("my_account", 25560466, "9018c45fda174c5c9ecf61ecb23d065e", workdir=os.curdir,
                 max_concurrent_transmissions=10)
    if False and sys.argv[1] == "download":
        async with app:
            orig_set = await get_sticker_set(app, darushka_title)

            sticker2emoji_map = invert_emoji_sticker_map(orig_set.packs)

            stickers = [
                dict(
                    id=sticker.id,
                    access_hash=sticker.access_hash,
                    file_reference=sticker.file_reference,
                    file_size=sticker.size,
                    mime_type=sticker.mime_type,
                    first_emoji=sticker.attributes[1].alt,
                    all_emojis=sticker2emoji_map[sticker.id]
                )
                for sticker in orig_set.documents
            ]

            file_blobs = {}
            for sticker in stickers:
                blob = await download_multichunk_file(app, sticker["id"], sticker["file_reference"],
                                                      sticker["access_hash"], sticker["file_size"])
                file_blobs[sticker["id"]] = blob

            os.mkdir(os.path.join(os.curdir, darushka_id))
            for sticker in stickers:
                with open(os.path.join(os.curdir, darushka_id, str(sticker["id"]) + ".webp"),
                          "wb") as sticker_file:  # TODO guess extension from mime
                    sticker_file.write(sticker["file_blob"])

            with open(os.path.join(os.curdir, darushka_id, "stickerset_meta.json"),
                      "w") as metainfo_file:  # TODO guess extension from mime
                json.dump(stickers, metainfo_file)

    elif True or sys.argv[1] == "upload":
        # stickers_dir = os.path.abspath(sys.argv[2])
        # print("Stickers will be uploaded using information from" + stickers_dir)
        answer = input("Continue? [y/N]")
        if answer.lower() != "y":
            print("Aborting...")
            exit(0)

        async with app:
            file_id = m_hash()
            with open("0.png", "rb") as pic:
                index = 0
                while True:
                    chunk = pic.read(512 * 1024)
                    if not await app.invoke(SaveFilePart(file_id=file_id, file_part=index, bytes=chunk)):
                        raise RuntimeError("could not upload file")
                    index += 1
                    if len(chunk) < 512 * 1024:
                        document = cast(MessageMediaDocument, await app.invoke(UploadMedia(
                            peer=InputPeerSelf(),
                            media=InputMediaUploadedDocument(
                                file=InputFile(id=file_id, parts=index, name="0.png", md5_checksum=""),
                                mime_type="img/png",
                                attributes=[DocumentAttributeImageSize(w=512, h=512)],
                                force_file=True
                                )
                        ))).document
                        break

            sticker_set = cast(StickerSet, await app.invoke(
                CreateStickerSet(
                    user_id=InputUserSelf(),
                    title="myTestStickerSet",
                    short_name="myteststickersetpettro98",
                    stickers=[InputStickerSetItem(
                        document=InputDocument(id=document.id, access_hash=document.access_hash, file_reference=document.file_reference),
                        emoji="❤"
                    )],
                )
            )).set
            await app.invoke(InstallStickerSet(
                stickerset=InputStickerSetID(id=sticker_set.id, access_hash=sticker_set.hash),
                archived=False
            ))


aio.run(main())
