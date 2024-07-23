import io
import os
import json
import mimetypes
import argparse
import pyrogram as pg

from PIL import Image

from api_helpers import find_installed_stickerset, download_file
from tg_utils import create_sticker_to_emojis_map, StickerDownloadInfo, StickerInfoJSONEncoder


# TODO: convert to any possible format when downloading
# TODO: option to create archive?
# TODO: respect stickerset thumbnail
async def download_stickerset(app: pg.Client, args: argparse.Namespace):
    async with app:
        stickerset = await find_installed_stickerset(app, args.id, args.short_name, args.title)

        sticker2emoji_map = create_sticker_to_emojis_map(stickerset.packs)

        stickers = [
            StickerDownloadInfo(
                id=document.id,
                access_hash=document.access_hash,
                file_reference=document.file_reference,
                file_size=document.size,
                mime_type=document.mime_type,
                first_emoji=document.attributes[1].alt,
                all_emojis=sticker2emoji_map[document.id]
            )
            for document in stickerset.documents
        ]

        stickerset_dir = args.out_dir if "out_dir" in vars(args).keys() else os.path.abspath("stickerset_" + str(stickerset.set.id))
        try:
            os.makedirs(stickerset_dir)
        except FileExistsError:
            print(f"Directory `{stickerset_dir}` already exists! Aborting...")
            exit(1)

        file_blobs = {}
        for sticker in stickers:
            blob = await download_file(app, sticker.id, sticker.file_reference,
                                       sticker.access_hash, sticker.file_size)
            file_blobs[sticker.id] = blob
            print(f"\tDownloaded: id={sticker.id}, size={sticker.file_size}, mime_type={sticker.mime_type}")

        for sticker in stickers:
            result_blob = file_blobs[sticker.id]
            if args.format == "png":
                blob_io = io.BytesIO(file_blobs[sticker.id])
                image = Image.open(blob_io)
                result_io = io.BytesIO()
                image.save(result_io, format="PNG")
                result_blob = result_io.getvalue()
                sticker.mime_type = "image/png"  # change target mime type to reflect image conversion
                print(f"Converted to png: id={sticker.id}, size={len(result_blob)}")

            with open(os.path.join(stickerset_dir, str(sticker.id) + mimetypes.guess_extension(sticker.mime_type)),
                      "wb") as sticker_file:
                sticker_file.write(result_blob)

        with open(os.path.join(stickerset_dir, "stickerset_meta.json"),
                  "w", encoding="utf-8") as metainfo_file:
            print("Writing metainfo file...")
            json.dump(stickers, metainfo_file, cls=StickerInfoJSONEncoder)

        print("Done")
        exit(0)
