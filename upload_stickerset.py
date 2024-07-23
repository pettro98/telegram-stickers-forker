import os
import json
import mimetypes
import argparse
import pyrogram as pg

from api_helpers import upload_file, create_stickerset, get_suggested_stickerset_short_name, \
    check_stickerset_short_name
from tg_utils import StickerUploadInfo


# TODO: resize images if needed (ask?)
# TODO: convert images from any supported by PIL format to webp by default
# TODO: respect multiple extensions corresponding to single MIME
async def upload_stickerset(app: pg.Client, args: argparse.Namespace):
    if not os.path.isdir(args.dir):
        print(f"Directory `{args.dir}` doesn't exist. Aborting.")
        exit(1)

    metainfo_path = os.path.join(args.dir, "stickerset_meta.json")
    if not os.path.isfile(metainfo_path):
        print(f"Cannot find metainfo file `{metainfo_path}`. Aborting.")

    stickers: list[StickerUploadInfo]
    with open(metainfo_path, "r", encoding="utf-8") as metainfo_file:
        def sticker_info_hook(obj):
            return StickerUploadInfo(**obj, file_reference=bytes(obj["file_reference"]))

        stickers = json.load(metainfo_file, object_hook=sticker_info_hook)

    all_stickers_found = True
    for sticker in stickers:  # check if all files present before uploading
        sticker.file_path = os.path.join(args.dir, str(sticker.id)) + mimetypes.guess_extension(sticker.mime_type)
        if not os.path.isfile(sticker.file_path):
            print(f"Cannot find sticker image `{sticker.file_path}`")
            all_stickers_found = False

    if not all_stickers_found:
        print("Detected missing files. Aborting.")
        exit(1)

    # TODO: check if shortname already in use and suggest another name if it is (ask user?)
    stickerset_short_name: str
    if "shortname" in vars(args).keys():
        stickerset_short_name = await get_suggested_stickerset_short_name(app, args.title)
    elif await check_stickerset_short_name(app, args.short_name):
        stickerset_short_name = args.short_name
    else:
        suggested_short_name = await get_suggested_stickerset_short_name(app, args.title)
        reply = input(f"Short name `{args.short_name}` is already in use."""
                      f"Telegram suggests using `{suggested_short_name}`."
                      "Accept suggestion? (y/N) ").lower()
        if not "yes".startswith(reply):
            print("Short name suggestion rejected. Aborting.")
            exit(0)  # zero exit status because it is not an error - it is user's choice
        else:
            stickerset_short_name = suggested_short_name

    # TODO: make loaded metainfo data immutable
    for sticker in stickers:  # upload sticker files and reflect new sticker data in objects
        with open(sticker.file_path, "rb") as sticker_image:
            document = await upload_file(app, sticker_image.read(), sticker.mime_type)
            sticker.id = document.id
            sticker.access_hash = document.access_hash
            sticker.file_reference = document.file_reference

    stickerset_desc = await create_stickerset(app, stickers, args.title, stickerset_short_name)
    print("Stickerset successfully created!")
    print(f"Stickerset URL: https://t.me/addstickers/{stickerset_short_name}")
