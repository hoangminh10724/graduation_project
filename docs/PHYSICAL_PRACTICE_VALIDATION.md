# Physical practice update: verification

Verified locally on 18 November 2026, revision `physical-practice-1`.

- **83 Python tests passed.** The existing sound comparison/API suite passed.
- **Five JavaScript check groups passed:** WAV/levels, recording diagnosis, lip
  geometry, starting-category movement planning, and reference comparison.
- **Six browser check groups passed:** teaching guides, simple word practice,
  lip references, microphone gain/playback, recording-specific feedback, and the
  new physical/prosody practice flow.
- The recording-feedback browser check included an existing teacher-commented
  development recording through the real local speech service. Other specified
  UI cases used synthetic microphone input or mocked model results.
- Desktop and 390-pixel mobile views were reviewed. All four phrase topics fit
  without horizontal overflow. Selected controls remain readable on hover.
- Phrase practice verified meaning choices, rise/fall gesture changes, reduced
  motion, recording and playback of two clips, rolling replacement of older clips,
  microphone-permission failure recovery, and navigation locking during capture.
  Phrase clips made no POST request to the word-recognition endpoint.
- The new sound movement planner verified use of a supported observed category,
  conditional wording for weak evidence, equivalent-shape handling and labeled
  fallback demonstrations. Full sound activities remain optional and target
  reference diagrams remain open by default.

Results and screenshots are in `data/results/physical_practice/`. Earlier browser
reports remain in `data/results/discovery_guides/`, `simple_practice/`,
`lip_reference_checks/`, `microphone_level_checks/`, and `recording_diagnosis/`.

These checks establish software behavior, not recognition accuracy or learning
effectiveness. Phrase stress, pitch and meaning are not automatically assessed.
No physical microphone, paid app account, course enrollment or learner trial was
used for this verification. The Python suite reports an existing dependency
deprecation warning; no test failures remained.

Research and remaining work: [Product study](PRONUNCIATION_PRODUCT_STUDY.md).
