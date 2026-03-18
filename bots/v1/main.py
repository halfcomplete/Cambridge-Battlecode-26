"""Our version 1 bot.

Each unit gets its own Player instance; the engine calls run() once per round.
Use Controller.get_entity_type() to branch on what kind of unit it is.
Five types of units: Core, Builder bot, Gunner, Sentinel, Breach, Launcher

This bot:
  - Core: spawns up to 3 builder bots on random adjacent tiles
  - Builder bot: builds a harvester on any adjacent ore tile, then moves in a
    random direction (laying a road first so the tile is passable), and places
    a marker recording the current round number
"""

import random
import math

import core, builder_bot, gunner, sentinel, breach, launcher

# Ignore the import error for cambc since it's only available in the battlecode environment
from cambc import Controller, Direction, EntityType, Environment, Position # type: ignore

# Do not edit the name of this class or the name of the run() function. This is the entry point for our bot.
class Player:
    def run(self, ct: Controller) -> None:
        self.delegate_behaviour(ct)
    
    # based on the entity type, delegate to the appropriate behaviour function
    def delegate_behaviour(self, ct: Controller) -> None:
        etype = ct.get_entity_type()
        if etype == EntityType.CORE:
            core.execute_behaviour(ct)
        elif etype == EntityType.BUILDER_BOT:
            builder_bot.execute_behaviour(ct)
        elif etype == EntityType.GUNNER:
            gunner.execute_behaviour(ct)
        elif etype == EntityType.SENTINEL:
            sentinel.execute_behaviour(ct)
        elif etype == EntityType.BREACH:
            breach.execute_behaviour(ct)
        elif etype == EntityType.LAUNCHER:
            launcher.execute_behaviour(ct)
        else:
            """
            We should never reach this case, but it's good practice to handle it anyway, just so we don't error out.

            Note:
                Erroring out in a game means the bot that errored out will destroy itself.
                If our actual program errors out (not just a single bot), we will lose the match.
                This means erroring out is really bad, and we should do everything we can to avoid it, even if it means doing nothing for a turn.
            
                CATCH ALL ERRORS!
            """
            print(f"Unknown entity type: {etype}")
            pass
    
    

    