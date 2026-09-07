SSS PROFILE LAYER v1.7 — LIVE PROPRESENTER API ADAPTER

Adds the second live Presentation adapter: ProPresenter.

Direct API:
  connection check: GET /version
  NEXT: GET /v1/presentation/active/next/trigger
  PREVIOUS: GET /v1/presentation/active/previous/trigger

Default:
  Host 127.0.0.1
  Port 50001

Profile Manager -> CONFIGURE PRESENTATION FOR THIS PROFILE now allows:
  LEGACY or PROFILE
  WorshipTools Presenter
  ProPresenter
  Bitfocus Companion (planned)
  PowerPoint / Keyboard (planned)

For ProPresenter, enter host/IP + port and use:
  CHECK PROPRESENTER CONNECTION

That check does not move slides.

System Status also understands Presentation PROFILE mode:
  ProPresenter ready
instead of incorrectly requiring the WorshipTools MIDI port.

The general Setup Wizard remains safe:
- choosing a new presentation provider does not silently activate it live
- an explicit Presentation Setup/Profile selection is still required
- if the provider is changed after a live PROFILE adapter was configured,
  SSS returns presentation control to LEGACY until the new provider is tested

Recording and streaming are never started by Presentation Setup.

No credentials, profiles, .env, Gmail token, PTZ runtime settings, or
sunday_config.json are included.
