SSS — SCRIPTURE END: WEBCAM ONLY + TRANSITION
==============================================

Corrected end-of-Scripture behavior.

When Scripture finishes, SSS now does:

  1. Ctrl + F13
     Load "webcam only" into OBS Preview.

  2. Wait briefly.

  3. Ctrl + Shift
     Perform the normal OBS Studio Mode Preview -> Program transition.

This applies to BOTH:
  FINISH READING
  END READING

So the transition effect is preserved instead of cutting directly back to
the webcam.

The flow is:

  Scripture on Program
        ↓
  Ctrl+F13
  webcam only -> Preview
        ↓
  Ctrl+Shift
  transition -> Program
        ↓
  webcam only on Program

No config files are included or changed.
