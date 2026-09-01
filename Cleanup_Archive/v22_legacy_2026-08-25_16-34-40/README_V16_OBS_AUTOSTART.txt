V16 — OBS AUTO-START CHECK
===========================

When Sunday Service System opens:

1. Check whether OBS WebSocket is already reachable.
2. If OBS is already open:
     Do NOT launch another copy.
     Wait for WebSocket to become ready.
3. If OBS is not open:
     Launch OBS automatically.
4. Recheck every 3 seconds for about 30 seconds.

This does NOT:
- start recording
- start streaming
- stop recording
- stop streaming

Recording and streaming remain separate manual buttons in Sunday Mode.

The Launch Sunday Apps button still works too, but OBS no longer depends
on the volunteer pressing that button first.
