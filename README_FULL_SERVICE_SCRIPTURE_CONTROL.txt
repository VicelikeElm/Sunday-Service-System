SSS — FULL-SERVICE SCRIPTURE READING CONTROL
===========================================

This update adds a dedicated Scripture-reading workflow to the main SSS
volunteer screen.

VOLUNTEER WORKFLOW
------------------
The compact workflow is now:

  1 — SERVICE PREP
  2 — LIVE A/V
  3 — SCRIPTURE
  4 — SERMON
  5 — CAMERA VIEW
  6 — END SERVICE


3 — SCRIPTURE
-------------
SSS automatically reads the weekly Scripture from sermon_plan.json.

Example:
  Matthew 12:43-50

Before Prayer has been chapter-marked, the Scripture button shows:

  AFTER PRAYER

and stays disabled.

Once Prayer has been marked, the normal sermon chapter button changes to:

  USE SCRIPTURE BUTTON ↑

and the Scripture control becomes:

  BACK VERSE | START — Matthew 12:43 | END READING


START READING
-------------
One press performs the Scripture setup:

  1. Ctrl + F15
     Puts Webcam TP into OBS Preview.

  2. Ctrl + Shift
     Performs the church OBS Preview/Program transition.

  3. Creates the existing sermon Scripture chapter:
       Matthew 12:43-50

  4. Advances WorshipTools Presenter to the first verse through loopMIDI.

After this, the normal sermon chapter sequence has automatically advanced
past the Scripture chapter to Point 1.


VERSE CONTROL
-------------
For an ordinary same-chapter range such as Matthew 12:43-50, SSS knows
the individual verse progression.

After START:

  NEXT — Matthew 12:44

then:

  NEXT — Matthew 12:45
  NEXT — Matthew 12:46
  ...

After the final verse is displayed:

  FINISH READING

BACK VERSE is also available if Presenter needs to move backward.


END READING
-----------
END READING is always available while Scripture mode is active.

Use it if the pastor stops before reading all planned verses.

It sends:

  Ctrl + Shift

again. In OBS Studio Mode, the webcam that was Program before Scripture
is still in Preview, so this transitions back to the webcam.

END READING does NOT create another chapter.


PRESENTER MIDI
--------------
The supplied Stream Deck settings are built in as defaults:

  MIDI output: loopMIDI Port
  Channel:     10

  NEXT:
    C3 / note 60
    Velocity 126

  BACK:
    D3 / note 62
    Velocity 126

SSS uses the Windows MIDI API directly. No new Python MIDI package is
required.


SYSTEM STATUS
-------------
A new compact SERVICE item appears:

  Presenter   MIDI ready

If loopMIDI Port cannot be found it becomes:

  CHECK — MIDI

This is a review item rather than a recording-blocking failure.


CHAPTER SAFETY
--------------
The dedicated Scripture control owns the Scripture/reference chapter.

When the chapter sequence reaches the Scripture reference, the ordinary
SERMON chapter button is disabled and says:

  USE SCRIPTURE BUTTON ↑

This prevents a volunteer from accidentally creating the Scripture chapter
twice.


TESTING WITHOUT RECORDING
-------------------------
The existing Admin:

  ENABLE CHAPTER / LT TEST MODE

also works with the new Scripture controls.

Suggested test:

  1. Open OBS and WorshipTools Presenter.
  2. Open Admin and enable Chapter / LT Test Mode.
  3. Use the SERMON button once for Prayer.
  4. The SCRIPTURE button becomes active.
  5. Press START Scripture.
  6. Verify:
       Webcam TP moves into Preview.
       Ctrl+Shift transitions it to Program.
       Presenter advances to the first verse.
       NEXT/BACK operate the verse slides.
       END READING transitions back to the webcam.
  7. No real recording chapter is written in Test Mode.

Closing Admin still exits Chapter/LT Test Mode and restores the preserved
real chapter position.


SCRIPTURE PARSING
-----------------
Exact verse labels/counts are automatic for common same-chapter references:

  Matthew 12:43-50
  John 3:16
  1 Corinthians 13:1-7

For a cross-chapter or unusual reference, SSS safely switches to generic:

  NEXT VERSE

with END READING always available.


OPTIONAL CONFIG OVERRIDES
-------------------------
No config changes are required.

These defaults can be overridden later in sunday_config.json if needed:

  "presenter_midi_port": "loopMIDI Port"
  "presenter_midi_channel": 10
  "presenter_next_note": 60
  "presenter_back_note": 62
  "presenter_midi_velocity": 126
  "scripture_preview_settle_seconds": 0.30
  "scripture_transition_settle_seconds": 0.25


INSTALL
-------
Close SSS.

Copy these files into:

  C:\Church\SermonAI

and overwrite sunday_mode.py:

  sunday_mode.py
  sss_scripture_reading.py

No configuration file or persistent PTZ file is included in this patch.
