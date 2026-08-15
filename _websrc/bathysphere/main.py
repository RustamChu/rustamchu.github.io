import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import game_main


async def _run():
    game = game_main.Game()
    while getattr(game, "running", True):
        game.step()
        await asyncio.sleep(0)


asyncio.run(_run())
