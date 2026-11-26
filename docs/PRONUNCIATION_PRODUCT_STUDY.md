# WordSpeak: pronunciation teaching, product direction and business test

Research reviewed 18 November 2026. This document distinguishes published
features, WordSpeak design decisions, and hypotheses that still need testing.

## Recommendation

Build a short physical coaching loop for Vietnamese learners: notice what the
recording suggests, compare a starting reference with a target, explore one small
change, then use it to convey meaning. Aim for comfortable understanding in
conversation. A sound recognizer and a set of diagrams alone are insufficient.

Start with teachers and small classes already accessible to the project. They
can review feedback, choose useful practice and help establish learning value.
This is a proposed initial market, not evidence of demand or revenue.

## What was studied, and what was not

The linked [IH London course](https://teacherportal.ihlondon.com/course/teach-pronunciation-adrian-underhill)
advertises ten hours of study, including three hours of video/audio. Its lesson
content requires sign-in. I reviewed the public page, not the gated lessons, and
did not complete the course. The accessible research below uses Underhill's own
published articles, his British Council articles, and Macmillan's official series
description. The linked video playlist could not be retrieved here; the videos
have not been claimed as watched or analysed frame by frame.

Competitor findings come from public official product pages, not paid-account
usability testing. Advertised capabilities, download totals, testimonials and
subscription availability do not establish learning effectiveness or profitability.
No competitor's finances were verified.

## Underhill: principles and their product consequences

| Principle from primary material | WordSpeak application | Avoid |
|---|---|---|
| Awareness of lips, tongue, jaw and voice; related sounds form a system [U1] | Show a small physical contrast with a nearby sound; keep all available targets accessible | Treating every sound as an unrelated diagram or equating unrounded lips with a forced grin |
| Mime can direct attention to movement before a spoken model; inner rehearsal is useful [U2] | An optional silent movement preview and a brief invitation to imagine the sound before speaking | A compulsory checklist before every recording; presenting a schematic animation as human mime |
| Find the starting sound, then demonstrate movement toward the target; each attempt should inform the next [U3] | When supported, base the illustration on the model's observed category and give one adjustment; compare recordings | Always playing the same generic transition after different errors, or retrying solely to raise a score |
| Word stress and unstress differ from the prominence a speaker chooses for meaning [U4] | Contrast light/full syllables, then let the learner change the prominent word to express an intention | Reducing stress to loudness; judging every alternative focus pattern as an error |
| Sounds operate inside words and connected speech [U5] | Carry practice into a useful phrase, including linking and light syllables | Requiring mastery of ten isolated sounds before allowing connected speech |
| The broader goal is comfortable intelligibility [U6] | Judge whether listeners understand intended words and meaning with reasonable effort | Selling accent removal or treating one accent as the only acceptable identity |

These are original WordSpeak adaptations. This study does not establish that
Underhill or IH London has reviewed, licensed or endorsed the app. His existing
work also means that physical pronunciation teaching is not a new invention by
WordSpeak.

## What established products offer

| Product and public evidence | Useful pattern to borrow | WordSpeak adjustment or design risk |
|---|---|---|
| **ELSA Speak** advertises feedback on sounds, stress and intonation [C1]; its subscription page describes personalized paths, multiple accent options and bilingual explanations [C2] | Give a short next practice based on a specific difficulty; explain cues in language learners understand | A score needs calibration and a clear interpretation. We have not verified ELSA's recognition accuracy, and WordSpeak must not imply equal capability |
| **BoldVoice** describes expert-coach video lessons alongside immediate sound-level AI feedback and a personalized plan [C3] | Show an actual movement or coaching demonstration alongside feedback | Original teacher-recorded front/side clips would add information our schematic art cannot convey. A video plus AI alone would not differentiate us |
| **Speechling** describes listening, recording and human coaching, including rhythm and intonation [C4]; its pricing page includes voice comparison and an audio journal [C5] | Let learners compare attempts and allow teacher review of uncertain feedback | Human review has a staffing cost. Do not promise unlimited teacher service without measuring that cost |
| **Macmillan Sounds / Sound Foundations**: Macmillan explicitly identifies its pronunciation app as inspired by Underhill [U7] | Treat the sound map as a tool for exploration and relationships | An Underhill-inspired app is not a unique claim. Current distribution/maintenance of the old Sounds app was not verified |

The final column records our design judgments. It is not a claim that these
products have the stated problems. Public pages support feature comparisons;
they do not establish which product teaches best.

## Changes applied to this local demo

**Sounds** retains recording-specific feedback and both reference diagrams. Its
Watch movement action now opens a compact silent demonstration without opening
the longer lesson. For supported vowel and fricative contrasts it uses the
suggested starting category, rather than always using the lesson's fixed anchor.
Weak candidates keep conditional wording. Equivalent illustrated shapes, such as
unmarked /i/ and /iː/, produce a target-pose demonstration without inventing a
shape correction or a vowel-length diagnosis. Stop/release examples remain
explicitly target demonstrations where interpolation would mislead.

**Words & meaning** adds four selectable micro-activities:

- Word stress: a light first syllable and a fuller second syllable in about.
- Sentence focus: move prominence between YOU and THINK in What do you think?
- Intonation: explore possible rising and falling readings of Really for two
  stated intentions. These are contextual possibilities, not rules that every
  question rises or every statement falls.
- Connected speech: use take a seat as one phrase, with a light a and a focus on
  seat.

Each offers one main cue, a reference gesture, optional silent rehearsal, local
recording, and playback of the two latest attempts for that topic. Learners
choose when to retry. The lines and beats are examples, not acoustic traces.
Phrase clips stay in the tab; there is no phrase-level AI assessment or progress
grade. Refreshing or leaving the page clears these recordings.

This is an initial application of the principles, not a complete digital version
of the method. Human demonstrations, guided listening, a broader sound map,
teacher review and validated phrase analysis remain gaps. The ten-sound
recognizer's accuracy has not improved merely because the teaching flow changed.

## How learners and teachers could benefit

| Intended benefit | Mechanism in the product | Evidence needed |
|---|---|---|
| A learner knows what to change | Recording-specific hypothesis, starting/target references and one cue | Teacher agreement with the identified category and the suitability of the cue |
| Practice feels manageable | One attempt is useful; extra exploration is optional | Completion, observed confusion and learner interviews, including beginners |
| A change transfers beyond a drill | Apply it in a phrase with an intended meaning | Listener understanding on unfamiliar words and spontaneous speech |
| Learners hear their own development | Compare attempts and state what changed | Retained improvement after a delay; self-observation alone is not proof |
| Teachers use time more effectively | Proposed review of uncertain or persistent cases | Actual teacher minutes per learner and agreement that review is useful |

These are mechanisms and hypotheses. Functional tests do not establish these
benefits. A [systematic review of computer-assisted pronunciation training][R1]
distinguishes perception from production and controlled features from broader
speech outcomes; its findings support evaluating more than a drill score. It is
background evidence, not validation of our app or of this exact adaptation.

## Revenue and profitability

The paying value would be dependable practice between lessons, clear correction,
and evidence that the practice helps. Pictures, IPA labels and an unsupported
percentage are weak reasons for an ongoing subscription.

Proposed first route: a teacher or language centre pilots a class pack. Include
assignable practice and a bounded review workflow only after those features exist.
Later, consider individual subscriptions with personalized review and optional
paid human feedback. The present demo has no billing, teacher dashboard or
validated automated prosody grading; these are product directions.

No price has been validated. The following is arithmetic with deliberately
explicit assumptions, not a forecast or a recommended market price:

- Assumed subscription: **99,000 VND per paying active learner per month**.
- Assumed fixed monthly costs: **15,000,000 VND**, a placeholder for a real budget.
- Variable cost must include inference, storage, payment fees, support and any
  human review allocated per user. Acquisition, refunds, tax and missing staff
  costs also need to be included in the eventual business budget.

| Assumed variable cost / learner / month | Contribution / learner / month | Paying users to cover the assumed fixed costs |
|---:|---:|---:|
| 25,000 VND | 74,000 VND | 203 |
| 55,000 VND | 44,000 VND | 341 |
| 85,000 VND | 14,000 VND | 1,072 |

Contribution = price minus variable cost. Illustrative break-even users = round
up(fixed cost / contribution). This is operating break-even under the stated
assumptions, before the additional items above. It is not evidence of profit.
High manual-review rates, weak retention or acquisition costs could make this
unviable. Measure cost per usable feedback event, not just cost per request;
an uncertain result can still consume compute and support time.

Our possible differentiation is an easy physical correction loop, adapted to
specific learners and integrated with a teacher. That is currently a hypothesis.
It becomes defensible through reviewed content, reliable feedback and learning
evidence, not through calling the app AI-powered or associating it with a famous
teacher.

## Validation before expanding or charging

1. **Diagnosis and cue review.** Use existing consented project recordings and
   clearly specified tasks. Have a teacher label sound categories and whether a
   correction is justified without seeing model outputs first. Split by speaker;
   report per-contrast coverage, agreement, misleading corrections and abstentions.
   Do not count uncertain results as correct. Freeze thresholds before evaluation.
2. **Usability pilot.** Recruit, with the team's authorization, roughly 10–15
   learners. Observe one attempt without explanation. Record time to first useful
   attempt, retries, confusion, abandonment and perceived usefulness. These numbers
   would be exploratory, not a powered learning trial.
3. **Learning pilot.** Compare the physical-cue flow with a simpler reference and
   playback flow using equivalent time and tasks. Pre-test, post-test and delayed
   test (for example after one week), including unfamiliar items and a short
   communicative task. Use listeners blind to group/time, transcription for word
   understanding, meaning identification for focus/intonation, and ease-of-
   understanding ratings. Counterbalance practice materials and analyse by learner.
4. **Business pilot.** Ask teachers/centres what problem they would pay to solve;
   test a concrete offer rather than a hypothetical liking question. Track return
   use, human-review time, actual compute, support and payment costs. Set a price
   only after this evidence. No outreach, enrollment or charging has been done.

Priority after this implementation: validate diagnosis and obtain reviewed human
models for the small set of contrasts. Phrase-level automatic feedback needs its
own alignment, voiced-pitch/energy/duration measurements, task definitions and
evaluation. A rising pitch trace by itself cannot judge a speaker's intention.

## Sources

- [U1: Underhill, physical awareness and muscle controls](https://adrianunderhill.com/2012/05/29/making-pronunciation-physical-finding-the-%E2%80%98muscle-buttons%E2%80%99/)
- [U2: Underhill, mime and the voice control](https://adrianpronchart.wordpress.com/2012/02/29/the-story-of-sounds-episode-9-further-discoveries-using-the-voice-button/)
- [U3: Underhill, physicality, iteration and integration](https://oxfordtefl.com/blog/my-top-ten-pronunciation-tips-physicality-and-integration-by-adrian-underhill/)
- [U4: Underhill, word stress and prominence](https://adrianunderhill.com/2012/06/07/sentence-stress-prominence-and-word-stress/)
- [U5: Underhill for the British Council, core chart activities](https://www.teachingenglish.org.uk/professional-development/teachers/knowing-subject/core-pronunciation-activities-using-phonemic)
- [U6: Underhill, comfortable intelligibility](https://adrianunderhill.com/2015/11/09/comfortable-intelligibility-pronunciation/)
- [U7: Macmillan, official pronunciation series and Sounds app context](https://www.macmillanenglish.com/us/blog-resources/articles/article/pronunciation-skills-videos)
- [C1: ELSA, pronunciation feedback](https://elsaspeak.com/en/faqs/how-does-elsas-pronunciation-feedback-work)
- [C2: ELSA, subscriptions and advertised features](https://elsaspeak.com/en/elsa-subscription)
- [C3: BoldVoice, product and coaching](https://boldvoice.com/)
- [C4: Speechling, learning and coaching workflow](https://speechling.com/)
- [C5: Speechling, plans and voice comparison](https://speechling.com/pricing)

[R1]: https://www.cambridge.org/core/journals/recall/article/computerassisted-pronunciation-training-a-systematic-review/71E786F7DFC99727837909FDED7A2320
