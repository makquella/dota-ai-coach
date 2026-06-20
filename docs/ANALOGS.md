# Analogues and Differentiation

## Purpose

Dota AI Coach is not intended to replace commercial assistants, replay/statistics platforms, generic AI chatbots, or human coaching. It is a coursework MVP focused on a narrow technical question: how to build a safe local real-time coaching assistant from official Dota 2 Game State Integration data.

The project uses deterministic live logic, small overlay messages, and conservative scheduling. Optional LLM support is limited to wording and review workflows; it does not own live authority.

## Comparison Criteria

| Solution / category | Main purpose | Data source | Real-time capability | Safety / integration model | Limitations for this coursework goal | Difference of Dota AI Coach |
|---|---|---|---|---|---|---|
| Dota Plus / built-in assistant | First-party player assistance, progression, statistics, and in-game quality-of-life features. | Valve game client and Valve-controlled services. | Yes, but within Valve's own feature set. | Fully integrated by the game developer. | Closed implementation; not suitable as a coursework architecture to inspect, extend, or evaluate locally. | Provides an educational open local architecture around GSI, rule-based decisions, scheduler behavior, and reproducible tests. |
| Overwolf-style overlay apps | Companion overlays for stats, draft help, match tracking, and game-adjacent utilities. | App-specific sources such as public profile data, platform APIs, user notes, and sometimes GSI-style telemetry. | Often yes, depending on app and game support. | Third-party overlay platform with its own app runtime and store model. | Broader product scope; may depend on external platforms or account/profile data rather than a minimal local backend. | Runs locally as a coursework system and focuses on safe carry advice from local GSI/replay states rather than broad companion-app features. |
| GameLeap-like educational coaching platforms | Structured learning content, guides, videos, and coaching-style education. | Human-created educational material and public game knowledge. | Mostly not real-time during a match; learning usually happens before or after play. | Content platform, not a local telemetry pipeline. | Does not demonstrate live state parsing, scheduler design, local overlay integration, or session recording. | Implements a real-time assistant loop and post-session summaries based on advice actually produced by the backend. |
| Dotabuff / OpenDota-style statistics and replay analysis | Match history, hero statistics, public data analysis, and replay-derived insights. | Public match data, APIs, parsed replay data, and user-exposed match history. | Mainly post-match or external analysis; not a compact live overlay coach. | Web/API services outside the live game client. | Strong for analytics, but not focused on live low-distraction advice from current GSI state. | Uses local live GSI and replay-derived GSI-like states to test the same advice path used by the overlay. |
| Generic LLM chatbot | General conversation, explanation, brainstorming, and natural-language help. | User prompts and any provided context. | Interactive, but not automatically grounded in live Dota 2 telemetry unless a separate integration is built. | General-purpose AI assistant; correctness depends on prompt/context. | May hallucinate unavailable game facts and does not provide deterministic scheduling or safety gating by itself. | Uses LLM only optionally for wording/review while local rule-based policy controls live decisions, priority, and timing. |
| This project: Dota AI Coach | Coursework MVP for safe real-time carry-oriented Dota 2 advice. | Official Dota 2 GSI, replay-derived GSI-like states, local hero profiles, and local session history. | Yes for live GSI; also supports offline replay/demo playback. | Local FastAPI backend plus Electron launcher/overlay; no game-process hooks or automated input. | Limited GSI visibility, limited hero-specific rules, no full packaged installer validation yet, and no human-level coaching. | Demonstrates the complete local architecture: telemetry intake, normalization, deterministic advice, anti-spam scheduling, overlay display, recording, tests, and replay evaluation. |

## Key Differentiation

Dota AI Coach is different from the compared systems because it:

- uses official Dota 2 Game State Integration as the live input path;
- works locally through a FastAPI backend and Electron apps;
- does not inspect game process memory;
- does not analyze screen pixels;
- does not automate keyboard or mouse input;
- uses deterministic rule-based logic for live advice;
- uses optional LLM support only for wording and review, not live authority;
- focuses on short carry-oriented safety and farming recommendations;
- records live sessions for evaluation;
- includes replay/demo playback for reproducible defense demos;
- has documented live GSI validation and automated tests.

## Honest Limitations

The project has important limitations:

- GSI visibility is limited.
- Exact enemy positions are unavailable.
- Exact team readiness is unavailable.
- Exact teamfight and Roshan/objective context are unavailable.
- The assistant does not provide human-level strategic coaching.
- The final packaged Windows portable build still needs full clean-machine validation.
- Hero-specific rules and profiles are limited.
- Replay-derived GSI-like states are useful for testing but are not identical to live GSI.

These limitations are handled by conservative wording and by avoiding claims that require missing signals.

## Coursework Value

The project is academically useful because it demonstrates:

- architecture of a real-time game assistant;
- safe integration with official game telemetry;
- normalized state modeling;
- deterministic rule-based decision making;
- anti-spam scheduling and game-time spacing;
- live session recording and reproducible evaluation;
- offline replay/demo workflows;
- a separation between local safety policy and optional LLM wording;
- tests and documentation suitable for coursework defense.

## Sources

Lightweight public references used for the comparison:

- Dota Plus official page: <https://www.dota2.com/plus>
- Dota Plus Steam Support FAQ: <https://help.steampowered.com/en/faqs/view/2FED-F8AA-46FD-5094>
- Overwolf Dota 2 apps: <https://www.overwolf.com/browse-by-game/dota2>
- GameLeap Dota 2 page: <https://www.gameleap.com/dota-2>
- Dotabuff: <https://www.dotabuff.com/>
- OpenDota: <https://www.opendota.com/>
- OpenDota API docs: <https://docs.opendota.com/>
- OpenAI ChatGPT capabilities overview: <https://help.openai.com/en/articles/9260256-chatgpt-capabilities-overview>
