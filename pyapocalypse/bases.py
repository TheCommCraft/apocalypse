"""
Base classes for apocalypse.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum, auto, Flag
from typing import Optional
from io import BytesIO
import time
from collections.abc import Iterator
from .events import *

class HostSettings(Flag):
    CONTROL_GAME_LOOP = auto()
    RECEIVE_GAME_LOOP = auto()
    SEND_GAME_LOOP = auto()
    HOST = CONTROL_GAME_LOOP | SEND_GAME_LOOP
    CLIENT = RECEIVE_GAME_LOOP
    NODE = SEND_GAME_LOOP | RECEIVE_GAME_LOOP

class GameConnected(ABC):
    """
    Manages a connection.
    """
    connection: Connection
    
    async def send_raw(self, data: bytes):
        await self.connection.send(data)
        
    async def receive_raw(self, timeout: float = 10.0):
        await self.connection.receive(timeout=timeout)

class PlayerConnection(GameConnected):
    """
    Manages a connection to a player.
    """

class GamePerspective(GameConnected):
    """
    Someone looking at information of the game while it is running. Controlled by this runtime of python.
    """
    
    def incoming_event(self):
        pass

class ControlledPlayer(GamePerspective):
    """
    A player that this runtime of python controls.
    """

class Connection(ABC):
    """
    Manages a connection to a host or a client of the game.
    """
    current_iterator: Optional[Iterator]
    streamer: PacketStreamer
    
    def __init__(self):
        self.streamer = PacketStreamer()
        self.current_iterator = None
    
    @abstractmethod
    async def send(self, data: bytes):
        """
        Send raw data.
        """
    
    async def receive(self, timeout: float) -> bytes:
        """
        Receive a packet of raw data.
        """
        end_time = time.time() + timeout
        while True:
            if self.current_iterator is None:
                self.current_iterator = self.streamer.stream(await self.receive_fragment(timeout=(end_time - time.time())))
            value = next(self.current_iterator)
            if value is not None:
                return value
            self.current_iterator = None
    
    @abstractmethod
    async def receive_fragment(self, timeout: float) -> bytes:
        """
        Receive possibly fragmented data.
        """

class ApocalypseGame(ABC):
    """
    A game of Apocalypse.
    """
    players: list[Player]
    owned_perspectives: list[GameConnected]
    host_settings: HostSettings
    intercept_any: list[AnyCard]

    @property
    def dead_players(self) -> list[Player]:
        """
        All dead players in the game.
        """
        return [player for player in self.players if player.get_lifestate() == LifeState.DEAD]

    @property
    def alive_players(self) -> list[Player]:
        """
        All alive players in the game.
        """
        return [player for player in self.players if player.get_lifestate() == LifeState.ALIVE]
    
    @property
    def other_players(self) -> list[Player]:
        """
        All other players in the game.
        """
        return [player for player in self.players if player.get_lifestate() == LifeState.OTHER]

class LifeState(Enum):
    """
    Whether a player is alive, dead or something else.
    """
    ALIVE = auto()
    DEAD = auto()
    OTHER = auto() # Avoid using this

class Player(ABC):
    """
    A player of apocalypse in a game.
    """
    lifestate: LifeState
    health: int
    name: str
    game: ApocalypseGame
    hand_cards: list[AnyActionCard]
    
    def get_lifestate(self):
        """
        Returns the players lifestate.
        """
        return self.lifestate

class CardPermissions(Flag):
    INTERCEPT_ANY = auto()

class AnyCard(ABC):
    """
    Represents an arbitrary card. All cards can theoratically be held by a player.
    """
    id: str
    game: ApocalypseGame
    _holder: Optional[Player] = None
    _newest_holder: Optional[Player] = None
    permissions: CardPermissions
    
    def __init__(self, game: ApocalypseGame, holder: Optional[Player]):
        self.game = game
        self.holder = holder
        if CardPermissions.INTERCEPT_ANY in self.permissions:
            self.game.intercept_any.append(self)

    @property
    def holder(self):
        """
        The player that is currently holding this Card.
        """
        return self._holder

    @holder.setter
    def holder(self, value: Optional[Player]):
        if value is not None:
            self._newest_holder = value
        self._holder = value

    @property
    def newest_holder(self):
        """
        The player that last held this Card.
        """
        return self._newest_holder
    
    @abstractmethod
    def play(self):
        """
        What happens when the card is played by a player.
        """

    @abstractmethod
    def intercept_event(self, event):
        pass

class ChaosCard(AnyCard):
    """
    Represents a chaos card. Intended not to be held by a player (but still possible).
    """
    
    @abstractmethod
    def occur(self):
        """
        What happens when the card occurs.
        """

    def play(self):
        self.occur()

class AnyActionCard(AnyCard):
    """
    Represents an action card. Intended to be held by a player.
    """

class ActionCard(AnyActionCard):
    """
    An Action Card intended to be held by an alive player.
    """

class GhostActionCard(AnyActionCard):
    """
    An Action Card intended to be held by a dead player.
    """

class PacketStreamerMode(Enum):
    RECEIVING_LENGTH = auto()
    RECEIVING_DATA = auto()

class PacketStreamer:
    current_packet: BytesIO
    packet_length: int
    current_packet_length_data: bytes
    mode: PacketStreamerMode
    def __init__(self):
        self.packet_length = 0
        self.current_packet = BytesIO()
        self.current_packet_length_data = b""
        self.mode = PacketStreamerMode.RECEIVING_LENGTH

    def stream(self, fragment: bytes) -> Iterator[bytes]:
        fragment_stream = BytesIO(fragment)
        while True:
            if self.mode == PacketStreamerMode.RECEIVING_LENGTH:
                self.current_packet_length_data += fragment_stream.read(4 - len(self.current_packet_length_data))
                if len(self.current_packet_length_data) >= 4:
                    self.packet_length = int.from_bytes(self.current_packet_length_data)
                    self.mode = PacketStreamerMode.RECEIVING_DATA
                else:
                    break
            if self.mode == PacketStreamerMode.RECEIVING_DATA:
                self.current_packet.write(fragment_stream.read(self.packet_length - self.current_packet.tell()))
                if self.current_packet.tell() >= self.packet_length:
                    yield self.current_packet.getvalue()
                    self.mode = PacketStreamerMode.RECEIVING_DATA
                    self.current_packet = BytesIO()
                    self.current_packet_length_data = b""
                else:
                    break