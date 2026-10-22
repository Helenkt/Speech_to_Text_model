# Source-Grounded Course Grading

This backend addition does not change the UI, model weights, approved rubric
revisions, question-bank files, or production database. No external knowledge
is downloaded and no training is performed.

## Runtime

- `rubric_guidance.py` derives per-criterion source quotes, compound-claim
  warnings, critical literals and bounded equivalent-expression examples.
- Teacher tooling retains these hints. The runtime judge receives compact rubric
  points and exact student clauses, not duplicated references/guidance that caused
  the 3B judge to conflate criteria. Complex assertion scopes retain the full raw
  transcript too. Course terminology still comes only from supplied sources.
- The teacher rubric GET endpoint includes the same guidance. It remains a draft,
  not automatic teacher approval or a new requirement to review practice answers.
- `course_verifier.py` compares closed assertions against the actual criterion.
  It handles access order, both stack operations, inheritance direction, subclass
  extension permission, bounded NULL definitions/check predicates, primary-key
  nullability and parameter-update direction. It compares against the supplied
  criterion, not a cached correct answer. A changed source value changes the check.
- An implicit order description can use the question's subject only when the
  question, criteria and answer mention a single unambiguous structure. A closed
  absence is final only when every candidate clause is accounted for as another
  parsed fact or an explicit abstention. Unparsed text disables this shortcut.
- These are deliberately narrow grammars, not general natural-language parsers.
  Arbitrary SQL/code is never executed. Complex conditions, rejected quotations,
  corrections, unsupported wording and compound criteria still need the existing
  semantic evaluation path. Recognized inconsistent assertions stay unresolved.
- Each rule decision retains the original evidence, criterion quote and rule ID.
  Backend rubric weights still determine points.

## Evidence And Uncertainty

- The judge restates required/student meanings separately before choosing a label.
  Generated restatements are explanations only, never replacement transcripts.
- A model's self-reported confidence is uncalibrated metadata, not an accuracy
  estimate or a blanket reason to erase independently correct criteria.
- Exact evidence IDs remain mandatory. An invalid missing-with-evidence label is
  isolated to that criterion and gets at most one repair within the existing time
  budget. Duplicate points, invented IDs and malformed JSON remain rejected.
- The NLI evidence check honors its saved calibration threshold. Neutral/weak
  evidence means unresolved, not a final wrong answer. Unverified partial credit
  is not automatically converted into half the criterion weight.
- If the secondary judge fails, pending Transformer guesses are marked unresolved;
  an unverified 100-point proposal is not substituted for a verified grade.
- Practice excludes unresolved results from final scores. This is a safety fix,
  not evidence that the general-purpose grader is sufficiently accurate. The live
  rehearsal still exposes substantial abstention outside the closed grammars.

## Preparation

Run from the project directory with a NEW output directory:

```powershell
.\.test-venv\Scripts\python.exe -B -m tools.prepare_course_grading --output data/course_grading_checks/new-run
```

Use `.venv` instead of `.test-venv` on an ordinary installation.

Outputs:

- `rubric_drafts.json`: source-bound drafts for the two supplied banks; existing
  criteria and weights are preserved, not automatically split or published.
- `contrastive_cases.jsonl`: complete, missing, negated, inconsistent, corrected
  and applicable equivalent-answer cases derived from the four supplied course
  reference datasets. Every source file has a SHA-256 recorded.
- `rule_regressions.json`: rule-only behavior checks, including abstentions and
  deferred semantic cases; no STT or LLM inference.
- `manifest.json`: counts, provenance and limitations.

Variants from one source question remain in one preparation split. Original
sources may overlap earlier training. Generated labels are not independently
teacher-validated student answers and must not be reported as held-out product
accuracy. Do not automatically merge them into training or calibrate a claim of
real student accuracy from them. Save an independent evaluation set before any
future training and measure the deployed INT8 model again after export.

No additional large model is required on a student's computer. Closed rules
can avoid inference for covered criteria. Hardware latency and real grading accuracy require
separate measurements.
