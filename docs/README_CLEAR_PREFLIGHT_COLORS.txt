SSS — CLEAR PREFLIGHT STATUS COLORS
====================================

The old emoji status symbols were removed because Windows/Tk can render
them inconsistently and they were not obvious enough.

Preflight now uses actual colored status boxes:

  GREEN  READY   = good
  YELLOW REVIEW  = check/waiting
  RED    PROBLEM = needs attention

Each box also includes the detailed status text.

This changes only the SSS display. It does not change any preflight logic,
recording, streaming, PTZ, chapter, Planning, or YouTube behavior.
