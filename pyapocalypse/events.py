"""
Events
"""
from __future__ import annotations
from typing import TypeVar, Generic
from abc import ABC, abstractmethod
from .bases import AnyCard

T = TypeVar("T")

class Event(ABC, Generic[T]):
    """
    Abstract event class.
    """
    value: T
    
    @abstractmethod
    def __init__(self):
        pass
    
    def intercept(self, value: T):
        """
        Intercept the event to change its value.
        """
        self.value = value
        

class BooleanEvent(Event[bool]):
    """
    Event with a boolean.
    """

class DisruptEvent(BooleanEvent):
    """
    Event that can be disrupted/prevented.
    """
    def __init__(self):
        self.value = True
    
    def prevent(self):
        """
        Prevent the event.
        """
        self.intercept(False)

class InterceptionEvent(DisruptEvent):
    """
    Event from an interception.
    """
    intercepted_event: Event
    interception_source: AnyCard
    def __init__(self, intercepted_event: Event, interception_source: AnyCard):
        self.intercepted_event = intercepted_event
        self.interception_source = interception_source
        super().__init__()