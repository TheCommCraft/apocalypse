from __future__ import annotations
from abc import ABC, abstractmethod, abs

class ApocalypseGame(ABC):
    players : list[Player]
    
    @property
    def dead_players(self):
        return []
    
class Player(ABC):
    pass