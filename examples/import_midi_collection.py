from gsapi import *

crawledFolder = "./corpora/drums/*.mid"

customNoteMapping = {"spam": [(35, '*'), 45],
                     "Kick": 36,
                     "Rimshot": 37,
                     "Snare": 38,
                     "Clap": 39,
                     "Clave": 40,
                     "LowTom": 41,
                     "ClosedHH": 42,
                     "MidTom": 43,
                     "Shake": 44,
                     "HiTom": 45,
                     "OpenHH": 46,
                     "LowConga": 47,
                     "HiConga": 48,
                     "Cymbal": 49,
                     "Conga": 50,
                     "CowBell": 51}


# desiredPatternLength = 16
patterns = gsio.fromMidiCollection(crawledFolder,
                                   {"Kick": 36},
                                   tagsFromTrackNameEvents=False)

print(patterns[0])
print([x.startTime for x in patterns[0].events])
