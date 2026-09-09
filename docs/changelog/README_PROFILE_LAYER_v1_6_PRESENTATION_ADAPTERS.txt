SSS PROFILE LAYER v1.6 — PRESENTATION ADAPTER FOUNDATION
========================================================

This implements roadmap item #3: Integration Adapters.

FIRST LIVE ADAPTER
------------------
WorshipTools Presenter

PROFILE mode uses the same proven SSS MIDI control already used by the Perry
system:

NEXT:
  Presenter
  Channel 10
  Note 60
  Velocity 126

PREVIOUS:
  Presenter
  Channel 10
  Note 62
  Velocity 126

LEGACY remains the default and keeps the previous direct code path.


PROFILE MANAGER
---------------
New button:

  CONFIGURE PRESENTATION FOR THIS PROFILE

Presentation Setup includes:

  Configuration Source
    LEGACY
    PROFILE

  Provider
    WorshipTools Presenter
    ProPresenter
    Bitfocus Companion
    PowerPoint / Keyboard
    None


SAFETY
------
Only WorshipTools Presenter can currently be saved as PROFILE/live.

If someone selects ProPresenter, Companion, or PowerPoint and tries to save
PROFILE mode, SSS refuses and tells them to keep it on LEGACY until that
adapter is implemented.

That prevents an unfinished adapter from breaking a live Sunday service.


ADAPTER ARCHITECTURE
--------------------
New module:

  sss_presentation_adapters.py

This creates a provider registry and standardized presentation actions:

  next slide
  previous slide

The main SSS Scripture controls now behave as:

  LEGACY
    -> existing exact Presenter MIDI path

  PROFILE + WorshipTools Presenter
    -> presentation adapter
    -> same proven Presenter MIDI path

This proves the adapter architecture without changing what actually happens
on the Perry church PC.


NEXT ADAPTERS
-------------
The registry already reserves slots for:

  ProPresenter
  Bitfocus Companion
  PowerPoint / Keyboard

Those will be implemented one at a time.


NO CHANGES TO
-------------
Recording / streaming
OBS profile mappings
PTZ
Gmail / Planning
chapters
lower thirds
audio
YouTube
Sermon AI

No credentials or runtime configuration files are included.
