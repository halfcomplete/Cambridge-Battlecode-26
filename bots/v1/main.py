"""Our version 1 bot.

Each unit gets its own Player instance; the engine calls run() once per round.
Use Controller.get_entity_type() to branch on what kind of unit it is.
Six types of units: Core, Builder bot, Gunner, Sentinel, Breach, Launcher

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
    def __init__(self):
        """
        Initialises the bot with states for each entity type.
        Because we can't tell which entity type this bot is at the time of initialisation, we have to initialise all states.
        """

        self.builder_bot_state = builder_bot.BuilderBotState()
        self.core_state = core.CoreState()
        self.breach_state = breach.BreachState()
        self.launcher_state = launcher.LauncherState()
        self.sentinel_state = sentinel.SentinelState()
        self.gunner_state = gunner.GunnerState()

    def run(self, ct: Controller) -> None:
        self.delegate_behaviour(ct)
    
    """
    Based on the entity type, delegate to the appropriate behaviour function.
    We pass in the state for that entity type, which will be used to make decisions in the behaviour logic.

    This is done by value - i.e., we pass in a copy of the reference to the state objects so that any behaviour logic
    that modifies the state will modify the original state object in this Player instance.
    """
    def delegate_behaviour(self, ct: Controller) -> None:
        etype = ct.get_entity_type()
        if etype == EntityType.CORE:
            core.execute_behaviour(ct, self.core_state)
        elif etype == EntityType.BUILDER_BOT:
            builder_bot.execute_behaviour(ct, self.builder_bot_state)
        elif etype == EntityType.GUNNER:
            gunner.execute_behaviour(ct, self.gunner_state)
        elif etype == EntityType.SENTINEL:
            sentinel.execute_behaviour(ct, self.sentinel_state)
        elif etype == EntityType.BREACH:
            breach.execute_behaviour(ct, self.breach_state)
        elif etype == EntityType.LAUNCHER:
            launcher.execute_behaviour(ct, self.launcher_state)
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
    
    

    