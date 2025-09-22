Name: **Symphonic Compression**

Essence: compress elapsed read time without losing meaning or safety. Code plays as one coherent movement. Every token earns its place.

# First principles

* **Semantic economy:** one concept per name. No synonyms. Vocabulary is small and exact.
* **Intent-first grammar:** verbs do work, nouns hold state, adjectives qualify constraints. Booleans read as claims.
* **Explicit boundaries:** pure computation centered; I/O, time, and randomness at the edges and named as such.
* **Predictable rhythm:** straight-line flow dominates; branches announce purpose; early exits end phrases cleanly.
* **Cognitive budget:** ≤ one new idea per visual block. Depth beats breadth. Indentation ≤ three levels.
* **Invariants in code:** preconditions, postconditions, and units encoded in types and guards, not prose.
* **Reversible structure:** small parts compose and can be inlined or extracted without ripple.
* **Temporal compression:** fewer passes over data; eliminate gratuitous waits; batch intent, not accidents.
* **Stable lexicon:** domain terms are governed; names are contracts; renames track concept changes.
* **Truthful errors:** messages state fact, expected state, and delta; no stories.
* **Observability as metronome:** logs and metrics mark tempo—cause, effect, duration—without narration.
* **Consistency over cleverness:** the same idea looks the same everywhere.

# Practitioner’s guide (Python ≥3.11)

* **Surface design**

  * Public API reads as a table of contents. Hide mechanics; expose purpose and contracts.
  * Keep parameter lists short; bundle configuration when meaning improves.
  * Prefer total ordering of names inside a module: inputs → transforms → outputs.

* **Naming discipline**

  * Encode units and ranges in names when ambiguity risks bugs (`*_usd_cents`, `ratio_0to1`).
  * Ban placeholders (`data`, `tmp`, `process`). Use role-precise stems.

* **Flow and form**

  * One operation per function. If the name needs “and,” split.
  * Replace boolean soup with small, named predicates.
  * Use pattern matching where it clarifies intent, not as a puzzle.

* **Data shapes**

  * Choose the simplest structure that preserves meaning. Prefer typed records for fixed schemas.
  * Make shape discovery trivial with explicit schema helpers where external data enters.

* **Boundaries and effects**

  * Isolate time, I/O, and concurrency behind narrow seams. Pure core stays testable and fast.
  * Make side effects visible in names (`emit_`, `persist_`, `fetch_`, `cache_`).

* **Contracts and safety**

  * Types on all public surfaces; assertions for programmer errors; guarded failures for user errors.
  * Idempotence is a property, not a parameter. Either guaranteed or not.

* **Rhythm of concurrency**

  * Concurrency serves clarity and latency, not fashion. Group independent work; avoid shared mutable state.
  * Bound parallelism explicitly; prefer backpressure over queues without limits.

* **Error cadence**

  * Fail fast at boundaries; recover where intent is clear. No silent retries without budget and reason.
  * Propagate causes intact; add context, do not replace.

* **Testing as score**

  * Tests narrate behavior, not internals. Unit tests prove laws; integration tests prove wiring.
  * Property tests guard invariants; example tests document typical paths.
  * One assertion concept per test to keep tempo steady.

* **Documentation minimalism**

  * Let names and types carry most meaning. Comments justify rule-bending and document non-obvious constraints only.
  * Keep a living lexicon; link code to terms instead of re-explaining.

* **Measurement and guardrails**

  * Track function size, nesting, fan-out, and churn; cap by policy.
  * Track hot paths’ wall time and allocation; compress where it moves user time.
  * Enforce uniform formatting and import order to remove visual noise.

* **Evolution**

  * Change in concept → change in name. Preserve compatibility via adapters, not overloaded meanings.
  * Remove abstractions that do not pay rent. Addition by subtraction is progress.

Goal: music without filler. Read once, understand once, execute fast.

