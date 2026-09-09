SSS — UPCOMING SUNDAY SERMON / VERSE FIX
=========================================

PROBLEM
-------
SSS could keep using the previous Sunday's sermon_plan.json.

That made the Scripture controls show the old passage even though the pastor
had already sent the new Friday sermon email.


FIX 1 — GMAIL SEARCH
--------------------
The Gmail importer no longer requires the literal Gmail search keyword:

  sermon

The pastor may send a subject such as:

  Matt 13:10-17 "The Purpose of Parables!"

without the word "sermon" in the subject.

SSS now fetches recent direct messages from the configured pastor and uses the
structured Title / Text / Outline parser to identify sermon notes.


FIX 2 — UPCOMING SUNDAY DATE
----------------------------
SSS calculates the service being prepared:

  Sunday today if today is Sunday
  otherwise the next Sunday

The importer ONLY selects a parseable pastor sermon email whose calculated
service_date equals that upcoming Sunday.

An old email for the previous Sunday cannot overwrite the upcoming plan.


FIX 3 — STALE PLAN SAFETY
-------------------------
If sermon_plan.json is still for the wrong Sunday:

  System Status -> Sermon becomes yellow CHECK
  Scripture button becomes:
      UPDATE SERMON PLAN

The old Scripture cannot be started accidentally.


CURRENT EXAMPLE
---------------
Friday Aug 28 -> upcoming service Sunday Aug 30.

The correct new pastor email should produce:

  Title:     The Purpose in Parables!
  Scripture: Matt 13:10-17
  Service:   2026-08-30


TEST
----
After installing, run:

  Refresh-Upcoming-Sunday-Sermon.bat

It should print the imported title, Scripture, service date, and points.

Then reopen SSS. The Scripture row should use Matt 13:10-17 rather than the
previous Sunday's Matthew 12:43-50.


INSTALL
-------
Close SSS.

Copy into:
  C:\Church\SermonAI

and overwrite:
  sunday_mode.py
  gmail_sermon_importer.py

Also copy:
  Refresh-Upcoming-Sunday-Sermon.bat

No sunday_config.json or persistent PTZ file is included.
