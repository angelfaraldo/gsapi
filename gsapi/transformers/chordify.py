from __future__ import absolute_import, division, print_function

from ..gspattern import Event
from .base_transformer import *


# LEGACY CLASS: could be replaced by Pattern.generateViewpoint("chords")

class EventChord(Event):
    """Represents an event of a pattern.
    An event has a startTime, duration, pitch, velocity and associated tags.

    Class variables:
        startTime: startTime of event
        duration: duration of event
        pitch: pitches of event
        velocity: velocity of event
        tags: list of tags representing the event
    """

    def __init__(self, startTime=0, duration=1.0, components=None, tag=None, label="chord"):
        Event.__init__(self, startTime=startTime, duration=duration, tag=tag)
        self.components = components or []
        self.label = label

    def __repr__(self):
        return "%s %s %s %05.2f %05.2f" % (self.label,
                                           self.tag,
                                           str(self.components),
                                           self.startTime,
                                           self.duration)


class Chordify(BaseTransformer):
    """Makes vertical slices of a pattern"""

    def __init__(self, pattern):
        self.inputPattern = pattern
        self.outputPattern = self.transformPattern()
        self.duration = self.outputPattern.duration
        self.events = self.outputPattern.events
        self.numChords = len(self.outputPattern.events)

    def configure(self, paramDict):
        """Configure current transformer based on implementation
        specific parameters passed in paramDict argument.

        Args:
            paramDict: a dictionary with configuration values
        """
        raise NotImplementedError("Not Implemented.")

    def transformPattern(self):
        """Return a transformed Pattern"""
        self.outputPattern = self.inputPattern.copyWithoutEvents()
        p = -1
        for e in self.inputPattern:
            if e.startTime != p:
                new_chord = EventChord(startTime=e.startTime, duration=e.duration, components=[], tag=())
                for ee in self.inputPattern.getActiveEventsAtTime(e.startTime):
                    new_chord.components.append([ee.pitch, ee.velocity])
                    for tag in ee.tag:
                        new_chord.tag.append(tag)
                self.outputPattern.addEvent(new_chord)
            p = e.startTime
        return self.outputPattern
