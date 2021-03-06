#!/usr/bin/env python
# encoding: utf-8

"""
The gspattern module is the core of the GS-API. It declares the classes Event
and Pattern, which are the main holders of musical symbolic information.
"""

from __future__ import absolute_import, division, print_function

import collections
import copy
import logging
import math

from . import gsdefs, gsutil

# logger for pattern related operations
gspatternLog = logging.getLogger("gsapi.gspattern")
gspatternLog.setLevel(level=logging.WARNING)


class Event(object):
    """
    Represents an event in a Pattern. Its attributes are startTime, duration,
    pitch, velocity and one or more tags.

    Parameters
    ----------
    startTime: float
        startTime of the Event.
    duration: float
        duration of Event.
    pitch: int
        pitch of the Event in midi note numbers.
    velocity: int
        velocity of event in midi format (0-127).
    tag: string, tuple, object
        any hashable object representing the event, except lists.
    originPattern: Pattern
        keeps track of origin pattern for events generated from pattern,
        e.g., a chord event can still access to its individual components
        via originPattern (see Pattern.generateViewpoints)

    """
    def __init__(self, startTime=0, duration=1, pitch=60, velocity=80,
                 tag=(), originPattern=None):

        self.startTime = startTime
        self.duration = duration
        self.pitch = pitch
        self.velocity = velocity
        self.originPattern = originPattern

        #if not tag:
        #    self.tag = () # since it is assigning a tuple,
        # i'll do it in the initialization instead of 'None'
        if isinstance(tag, list):
            gspatternLog.error("'tag' can't be a list, converting to tuple.")
            self.tag = tuple(tag)
        elif not isinstance(tag, collections.Hashable):
            gspatternLog.error("'tag' has to be hashable, trying conversion to tuple.")
            self.tag = (tag,)
        else:
            self.tag = tag

    def __repr__(self):
        return "%s %i %i %05.4f %05.4f" % (self.tag, self.pitch, self.velocity, self.startTime, self.duration)

    def __eq__(self, other):
        if isinstance(other, Event):
            return (self.startTime == other.startTime) and (self.pitch == other.pitch) and \
                   (self.velocity == other.velocity) and (self.duration == other.duration) and (self.tag == other.tag)
        return NotImplemented

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def hasCommonTagWith(self, event):
        """
        Compare tags between events.

        Parameters
        ----------
        event: Event
            an Event to compare with.

        Returns
        -------
        bool: True if at least one tag is equal.

        """
        # if type(self.tag)!=type(event.tag):
        #     return False
        return self.hasOneOfTags(event.tag)

    def hasOneOfTags(self, tags):
        """
        Compare this event's tags with a list of possible tag.

        Parameters
        ----------
        tags: list
            list of tags to compare with.

        Returns
        -------
            bool: True if at least one tag is equal.
        """
        for t in tags:
            if (t == self.tag) or (t in self.tag):
                return True
        return False

    def isTag(self, tag):
        """
        Compare this Event's tag with a given tag.

        Parameters
        ----------
        tag: str
            the tag to compare with.

        Returns
        -------
        bool: True if the event's tag is equal to the specified tag.
        """
        return self.tag == tag

    def allTagsAreEqualWith(self, myEvent):
        """
        Compare this Event's tag with other Event's tags.

        Parameters
        ----------
        myEvent: Event
            Event to compare with.

        Returns
        -------
            bool: True if tags are equal.

        """
        self.isTag(myEvent.tag)

    def endTime(self):
        """Get the time at which the Event ends.

        Returns
        -------
        float: the time when this event ends.

        """
        return self.startTime + self.duration

    def copy(self):
        """
        Copy an event.

        Returns
        -------
        Event: A deepcopy of this event to be manipulated without changing the
        original.

        """
        return copy.deepcopy(self)

    def cutInSteps(self, stepSize):
        """
        Cut an event in steps of stepsize length.

        Parameters
        ----------
        stepSize: float
            new size of each newly produced Event

        Returns
        -------
            list: a list of Events of length `stepSize`
        """
        res = []
        num = max(1, int(self.duration / stepSize))  # if smaller still take it
        for i in range(num):
            newE = self.copy()
            newE.startTime = self.startTime + i * stepSize
            newE.duration = stepSize
            res += [newE]
        return res

    def containsTime(self, time):
        """
        Check whether an Event is active at a specified time.

        Parameters
        ----------
        time: float
            time to compare with

        Returns
        -------
        bool: True if event is active at the specified time.

        """
        return (time >= self.startTime) and (
        time < self.startTime + self.duration)


class Pattern(object):
    """
    Class representing a Pattern (i.e. a collection of Events).
    Holds a list of events and provides basic manipulation functions.

    Parameters
    ----------
    duration: float
        length of pattern. Usually in beats, but time scale is up to
        the user (it can be useful if working on 32th note steps).
    events: list of Events
        list of Events for this pattern.
    bpm: float
        initial tempo in beats per minute for this pattern (default: 120).
    timeSignature: list of ints [i,i]
        list of integers representing the time signature as [numerator, denominator].
     startTime: float
        startTime of pattern (useful when splitting in sub patterns).
     viewPoints: dict
        dict of ViewPoints
    key: str
        The key of the pattern
    name: str
        A name given to the pattern

    """
    def __init__(self, duration=0, events=None, bpm=120, timeSignature=(4, 4),
                 key=None,  originFilePath=None, name=None):
        self.duration = duration
        if events:
            self.events = events
        else:
            self.events = []
        self.viewpoints = {}
        self.bpm = bpm
        self.timeSignature = timeSignature
        self.key = key
        self.originFilePath = originFilePath
        self.name = name
        self.startTime = 0
        self.originPattern = None
        self.resolution = 960

    def __eq__(self, other):
        if isinstance(other, Pattern):
            return (self.events == other.events) and (
                self.duration == other.duration) and (
                       self.timeSignature == other.timeSignature) and (
                       self.startTime == other.startTime)
        return NotImplemented

    def __getitem__(self, index):
        """
        Utility to access events as list member:
        Pattern[idx] = Pattern.events[idx]

        """
        return self.events[index]

    def __len__(self):
        return len(self.events)

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __repr__(self):
        """
        Print out the list of events.

        Notes
        -----
        Each line represents an event formatted as
        '[tag] pitch velocity startTime duration'

        """
        s = "Name: %s\n" \
            "Duration: %.2f\n" \
            "BPM: %.2f\n" \
            "TimeSignature: %i/%i\n" \
            "Key: %s\n" \
            "FilePath: %s\n\n" % (
            self.name,
            self.duration,
            self.bpm,
            self.timeSignature[0],
            self.timeSignature[1],
            self.key,
            self.originFilePath)
        for e in self.events:
            s += str(e) + "\n"
        return s

    def __setitem__(self, index, item):
        self.events[index] = item

    def addEvent(self, myEvent):
        """
        Add an event increasing its duration if needed.

        Parameters
        ----------
        myEvent: Event
            the Event to be added.

        """
        self.events += [myEvent]
        self.durationToLastEvent()

    def alignOnGrid(self, stepSize, repeatibleTags=['silence']):
        """
        Align the pattern on a temporal grid.

        Parameters
        ----------
        stepSize: int
            temporal definition of the grid
        repeatibleTags: list of str
            tags

        Notes
        -----
        Useful to deal with step-sequenced patterns:
        - all events durations are shortened to stepsize
        - all events startTimes are quantified to stepsize

        RepeatibleTags allow to deal with `silences type` of events. If a
        silence spread over tags than one stepsize, we generate an event
        for each stepSize. Thus each step is ensured to be filled with one
        distinct event at least.

        """
        newEvents = []
        for e in self.events:
            if e.isTag(repeatibleTags):
                evToAdd = e.cutInSteps(stepSize)
            else:
                evToAdd = [e]
            for ea in evToAdd:
                ea.startTime = int(ea.startTime / stepSize + 0.5) * stepSize
                # avoid adding last event out of duration range
                if ea.startTime < self.duration:
                    ea.duration = stepSize
                    newEvents += [ea]

        self.events = newEvents
        self.removeOverlapped()
        return self

    def applyLegato(self, usePitchValues=True):
        """
        This function supresses the possible silences in this pattern by
        stretching consecutive identical events (tags or pitch numbers).

        Parameters
        ----------
        usePitchValues: boolean
            use pitch note numbers instead of tags (it is a bit faster).

        """

        def _perVoiceLegato(myPattern):
            myPattern.reorderEvents()
            if len(myPattern) == 0:
                gspatternLog.warning("Trying to apply legato on an empty voice")
                return
            for idx in range(1, len(myPattern)):
                diff = myPattern[idx].startTime - myPattern[idx - 1].endTime()
                if diff > 0:
                    myPattern[idx - 1].duration += diff
            diff = myPattern.duration - myPattern[-1].endTime()
            if diff > 0:
                myPattern[-1].duration += diff
        if usePitchValues:
            for p in self.getAllPitches():
                voice = self.getPatternWithPitch(p)
                _perVoiceLegato(voice)
        for t in self.getAllTags():
            voice = self.getPatternWithTags(tagToLookFor=t, exactSearch=False, makeCopy=False)
            _perVoiceLegato(voice)

    def copy(self):
        """
        Deepcopy a pattern

        """
        return copy.deepcopy(self)

    def copyWithoutEvents(self):
        """
        Copy all fields but events.
        Useful for creating patterns from patterns.

        Returns
        -------
        Pattern: a copy of the Pattern without events.

        """
        p = Pattern()
        p.duration = self.duration
        p.bpm = self.bpm
        p.timeSignature = self.timeSignature
        p.originFilePath = self.originFilePath
        p.name = self.name
        return p

    def fillWithPreviousEvent(self):
        """
        Fill the gaps between onsets making longer
        the duration of the previous event.
        """

        onsets = []
        for e in self.events:
            if e.startTime not in onsets:
                onsets.append(e.startTime)
        onsets.append(self.duration)

        for e in self.events:
            e.duration = onsets[onsets.index(e.startTime) + 1] - e.startTime

    def fillWithSilences(self, maxSilenceTime=0, perTag=False,
                         silenceTag='silence', silencePitch=0):
        """
        Fill empty time intervals (i.e no event) with event 'silence'.

        Parameters
        ----------
        maxSilenceTime: float
            if positive value is given, will add multiple silence of
            maxSilenceTime for empty time larger than maxSilenceTime.
        perTag: bool
            fill silence for each Tag
        silenceTag: str
            tag that will be used when inserting the silence event
        silencePitch: int
            the desired pitch of new silences events

        """
        self.reorderEvents()

        def _fillListWithSilence(myPattern, silTag, silPitch=0):
            lastOff = 0
            newEvents = []

            for e in myPattern.events:
                if e.startTime > lastOff:
                    if maxSilenceTime > 0:
                        while e.startTime - lastOff > maxSilenceTime:
                            newEvents += [
                                Event(lastOff, maxSilenceTime, silPitch, 0,
                                      silTag)]
                            lastOff += maxSilenceTime
                    newEvents += [
                        Event(lastOff, e.startTime - lastOff, silPitch, 0,
                              silTag)]
                newEvents += [e]
                lastOff = max(lastOff, e.startTime + e.duration)

            if lastOff < myPattern.duration:
                if maxSilenceTime > 0:
                    while lastOff < myPattern.duration - maxSilenceTime:
                        newEvents += [
                            Event(lastOff, maxSilenceTime, silPitch, 0,
                                  silTag)]
                        lastOff += maxSilenceTime
                newEvents += [
                    Event(lastOff, myPattern.duration - lastOff, silPitch, 0,
                          silTag)]
            return newEvents

        if not perTag:
            self.events = _fillListWithSilence(self, silenceTag, silencePitch)
        else:
            allEvents = []
            for t in self.getAllTags():
                allEvents += _fillListWithSilence(
                    self.getPatternWithTags(tagToLookFor=t,
                                            exactSearch=False,
                                            makeCopy=False),
                    silenceTag, silencePitch)
            self.events = allEvents

    def fromJSONDict(self, json, parentPattern=None):
        """
        Loads a JSON API dict object to this pattern

        Parameters
        ----------
        json: dict
            a dict created from reading json file with GS-API JSON format.

        """
        self.name = json['name']
        self.duration = json['timeInfo']['duration']
        self.bpm = json['timeInfo']['bpm']
        self.timeSignature = tuple(json['timeInfo']['timeSignature'])
        if 'originPattern' in json:
            def findOriginPatternInParent(name):
                if not name:
                    return None
                checkedPattern = parentPattern
                while checkedPattern:
                    if checkedPattern.name == name:
                        return checkedPattern
                    checkedPattern = checkedPattern.originPattern

                assert False, "no origin pattern found"

            self.originPattern = findOriginPatternInParent(
                    json['originPattern'])

        hasIndexedTags = 'eventTags' in json.keys()
        if hasIndexedTags:
            tags = json['eventTags']
            for e in json['eventList']:
                self.events += [Event(startTime=e['on'],
                                      duration=e['duration'],
                                      pitch=e['pitch'],
                                      velocity=e['velocity'],
                                      tag=tuple(
                                              [tags[f] for f in e['tagsIdx']])
                                      )]
        else:
            for e in json['eventList']:
                self.events += [Event(startTime=e['on'],
                                      duration=e['duration'],
                                      pitch=e['pitch'],
                                      velocity=e['velocity'],
                                      tag=e['tag']
                                      )]

        self.viewpoints = {k: Pattern().fromJSONDict(v, parentPattern=self) for
                           k, v in json['viewpoints'].items()}
        self.durationToLastEvent()

        return self

    def generateViewpoint(self, name, descriptor=None, sliceType=None):
        """
        generate viewpoints in this Pattern
        Args:
            name: name of the viewpoint generated , if name is one of ["chords",] it will generate the default descriptor
            descriptor : if given it's the descriptor used
            sliceType: type of slicing to compute viewPoint:
                if integer its duration based see:splitInEqualLengthPatterns
                if "perEvent" generates new pattern every new events startTime,
                if "all" get the whole pattern (generate one and only viewPoint value)
        """

        def _computeViewpoint(originPattern, descriptor, name, sliceType=1):
            """
            Internal function for computing viewPoint

            """
            viewpoint = originPattern.copyWithoutEvents()
            viewpoint.name = name
            viewpoint.originPattern = originPattern

            if isinstance(sliceType, int):
                step = sliceType
                patternsList = originPattern.splitInEqualLengthPatterns(step)

            elif sliceType == "perEvent":
                originPattern.reorderEvents()
                lastTime = -1
                patternsList = []
                for consideredEvent in originPattern:
                    if lastTime < consideredEvent.startTime:  # group all identical startTimeEvents
                        pattern = originPattern.copyWithoutEvents()
                        pattern.startTime = consideredEvent.startTime
                        pattern.events = originPattern.activeEventsAtTime(
                                consideredEvent.startTime)
                        pattern.duration = 0

                        for se in pattern.events:
                            # TODO do we need to trim to beginning?
                            # some events can have negative startTimes and each GSpattern.duration corresponds to difference between consideredEvent.startTime and lastEvent.startTime (if some events were existing before start of consideredEvent)
                            #     se.startTime-=consideredEvent.startTime
                            eT = se.endTime() - pattern.startTime
                            if eT > pattern.duration:
                                pattern.duration = eT
                        lastTime = consideredEvent.startTime

                        patternsList += [pattern]

            elif sliceType == "all":
                patternsList = [originPattern]
            else:
                gspatternLog.error("sliceType %s not valid" % (sliceType))
                assert False

            for subPattern in patternsList:
                if subPattern:
                    viewpoint.events += [Event(duration=subPattern.duration, startTime=subPattern.startTime,
                                               tag=descriptor.getDescriptorForPattern(subPattern),
                                               originPattern=subPattern)]

            return viewpoint

        if descriptor:
            self.viewpoints[name] = _computeViewpoint(originPattern=self, descriptor=descriptor,
                                                      sliceType=sliceType, name=name)
        else:
            if name == "chords":
                from .gsdescriptors import Chord
                self.viewpoints[name] = _computeViewpoint(originPattern=self, descriptor=Chord(),
                                                          sliceType=4, name=name)
        # can use it as a return value
        return self.viewpoints[name]

    def activeEventsAtTime(self, time, tolerance=0):  # todo: implement tolerance
        """
        Get all events currently active at a givent time.

        Args:
            time: time asked for
            tolerance: admited deviation of start time
        Returns:
            list of events
        """
        res = []
        for e in self.events:
            if 0 <= time - e.startTime < e.duration:
                res += [e]
        return res

    def getIdenticalEvents(self, event, allTagsMustBeEquals=True):
        """
        Get a list of events with the same tag or tags.

        Parameters
        __________
        event: Event
            event to compare with
        allTagsMustBeEquals: bool
            if set to True, events are considered identical when all tags
            coincide. It set to False, one common tag will produce output.

        Returns:
            list of events that have all or one tags in common
        """
        res = []
        for e in self.events:
            equals = False
            equals = event.allTagsAreEqualWith(
                    e) if allTagsMustBeEquals else event.hasCommonTagWith(e)
            if equals:
                res += [e]

    def getFilledWithSilences(self, maxSilenceTime=0, perTag=False, silenceTag='silence'):
        pattern = self.copy()
        pattern.fillWithSilences(maxSilenceTime=maxSilenceTime, perTag=perTag,
                                 silenceTag=silenceTag)
        return pattern

    def lastNoteOff(self):
        """
        Gets last event's end time

        Returns
        -------
        lastNoteOff: float
             The time corresponding to the end of the last event.

        """
        if len(self.events):
            self.reorderEvents()
            return self.events[-1].duration + self.events[-1].startTime
        else:
            return None

    def patternFromTimeSlice(self, startTime, length, trimEnd=True):
        """
        Returns a pattern within the given timeslice.

        Parameters
        ----------
        startTime: float
            start time for time slice
        length: float
            length of time slice
        trimEnd: bool
            cut any events ending after startTime + length.

        Returns
        -------
            new Pattern within the given time slice.

        """
        p = self.copyWithoutEvents()
        p.startTime = startTime
        p.duration = length
        for e in self.events:
            if 0 <= (e.startTime - startTime) < length:
                newEv = e.copy()
                newEv.startTime -= startTime
                p.events += [newEv]
        if trimEnd:
            for e in p.events:
                toCrop = e.startTime + e.duration - length
                if toCrop > 0:
                    e.duration -= toCrop
        return p

    def getStartingEventsAtTime(self, time, tolerance=0):
        """ Get all events activating at a given time.

        Args:
            time: time asked for
            tolerance: allowed deviation of start time
        Returns:
            list of events
        """
        res = []
        for e in self.events:
            if time - e.startTime >= 0 and time - e.startTime <= tolerance:
                res += [e]
        return res

    def getAllTags(self):
        """ Returns all used tags in this pattern.

        Returns:
            set of tags composed of all possible tags

        """
        tagsList = []
        for e in self.events:
            tagsList += [e.tag]
        tagsList = set(tagsList)
        return tagsList

    def getAllPitches(self):
        """ Returns all used pitch in this pattern.

        Returns:
            list of integers composed of all pitches present in this pattern
        """
        pitchs = []
        for e in self.events:
            pitchs += [e.pitch]
        pitchs = list(set(pitchs))
        return pitchs

    def getPatternWithTags(self, tagToLookFor, exactSearch=True,
                           makeCopy=True):
        """Returns a sub-pattern with the given tags.

        Args:
            tagToLookFor: tag,tags list or lambda  expression (return boolean based on tag input): tags to be checked for
            exactSearch: bool: if True the tags argument can be an element of tag to look for, example : if we set tags='maj',an element with tag ('C','maj') will be valid
            makeCopy: do we return a copy of original events (avoid modifying originating events when modifying the returned subpattern)
        Returns:
            a Pattern with only events that tags corresponds to given tagToLookFor
        """
        if isinstance(tagToLookFor, list):
            if exactSearch:
                gspatternLog.error(
                    "cannot search exactly with a list of elements")
            boolFunction = lambda inTags: len(
                inTags) > 0 and inTags in tagToLookFor
        elif callable(tagToLookFor):
            boolFunction = tagToLookFor
        else:
            # tuple / string or any hashable object
            if exactSearch:
                boolFunction = lambda inTags: inTags == tagToLookFor
            else:
                boolFunction = lambda inTags: (inTags == tagToLookFor) or (
                len(inTags) > 0 and tagToLookFor in inTags)

        res = self.copyWithoutEvents()
        for e in self.events:
            found = boolFunction(e.tag)
            if found:
                newEv = e if not makeCopy else e.copy()
                res.events += [newEv]
        return res

    def getPatternWithPitch(self, pitch, makeCopy=True):
        """Returns a sub-pattern with the given pitch.

        Args:
            pitch: pitch to look for
            makeCopy: do we return a copy of original events (avoid modifying originating events when modifying the returned subpattern)
        Returns:
            a Pattern with only events that pitch corresponds to given pitch
        """
        res = self.copyWithoutEvents()
        for e in self.events:
            found = (e.pitch == pitch)
            if found:
                newEv = e if not makeCopy else e.copy()
                res.events += [newEv]

        return res

    def getPatternWithoutTags(self, tagToLookFor, exactSearch=False, makeCopy=True):
        """
        Returns a sub-pattern without the given tags.

        Parameters
        ----------
        tagToLookFor: tag or tag list
            tags to be checked for
        exactSearch: bool
            if True the tags have to be exactly the same as tagToLookFor,
            else they can be included in events tag.
        makeCopy: bool
            do we return a copy of original events (avoid modifying originating
             events when modifying the returned subpattern).

        Returns
        -------
            A Pattern with events without specified tags.
        """

        if isinstance(tagToLookFor, list):
            if exactSearch:
                gspatternLog.error(
                    "cannot search exactly with a list of elements")
            boolFunction = lambda inTags: len(
                inTags) > 0 and inTags in tagToLookFor
        elif callable(tagToLookFor):
            boolFunction = tagToLookFor
        else:
            # tuple / string or any hashable object
            if exactSearch:
                boolFunction = lambda inTags: inTags == tagToLookFor
            else:
                boolFunction = lambda inTags: (inTags == tagToLookFor) or (
                len(inTags) > 0 and tagToLookFor in inTags)

        res = self.copyWithoutEvents()
        for e in self.events:
            needToExclude = boolFunction(e.tag)
            if not needToExclude:
                newEv = e if not makeCopy else e.copy()
                res.events += [newEv]
        return res

    # def quantize(self, stepSize=0.25, quantizeStartTime=True, quantizeDuration=True):
    #     """ Quantize events.
    #
    #     Args:
    #         stepSize: the duration that we want to quantize to
    #         quantizeStartTime: do we quantize startTimes
    #         quantizeDuration: do we quantize duration?
    #     """
    #     beatDivision = 1.0 / stepSize
    #     if quantizeStartTime and quantizeDuration:
    #         for e in self.events:
    #             e.startTime = int(e.startTime * beatDivision) * 1.0 / beatDivision
    #             e.duration = int(e.duration * beatDivision) * 1.0 / beatDivision
    #     elif quantizeStartTime:
    #         for e in self.events:
    #             e.startTime = int(e.startTime * beatDivision) * 1.0 / beatDivision
    #     elif quantizeDuration:
    #         for e in self.events:
    #             e.duration = int(e.duration * beatDivision) * 1.0 / beatDivision


    def quantize(self, stepSize=0.25, quantizeStartTime=True, quantizeDuration=True):
        """ Quantize events.

        Args:
            stepSize: the duration that we want to quantize to
            quantizeStartTime: do we quantize startTimes
            quantizeDuration: do we quantize duration?
        """
        beat_grid = 2 * (1.0 / stepSize)
        for e in self.events:
            if quantizeStartTime:
                starts = (e.startTime * beat_grid) % 2
                if starts < 1.0:
                    e.startTime = math.floor(e.startTime * beat_grid) / beat_grid
                elif starts == 1.0:
                    e.startTime = ((e.startTime - (stepSize * 0.5)) * beat_grid) / beat_grid
                else:
                    e.startTime = math.ceil(e.startTime * beat_grid) / beat_grid
            if quantizeDuration:
                if e.duration < (stepSize * 0.5):
                    e.duration = stepSize
                else:
                    durs = (e.duration * beat_grid) % 2
                    if durs < 1.0:
                        e.duration = math.floor(e.duration * beat_grid) / beat_grid
                    elif durs == 1.0:
                        e.duration = ((e.duration + (stepSize * 0.5)) * beat_grid) / beat_grid
                    else:
                        e.duration = math.ceil(e.duration * beat_grid) / beat_grid


    def removeByTags(self, tags):
        """Remove all event(s) in a pattern with specified tag(s).

        Args:
            tags: list of tag(s)
        """
        for e in self.events:
            if e.hasOneOfTags(tuple(tags)):
                self.removeEvent(e)

    def removeEvent(self, event):
        """remove given event
        Args:
            event: the Event to be added
        """
        idxToRemove = []
        idx = 0
        for e in self.events:
            if event == e:
                idxToRemove += [idx]
            idx += 1

        for i in idxToRemove:
            del self.events[i]

    def removeOverlapped(self, usePitchValues=False):
        """
        Remove overlapped Events.

        Parameters
        ----------
        usePitchValues: bool
            use pitch to discriminate events

        """
        self.reorderEvents()
        newList = []
        idx = 0
        for e in self.events:
            found = False
            overLappedEv = []
            for i in range(idx + 1, len(self.events)):
                ee = self.events[i]
                if usePitchValues:
                    equals = (ee.pitch == e.pitch)
                else:
                    equals = (ee.tag == e.tag)
                if equals:
                    if (ee.startTime >= e.startTime) and (
                        ee.startTime < e.startTime + e.duration):
                        found = True
                        if ee.startTime - e.startTime > 0:
                            e.duration = ee.startTime - e.startTime
                            newList += [e]
                            overLappedEv += [ee]
                        else:
                            gspatternLog.info("strict overlapping of start times %s with %s" % (e, ee))

                if ee.startTime > (e.startTime + e.duration):
                    break
            if not found:
                newList += [e]
            else:
                gspatternLog.info("remove overlapping %s with %s" % (e, overLappedEv))
            idx += 1
        self.events = newList
        # return self

    def reorderEvents(self):
        """
        Ensure than our internal event list `events` is time sorted.
        It can be useful for time sensitive events iteration.

        """
        self.events.sort(key=lambda x: x.startTime, reverse=False)

    def toJSONDict(self, useTagIndexing=True):
        """
        Gives a standard dict for json output.

        Parameters
        ----------
        useTagIndexing: bool
            if True, tags are stored as indexes from a list of all tags
            This reduces the size of the JSON file.

        """
        res = {}
        self.durationToLastEvent()
        res['name'] = self.name
        if self.originPattern: res['originPattern'] = self.originPattern.name
        res['timeInfo'] = {'duration':      self.duration, 'bpm': self.bpm,
                           'timeSignature': self.timeSignature}
        res['eventList'] = []
        res['viewpoints'] = {k: v.toJSONDict(useTagIndexing) for k, v in
                             self.viewpoints.items()}
        if useTagIndexing:
            allTags = self.getAllTags()
            res['eventTags'] = allTags

            def findIdxforTags(tags, allTags):
                return [allTags.index(x) for x in tags]

            for e in self.events:
                res['eventList'] += [{'on':       e.startTime,
                                      'duration': e.duration,
                                      'pitch':    e.pitch,
                                      'velocity': e.velocity,
                                      'tagIdx':   findIdxforTags(e.tag,
                                                                 allTags)
                                      }]
        else:
            for e in self.events:
                res['eventList'] += [{'on':       e.startTime,
                                      'duration': e.duration,
                                      'pitch':    e.pitch,
                                      'velocity': e.velocity,
                                      'tag':      e.tag
                                      }]

        return res

    def durationToLastEvent(self, onlyIfBigger=True):
        """Sets duration to last event NoteOff

        Parameters
        ----------
        onlyIfBigger: bool
            update duration only if last Note off is bigger

        Notes
        -----
        If inner events have a bigger time span than self.duration,
        increase the duration to fit.

        """
        total = self.lastNoteOff()
        if total and (total > self.duration or not onlyIfBigger):
            self.duration = total

    def durationToBar(self):
        """
        Sets the duration of the pattern to fit a complete bar.

        """
        # TODO: get time signature from pattern and operate from there.
        actual_duration = self.duration
        beats_per_bar = self.timeSignature[0]
        self.duration = math.ceil(actual_duration / beats_per_bar) * beats_per_bar
        # self.addEvent(Event(self.lastNoteOff(), self.duration - self.lastNoteOff(), 0, 0,'silence'))

    def splitInEqualLengthPatterns(self, desiredLength, viewpointName=None, makeCopy=True, supressEmptyPattern=True):
        """Splits a pattern in consecutive equal length cuts.

        Args:
            desiredLength: length desired for each pattern
            viewpointName : if given, slice the underneath viewpoint instead
            makeCopy: returns a distint copy of original pattern events, if you don't need original pattern anymore setting it to False will increase speed

        Returns:
            a list of patterns of length desiredLength
        """

        def _handleEvent(e, patterns, makeCopy):
            p = int(math.floor(e.startTime * 1.0 / desiredLength))
            numPattern = str(p)
            if numPattern not in patterns:
                patterns[numPattern] = patternToSlice.copyWithoutEvents()
                patterns[numPattern].startTime = p * desiredLength
                patterns[numPattern].duration = desiredLength
                patterns[
                    numPattern].name = patternToSlice.name + "_" + numPattern
            newEv = e if not makeCopy else e.copy()

            if newEv.startTime + newEv.duration > (p + 1) * desiredLength:
                remainingEvent = e.copy()
                newOnset = (p + 1) * desiredLength
                remainingEvent.duration = remainingEvent.endTime() - newOnset
                remainingEvent.startTime = newOnset
                _handleEvent(remainingEvent, patterns, makeCopy)
                newEv.duration = (p + 1) * desiredLength - e.startTime

            newEv.startTime -= p * desiredLength
            patterns[numPattern].events += [newEv]

        patterns = {}

        patternToSlice = self.viewpoints[
            viewpointName] if viewpointName else self
        for e in patternToSlice.events:
            _handleEvent(e, patterns, makeCopy)
        res = []
        maxListLen = int(
            math.ceil(patternToSlice.duration * 1.0 / desiredLength))
        for p in range(maxListLen):
            pName = str(p)
            if pName in patterns:
                curPattern = patterns[pName]
                curPattern.durationToLastEvent()
            else:
                curPattern = None
            if (not supressEmptyPattern) or curPattern:
                res += [curPattern]
        return res

    def printASCIIGrid(self, blockSize=1):

        def __areSilenceEvts(l):
            if len(l) > 0:
                for e in l:
                    if 'silence' not in e.tag:
                        return False
            return True

        for t in self.getAllTags():
            noteOnASCII = '|'
            sustainASCII = '>'
            silenceASCII = '-'
            out = "["
            p = self.getPatternWithTags(t, makeCopy=True)
            isSilence = __areSilenceEvts(p.activeEventsAtTime(0))
            # inited = False
            lastActiveEvent = p.events[0]
            numSteps = int(self.duration * 1.0 / blockSize)
            for i in range(numSteps):
                time = i * 1.0 * blockSize
                el = p.activeEventsAtTime(time)
                newSilenceState = __areSilenceEvts(el)
                if newSilenceState != isSilence:
                    if newSilenceState:
                        out += silenceASCII
                    else:
                        out += noteOnASCII
                        lastActiveEvent = el[0]
                elif newSilenceState:
                    out += silenceASCII
                elif not newSilenceState:
                    if el[0].startTime == lastActiveEvent.startTime:
                        out += sustainASCII
                    else:
                        out += noteOnASCII
                        lastActiveEvent = el[0]

                isSilence = newSilenceState
                # inited = True
            out += "]: " + t
            print(out)

    def timeStretch(self, ratio):
        """Time-stretch a pattern.

        Args:
            ratio: the ratio used for time stretching
        """
        for e in self.events:
            e.startTime *= ratio
            e.duration *= ratio
        self.duration *= ratio

    def transpose(self, interval):
        """
        Transposes a Pattern to the desired interval.

        Parameters
        ----------
        interval: int
            transposition factor in semitones (positive or negative int)

        """
        for e in self.events:
            e.pitch += interval
            e.tag = [gsutil.pitch2name(e.pitch, gsdefs.defaultPitchNames)]


def patternToList(myPattern):
    """
    Converts a myPattern to a regular python list.

    """
    list_of_events = []
    for event in myPattern.events:
        list_of_events.append([event.pitch, event.startTime, event.duration])
    return list_of_events
