import argparse
import pyrogram as pg

from api_helpers import find_installed_stickerset


async def print_stickerset_info(app: pg.Client, args: argparse.Namespace):
    async with app:
        try:
            stickerset = await find_installed_stickerset(app, args.id, args.short_name, args.title)
            print(f"Stickerset id: {stickerset.set.id}")
            print(f"Stickerset title: {stickerset.set.title}")
            print(f"Stickerset short name: {stickerset.set.short_name}")
        except RuntimeError as e:  # could not find stickerset
            print(e)
            exit(1)
