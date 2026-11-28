# NeuraXAi — Task List (Stages 4–8)

Roadmap, decisions and risks: `tasks/plan.md`. D-numbers (D1…D13) refer to the defect table there. Stages 9–20 are roadmap-only until Checkpoint E.

Common commands (Windows PowerShell, from the repo root, venv active):

```powershell
python -m unittest discover -s tests -v     # tests
python -c "import app"                      # import/"build" check
python app.py                               # run → http://127.0.0.1:5000  (Ollama must be running)
```

Sizes: XS 1 file · S 1–2 · M 3–5 · L 5–8 (split further).

---

## Stage 4 — v0.4.0: Intelligence & stability

Completion condition (team roadmap): existing features work, memory-OFF tests pass, and the app doesn't crash when Ollama is offline.

### [ ] Task 1: Reproducible baseline, characterization tests, CI
**Status:** reviewed (PR #2). Real chat turn verified during the Task 5 review (`NEURAXAI_MODEL=qwen3.5:4b`, `/chat` → 200 with a model reply). Open: a green CI run on GitHub.
**Description:** Get v0.3.0 running, pin dependencies, and add a test harness that locks in current behaviour (known bugs marked as expected failures) so later refactors are safe.
**Acceptance criteria:**
- [x] Fresh clone + `python -m venv .venv` + `pip install -r requirements.txt` + `python app.py` serves the page and answers one real chat turn.
- [x] `tests/` has Flask test-client tests for `GET /` (200) and the "hi" shortcut (reply text, no Ollama call).
- [x] Known bugs D1, D2, D3 each have a test marked `@unittest.expectedFailure` naming the task that fixes it.
- [x] `requirements.txt` pins compatible ranges (`flask>=3.0,<4`, `requests>=2.31,<3`).
- [ ] GitHub Actions runs the unittest command on push/PR (Ubuntu + Windows, Python 3.10 + 3.12).
**Verification:**
- [x] Tests pass: `python -m unittest discover -s tests -v` (expected failures reported as such, not errors).
- [x] Build succeeds: `python -c "import app"`.
- [ ] Manual: CI run on GitHub is green.
**Dependencies:** None
**Files likely touched:** `requirements.txt`, `tests/__init__.py`, `tests/test_baseline.py`, `.github/workflows/ci.yml`
**Estimated scope:** Small–Medium (4 files)

### [x] Task 2: Storage that cannot lose or corrupt memory (D1, D6)
**Description:** Make `core/memory.py` safe: path anchored to the project (not cwd), auto-create `data/`, validate structure, serialize access with a lock, write atomically, and back up an unreadable file instead of silently replacing it. Keep it lean: Stage 5 replaces this storage with SQLite.
**Acceptance criteria:**
- [x] Saving on a fresh clone (no `data/`) succeeds, and the file is created next to the project regardless of cwd.
- [x] Two threads calling `save_message` 100 times each yield exactly 200 history entries.
- [x] A corrupt `memory.json` is renamed to `memory.json.corrupt-<timestamp>` and a fresh structure is used; the original bytes are preserved.
- [x] Writes use temp file + `os.replace`; a simulated exception between write and replace leaves the old file intact.
- [x] D1 expected-failure test passes and its decorator is removed.
**Verification:**
- [x] Tests pass: `python -m unittest tests.test_memory -v`
- [x] Manual: delete `data/`, send a message, restart the app, confirm history is still used. (Reviewed via two separate processes started outside the repo; app-level check repeats at Checkpoint A.)
**Dependencies:** Task 1
**Files likely touched:** `core/memory.py`, `tests/test_memory.py`, `tests/test_baseline.py`
**Estimated scope:** Small (3 files)

### [ ] Task 3: Memory toggle works end to end (D3)
**Description:** Every memory read and write in `/chat` honours the `memory` flag, and the UI exposes it as a switch. Memory OFF means: no history in the prompt, no saved-name lookup, no writes. It does not delete stored data.
**Acceptance criteria:**
- [ ] With `memory:false`, "what is my name" does not return the stored name and nothing is written to disk.
- [ ] With `memory:true`, the stored name is returned and the turn is saved.
- [ ] The page has a "Memory" switch (default ON, persisted in `localStorage`) sent as `memory` in every `/chat` request.
- [ ] Non-boolean `memory` values are rejected (the 400 response is wired in Task 7; the type check lives here).
- [ ] D3 expected-failure test passes and is un-marked.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_memory_toggle -v` (assert file contents unchanged when off).
- [ ] Manual: set name with memory ON, switch OFF, ask name → "I don't know."; switch ON → name returned.
**Dependencies:** Task 2
**Files likely touched:** `app.py`, `web/templates/index.html`, `web/static/app.js`, `web/static/style.css`, `tests/test_memory_toggle.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 4: Name capture that doesn't corrupt facts (D2)
**Description:** Create `core/intent.py` with `extract_name(text) -> str | None`. Only explicit phrases count ("my name is …", "call me …", Roman Telugu "naa peru …"); capture multi-word names; "I am a student" must never touch the saved name. When memory is OFF, say the name wasn't saved.
**Acceptance criteria:**
- [ ] `extract_name("My name is Alex Kumar")` → `"Alex Kumar"`; `"call me Sam"` → `"Sam"`.
- [ ] `"I am a student"`, `"I am tired"`, `"My name is"` (empty) → `None`.
- [ ] Trailing punctuation is trimmed; over-long input (>60 chars or >4 words) is rejected.
- [ ] `/chat` saves the name only when memory is ON; the reply differs when OFF.
- [ ] D2 expected-failure test passes and is un-marked.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_intent -v` (table-driven, at least 12 cases).
- [ ] Manual: "I am a student" after setting a name → name unchanged.
**Dependencies:** Task 2, Task 3
**Files likely touched:** `core/intent.py`, `app.py`, `tests/test_intent.py`
**Estimated scope:** Small (3 files)

### [ ] Task 5: Config module for model and runtime settings
**Status:** reviewed. Timeouts, max message length and debug are defined but not wired yet; Tasks 6 and 7 use them.
**Description:** Move hard-coded settings into `core/config.py`, read from environment variables with safe defaults: `NEURAXAI_MODEL` (default `phi3:mini`), `OLLAMA_URL`, connect/read timeouts, temperature, max message length, `NEURAXAI_DEBUG`, data directory. Other modules import from it instead of defining constants.
**Acceptance criteria:**
- [x] No module other than `core/config.py` contains the model name, Ollama URL or data path as a literal.
- [x] Invalid values (e.g. non-numeric timeout) fall back to the default with a logged warning, not a crash.
- [x] Tests can override settings without touching environment variables globally (e.g. a `Settings` object or patchable attributes).
- [x] README documents every variable.
**Verification:**
- [x] Tests pass: `python -m unittest tests.test_config -v`
- [x] Manual: `$env:NEURAXAI_MODEL = "qwen3.5:4b"; python app.py` uses that model.
**Dependencies:** Task 1
**Files likely touched:** `core/config.py`, `core/llm.py`, `core/memory.py`, `tests/test_config.py`, `README.md`
**Estimated scope:** Medium (5 files)

### [ ] Task 6: Ollama client hardening with visible errors (D4, D5, D12)
**Description:** Rewrite `core/llm.py` so failures are explicit and Stop actually stops generation: timeouts from config, status check, handling of `{"error": ...}` lines, and closing the upstream response when the consumer disconnects. The route pulls the first chunk before replying, so "Ollama offline" and "model not found" become a 503 JSON body that the UI shows.
**Status:** reviewed. Manual checks ran on the merged code with qwen3.5:4b. Ollama unreachable (closed port) → 503, and the UI showed the message. A normal turn worked. An uninstalled model gave the `ollama pull` hint. Aborting mid-answer closed the Ollama connection within 1s (checked with `netstat`; `ollama ps` lists loaded models, not active generations). Requests send `think: false`; without it, Stop during a thinking model's reasoning didn't stop Ollama. Open: confirm a non-thinking model (e.g. `phi3:mini`) still answers with `think: false`.
**Acceptance criteria:**
- [x] Ollama not running → `/chat` returns 503 `{"error": "Ollama is not reachable at …"}`; the app keeps running and the UI shows the message.
- [x] Unknown model → error naming the model, with the hint `ollama pull <model>`.
- [x] Closing the generator (client abort) closes the `requests` response (test with a fake response recording `.close()`).
- [x] `app.js` checks `response.ok`, reads the JSON error and renders it.
**Verification:**
- [x] Tests pass: `python -m unittest tests.test_llm -v` (mock `requests.post`: connection error, HTTP 404, error line mid-stream, normal stream, close-on-abort).
- [x] Manual: stop Ollama → message → readable error; start Ollama → works; Stop mid-answer → `ollama ps` shows generation ended.
**Dependencies:** Task 5
**Files likely touched:** `core/llm.py`, `app.py`, `web/static/app.js`, `tests/test_llm.py`
**Estimated scope:** Medium (4 files)

### [ ] Task 7: Request validation and server hardening (D7, D8)
**Description:** `/chat` rejects bad input with 4xx instead of 500, request size is capped, debug mode is opt-in, and the server binds explicitly to localhost.
**Acceptance criteria:**
- [ ] Non-JSON body → 400/415 JSON error; JSON that isn't an object → 400; non-string `message` → 400; empty/whitespace message → 400.
- [ ] `message` over the configured limit → 413 or 400; `MAX_CONTENT_LENGTH` set.
- [ ] `app.run(host="127.0.0.1", debug=<config>)`, debug off by default.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_validation -v`
- [ ] Manual: `Invoke-RestMethod -Uri http://127.0.0.1:5000/chat -Method Post -ContentType 'application/json' -Body '{"message":123}'` → 400.
**Dependencies:** Task 6 (shared error shape)
**Files likely touched:** `app.py`, `tests/test_validation.py`
**Estimated scope:** Small (2 files)

### [ ] Task 8: Language detection (English, Telugu, Roman Telugu)
**Description:** Move detection into `core/language.py`. Keep the Telugu Unicode check; add keyword/pattern heuristics for Roman Telugu ("naa peru enti", "ante enti", …). Be conservative: unknown or short text → English.
**Acceptance criteria:**
- [ ] `"తెలుగులో చెప్పు"` → telugu; `"Python ante enti?"` → telugu (romanized); `"What is Python?"` → english; `""` → english.
- [ ] A single ambiguous word that is both English and a Telugu keyword (listed in the module docstring) doesn't flip the language on its own.
- [ ] `app.py` imports from `core.language`; the old regex is removed.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_language -v` (≥15 table cases incl. the README example prompts).
**Dependencies:** Task 1
**Files likely touched:** `core/language.py`, `app.py`, `tests/test_language.py`
**Estimated scope:** Small (3 files)

### [ ] Task 9: Deterministic intents: greetings, thanks, bye, identity (D9)
**Description:** Extend `core/intent.py` with `classify(text, language) -> Intent` for no-LLM replies: greetings (case/punctuation tolerant, good morning/night), thanks, farewell, identity ("who are you", "what is your name" → always NeuraXAi), "what is my name". Replies in English and Telugu. `chat()` dispatches on the result.
**Acceptance criteria:**
- [ ] "Hi!", "HELLO", "good morning", "thanks", "bye", "good night", "who are you" resolve without calling the LLM (mock asserts `ask_llm_stream` not called).
- [ ] "high school" and "hello world program in python" do **not** match the greeting shortcut.
- [ ] Shortcut replies are saved to history when memory is ON, and not when OFF.
- [ ] `chat()` in `app.py` is under ~60 lines afterwards.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_intent tests.test_chat_routes -v`
- [ ] Manual: greeting/thanks/bye/identity prompts reply instantly in both languages.
**Dependencies:** Task 4, Task 8
**Files likely touched:** `core/intent.py`, `app.py`, `tests/test_intent.py`, `tests/test_chat_routes.py`
**Estimated scope:** Medium (4 files)

### [ ] Task 10: Prompt builder with dynamic response length (D10)
**Description:** Replace the inline f-string with a pure `build_prompt(user_msg, language, style, facts, history)` in `core/prompt.py`. Separate `KNOWN FACTS` from `RECENT CONVERSATION`; choose response length from the question (brief default, "in detail", bullets, paragraph); add uncertainty guidance; keep the NeuraXAi identity rules.
**Acceptance criteria:**
- [ ] "Explain Python in detail" drops the "Maximum 3 lines" rule; "in bullet points" keeps the 5-bullet rule; default stays brief.
- [ ] The stored name appears under facts only when memory is ON and a name exists; memory OFF → no facts and no history in the prompt.
- [ ] A user message containing "Assistant:" or "FORMAT RULES:" can't be mistaken for prompt structure (test with an injection string).
- [ ] `build_prompt` does no I/O.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_prompt -v`
- [ ] Manual: run the README example prompts against Ollama; note results for Checkpoint A.
**Dependencies:** Task 3, Task 8, Task 9
**Files likely touched:** `core/prompt.py`, `app.py`, `tests/test_prompt.py`
**Estimated scope:** Small (3 files)

### [ ] Task 11: Safe streaming renderer, stop and error states (D11, D12)
**Description:** Replace the regex-to-HTML `formatAIResponse` with DOM construction: text via `textContent`, fenced code as `<pre><code>` with a Copy button attached by `addEventListener`. Handle an unclosed fence while streaming; Stop, finish and error states reset the button correctly.
**Acceptance criteria:**
- [ ] A reply containing `<img src=x onerror=alert(1)>` or `<script>` renders as visible text; no `innerHTML` with model text anywhere.
- [ ] Fenced code renders with working Copy; a half-streamed fence doesn't break layout.
- [ ] Stop → button back to ➤, "Generation stopped" shown, next message works.
- [ ] HTTP/network errors render as a styled error bubble.
**Verification:**
- [ ] Tests pass: Python suite still green.
- [ ] Manual checklist: XSS payload; long code block copy; stop then send again; Ollama offline; Telugu text; autoscroll on long replies.
**Dependencies:** Task 6
**Files likely touched:** `web/static/app.js`, `web/static/style.css`
**Estimated scope:** Small (2 files)

### ◆ Checkpoint A: v0.4.0 (after Tasks 1–11)
- [ ] All tests green locally and in CI; consider adding Ruff and Bandit to CI here.
- [ ] README manual acceptance checklist ticked on the target laptop with real Ollama.
- [ ] `data/` auto-created on a fresh clone; memory survives restart; memory OFF writes nothing; Ollama offline doesn't crash the app.
- [ ] README updated to match the files actually in the repo; 20-stage roadmap replaces the old 12-stage table.
- [ ] Tag `v0.4.0`. **Review before Stage 5/6.**

---

## Stage 5 — v0.5.0: Advanced memory system

Expected result (team roadmap): personal information persists across restarts, and the user has full control over their memory. Multiple profiles are deferred (see `plan.md`).

### [ ] Task 12: SQLite storage with one-time JSON migration
**Description:** Add `core/db.py` (stdlib `sqlite3`) with tables for sessions, messages and facts. Re-implement the memory functions on top of it, keeping their names. On first start, if `memory.json` exists and the DB is new, import it into a default session and keep the original as `memory.json.bak`.
**Acceptance criteria:**
- [ ] Fresh start creates the DB and schema (versioned with `PRAGMA user_version`).
- [ ] A fixture `memory.json` imports completely and idempotently (running twice doesn't duplicate).
- [ ] All Stage 4 memory tests pass unchanged against the SQLite backend.
- [ ] `data/*.db*` is gitignored.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_db tests.test_memory -v`
- [ ] Manual: upgrade a v0.4.0 install with real history; history intact and `.bak` exists.
**Dependencies:** Checkpoint A
**Files likely touched:** `core/db.py`, `core/memory.py`, `.gitignore`, `tests/test_db.py`, `tests/fixtures/memory_v1.json`
**Estimated scope:** Medium (5 files)

### [ ] Task 13: Chat sessions
**Description:** Separate conversations. Endpoints `GET/POST /sessions`, `DELETE /sessions/<id>`, `GET /sessions/<id>/messages`; `/chat` takes `session_id`; history is scoped per session; the page gets a sidebar with "New chat" and the session list.
**Acceptance criteria:**
- [ ] A new chat starts with empty context; switching sessions loads that session's messages and only its history goes into the prompt.
- [ ] Session title defaults to the first user message (truncated).
- [ ] Deleting a session removes its messages; facts remain. Unknown `session_id` → 404 JSON.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_sessions -v`
- [ ] Manual: two sessions with different topics don't leak context; reload restores the last session.
**Dependencies:** Task 12
**Files likely touched:** `app.py`, `core/memory.py`, `web/templates/index.html`, `web/static/app.js`, `web/static/style.css`
**Estimated scope:** Medium (5 files)

### [ ] Task 14: Structured facts and memory commands
**Description:** Facts get categories (name, preference, skill, hobby, goal, project) and support multiple values. Deterministic commands handle them without guessing: "Remember that I know Python and Flask", "My goal is to become an AI Engineer", "What skills do I have?", "Remove cricket from my hobbies", "Show all my saved memories".
**Acceptance criteria:**
- [ ] Each example command above produces the right add/list/remove operation (table-driven parser tests).
- [ ] Adding a duplicate value doesn't create a second row; removing a value that doesn't exist says so.
- [ ] Facts are injected into the prompt by category only when memory is ON.
- [ ] Commands are refused with a clear message when memory is OFF.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_fact_commands -v`
- [ ] Manual: run the five example commands in order; restart; "Show all my saved memories" lists the right facts.
**Dependencies:** Task 12
**Files likely touched:** `core/facts.py`, `core/intent.py`, `core/db.py`, `app.py`, `tests/test_fact_commands.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 15: Memory dashboard
**Description:** A "Memory" panel in the page: list facts by category, edit, delete one, and "Delete all memory" with a confirm step. Backend `GET/PUT/DELETE /facts` and `DELETE /memory`.
**Acceptance criteria:**
- [ ] Editing the name in the panel changes what "what is my name" returns.
- [ ] "Delete all memory" removes facts, messages and sessions after a confirmation, and leaves the app in a clean state.
- [ ] Memory switch semantics unchanged (OFF doesn't read or write).
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_facts_api -v`
- [ ] Manual: edit, delete, wipe all; confirm the DB rows are gone.
**Dependencies:** Task 13 (UI shell), Task 14
**Files likely touched:** `app.py`, `web/templates/index.html`, `web/static/app.js`, `web/static/style.css`, `tests/test_facts_api.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 16: Conversation search (FTS5)
**Description:** Full-text search over past messages using an SQLite FTS5 table kept in sync with `messages`. `GET /search?q=` returns matches with session title, snippet and date; the sidebar gets a search box that opens the matching session.
**Acceptance criteria:**
- [ ] Searching a word from an old session returns that session with a highlighted snippet.
- [ ] Deleted sessions/messages don't appear in results.
- [ ] Search input is passed as a bound parameter; FTS syntax errors return an empty result, not a 500.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_search -v`
- [ ] Manual: search for a topic from yesterday's chat and jump to it.
**Dependencies:** Task 13
**Files likely touched:** `core/db.py`, `app.py`, `web/static/app.js`, `tests/test_search.py`
**Estimated scope:** Medium (4 files)

### [ ] Task 17: Memory export and import
**Description:** Back up and restore all memory as one JSON file: `GET /memory/export` downloads it; `POST /memory/import` restores it, with a preview of counts and a choice of merge or replace.
**Acceptance criteria:**
- [ ] Export → wipe → import restores identical facts, sessions and messages (round-trip test).
- [ ] Malformed or wrong-version files are rejected with a clear error and change nothing.
- [ ] Replace requires confirmation in the UI.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_export_import -v`
- [ ] Manual: export, delete all memory, import, confirm everything is back.
**Dependencies:** Task 12 (Task 15 for the UI buttons)
**Files likely touched:** `core/backup.py`, `app.py`, `web/static/app.js`, `tests/test_export_import.py`
**Estimated scope:** Medium (4 files)

### [ ] Task 18: `/api/chat` messages and context budget
**Description:** Call Ollama `/api/chat` with a `system` message and role-tagged history instead of one concatenated prompt. Add a context budget that trims the oldest turns first, always keeping the system message, facts and the latest user turn.
**Acceptance criteria:**
- [ ] Payload is `messages=[system, …history…, user]`; `build_prompt` becomes `build_messages` with its tests updated.
- [ ] A 200-message session never exceeds the configured budget; the newest turns survive.
- [ ] README example prompts follow format and language rules at least as well as before (before/after notes for Checkpoint B).
- [ ] Task 6 error handling and abort-closing still work.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_prompt tests.test_llm -v`
- [ ] Manual: 30-turn conversation without Ollama context errors.
**Dependencies:** Task 13, Task 10
**Files likely touched:** `core/llm.py`, `core/prompt.py`, `app.py`, `tests/test_prompt.py`, `tests/test_llm.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 19: Rolling summary of old turns
**Description:** Short-term memory for long chats. When a session exceeds the budget, summarize the oldest turns with the local model (non-streaming call), store the summary on the session, and include it as a "Conversation so far" block.
**Acceptance criteria:**
- [ ] A summary is generated only when the threshold is crossed, stored, and reused rather than regenerated every turn.
- [ ] If summarization fails, chat still works using plain trimming.
- [ ] The summary is deleted with its session; memory OFF never reads or writes it.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_summary -v` (mock the summarizer).
- [ ] Manual: long conversation; ask about something from the start; check the stored summary.
**Dependencies:** Task 18
**Files likely touched:** `core/summary.py`, `core/memory.py`, `app.py`, `tests/test_summary.py`
**Estimated scope:** Small–Medium (4 files)

### [ ] Task 20: Suggested memories with user approval
**Description:** Memory extraction from natural language. After a turn, the model may propose facts as JSON ("skill: Python"); the UI shows them as a "Save to memory?" chip, and nothing is stored until the user approves.
**Acceptance criteria:**
- [ ] No fact is written without an explicit approve action (test).
- [ ] Malformed model output is ignored silently (no error shown, nothing saved).
- [ ] Proposals that duplicate existing facts aren't shown.
- [ ] Off when memory is OFF; can be disabled separately in settings.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_suggested_memories -v` (mock the model).
- [ ] Manual: say "I've been learning Docker" → chip appears → approve → fact listed in dashboard.
**Dependencies:** Task 14, Task 15, Task 18
**Files likely touched:** `core/facts.py`, `app.py`, `web/static/app.js`, `tests/test_suggested_memories.py`
**Estimated scope:** Medium (4 files)

### ◆ Checkpoint B: v0.5.0
- [ ] Upgrade from a real v0.4.0 `memory.json` verified on the laptop; `.bak` exists.
- [ ] The five Stage 5 example commands work after a restart.
- [ ] Sessions, search, dashboard, export/import and the memory switch work together; wipe-all leaves no data.
- [ ] Tag `v0.5.0`.

---

## Stage 6 — v0.6.0: Multi-model AI engine

Expected result (team roadmap): changing the model requires no changes in the rest of the application. Tasks 21 and 25 can start right after Checkpoint A, in parallel with Stage 5.

### [ ] Task 21: Evaluation prompt set and runner
**Description:** A fixed set of ~30 prompts in `eval/prompts.jsonl` (English, Telugu, Roman Telugu, format requests, identity, code, "I don't know" cases) with simple automatic checks per prompt (language script, bullet count, line count, banned phrases, identity). `python -m eval.run --model <tag>` writes a results file with pass rate and latency. Runs against live Ollama; not part of CI.
**Acceptance criteria:**
- [ ] Each prompt has at least one automatic check; the runner prints pass rate per category and median latency.
- [ ] Results are saved as `eval/results/<model>-<date>.json` (gitignored except a committed baseline).
- [ ] A baseline result exists for at least two installed models.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_eval_checks -v` (checks themselves are unit-tested).
- [ ] Manual: run against two models and compare.
**Dependencies:** Checkpoint A
**Files likely touched:** `eval/prompts.jsonl`, `eval/checks.py`, `eval/run.py`, `tests/test_eval_checks.py`
**Estimated scope:** Medium (4 files)

### [ ] Task 22: Engine abstraction
**Description:** `engines/base.py` defines the interface (`chat_stream(messages, options)`, `health()`, `list_models()`); `engines/ollama_engine.py` moves the Task 18 client behind it. `app.py` and summarization use the engine, never `requests` directly. No behaviour change.
**Acceptance criteria:**
- [ ] No module outside `engines/` imports `requests` to talk to a model.
- [ ] A fake engine in tests can replace Ollama for every route test.
- [ ] All existing tests pass unchanged.
**Verification:**
- [ ] Tests pass: full suite.
- [ ] Manual: chat works as before.
**Dependencies:** Task 18
**Files likely touched:** `engines/__init__.py`, `engines/base.py`, `engines/ollama_engine.py`, `app.py`, `core/summary.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 23: Model registry and model selector
**Description:** `engines/model_registry.py` lists configured models with purpose tags, context size and default options (temperature, max tokens), merged with what Ollama reports as installed. `GET /models` feeds a model dropdown in the UI; the chosen model is sent per request.
**Acceptance criteria:**
- [ ] The dropdown lists only installed models; the choice persists across reloads.
- [ ] Per-model options from the registry are applied to requests.
- [ ] Requesting a model that isn't installed → clear 400 error.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_model_registry -v`
- [ ] Manual: switch between two installed models mid-session.
**Dependencies:** Task 22
**Files likely touched:** `engines/model_registry.py`, `app.py`, `web/static/app.js`, `web/templates/index.html`, `tests/test_model_registry.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 24: Model health check and fallback
**Description:** Health check on start and on demand (`GET /health`: Ollama reachable, selected model installed). If the primary model fails before its first token, retry once with the configured fallback model and tell the user which model answered.
**Acceptance criteria:**
- [ ] Primary model missing → reply comes from the fallback, with a visible note.
- [ ] Both fail → the Task 6 error, not a crash.
- [ ] Fallback never triggers after streaming has started (no mixed answers).
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_fallback -v` (fake engine).
- [ ] Manual: set the primary to an uninstalled tag; chat still works.
**Dependencies:** Task 23
**Files likely touched:** `engines/model_router.py`, `app.py`, `web/static/app.js`, `tests/test_fallback.py`
**Estimated scope:** Medium (4 files)

### [ ] Task 25: Hardware detection and model recommendation
**Description:** `engines/hardware.py` reports CPU, RAM and GPU (via `psutil`; NVIDIA VRAM via `nvidia-smi` when present) and recommends which registry models fit. Shown in a small "System" section of the model selector.
**Acceptance criteria:**
- [ ] Works with no GPU (reports "CPU only") and never crashes when `nvidia-smi` is missing.
- [ ] Models whose size exceeds available memory are marked "may be slow".
- [ ] Adds only `psutil` to `requirements.txt`.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_hardware -v` (mocked readings).
- [ ] Manual: numbers match Task Manager on the laptop.
**Dependencies:** Checkpoint A (Task 23 for the UI)
**Files likely touched:** `engines/hardware.py`, `app.py`, `requirements.txt`, `tests/test_hardware.py`
**Estimated scope:** Small–Medium (4 files)

### [ ] Task 26: Performance tracking
**Description:** Record per request: model, time to first token, total time, tokens/second (from Ollama's response stats), success/failure. Stored in SQLite; `GET /stats` returns per-model medians. This is the data Stage 19 builds on.
**Acceptance criteria:**
- [ ] Every chat request writes one stats row, including failures.
- [ ] Stats contain no message text (privacy).
- [ ] `/stats` shows median first-token and total time per model.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_stats -v`
- [ ] Manual: ten chats on two models; compare in `/stats`.
**Dependencies:** Task 22, Task 12
**Files likely touched:** `engines/metrics.py`, `core/db.py`, `app.py`, `tests/test_stats.py`
**Estimated scope:** Medium (4 files)

### [ ] Task 27: Rule-based model routing
**Description:** Pick a model per request from simple rules: code requests → coding model, Telugu → the best-scoring multilingual model, default → general model. Rules and model choices come from Task 21 eval results and Task 26 latency, not guesses. The user's manual choice always wins.
**Acceptance criteria:**
- [ ] Routing rules live in config, each with a comment citing the eval result that justifies it.
- [ ] Manual model selection overrides routing.
- [ ] Eval pass rate with routing on is ≥ the best single model's pass rate.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_routing -v`
- [ ] Manual: run the eval with routing on vs off; record both.
**Dependencies:** Task 21, Task 23, Task 26
**Files likely touched:** `engines/model_router.py`, `core/config.py`, `tests/test_routing.py`
**Estimated scope:** Small (3 files)

### ◆ Checkpoint C: v0.6.0
- [ ] Changing the default model needs only a config change (verified by switching on the laptop).
- [ ] Eval results for each registered model committed as the baseline.
- [ ] Tag `v0.6.0`.

---

## Stage 7 — v0.7.0: Intent routing & tool calling

Expected result (team roadmap): calculations, dates and similar tasks are answered by real Python functions, not model guesses. The safety core comes first.

### [ ] Task 28: Safety core (tiers, path allowlist, audit log, approval gate)
**Description:** `safety/` with: policy tiers T0 read-only, T1 low-risk reversible, T2 sensitive, T3 blocked; a path validator that only allows configured folders (resolving symlinks and `..`); an audit log of every attempted action (allowed or not); and an approval gate that blocks T2 actions until the user confirms in the UI.
**Acceptance criteria:**
- [ ] `..\..\Windows`, absolute paths outside the allowlist, symlinks pointing outside, and UNC paths are all rejected (test list).
- [ ] T3 actions are denied even with an approval flag.
- [ ] T2 actions stay pending until approved; a denied or expired approval does nothing.
- [ ] Every decision is written to the audit log with time, tool, arguments and outcome.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_safety -v` (adversarial path list included).
- [ ] Manual: audit log readable via `GET /audit`.
**Dependencies:** Checkpoint B, Checkpoint C
**Files likely touched:** `safety/policy.py`, `safety/paths.py`, `safety/audit.py`, `safety/approval.py`, `tests/test_safety.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 29: Tool registry, executor, calculator
**Description:** `tools/registry.py` describes each tool in MCP's shape (name, description, JSON Schema input, safety tier). `tools/executor.py` validates arguments, checks the policy, applies timeout and a max-calls-per-turn limit, and logs to the audit log. First tool: a calculator using an AST evaluator (no `eval`). "Calculate 25% of 15000" → 3750.
**Acceptance criteria:**
- [ ] Calculator handles `+ - * / ** %`, percentages and parentheses; rejects names, calls, attributes, huge exponents (`9**9**9`) and division by zero without crashing.
- [ ] A tool that exceeds its timeout is stopped and reported.
- [ ] Tool output goes into the prompt as labelled untrusted data.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_tools tests.test_calculator -v`
- [ ] Manual: "Calculate 25% of 15000" → 3750; "calculate __import__('os')" → refused.
**Dependencies:** Task 28
**Files likely touched:** `tools/registry.py`, `tools/executor.py`, `tools/calculator.py`, `app.py`, `tests/test_tools.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 30: Date, time, time zone and unit tools with deterministic routing
**Description:** Read-only tools for date, time, time in a city ("What time is it in London?" via `zoneinfo`) and unit conversion ("Convert 10 km to miles"). A deterministic router in `core/router.py` maps matching phrases (English and Telugu) to tools before any model call.
**Acceptance criteria:**
- [ ] The four example commands answer from tools, not the model (mock asserts no model call for the tool result).
- [ ] Unknown city or unit → clear message, not a guess.
- [ ] Router never calls a tool that isn't registered or whose arguments fail validation.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_router tests.test_time_tools -v`
- [ ] Manual: run the four examples plus Telugu equivalents.
**Dependencies:** Task 29
**Files likely touched:** `tools/datetime_tool.py`, `tools/units.py`, `core/router.py`, `tests/test_router.py`, `tests/test_time_tools.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 31: System info, approved-folder listing, text tools
**Description:** "Show my laptop RAM" (from Task 25's hardware module), "Show files in the approved folder" (T0, through the Task 28 path validator) and text tools (word/line count on pasted text or an approved file).
**Acceptance criteria:**
- [ ] File listing only works inside allowlisted folders and never follows links outside them.
- [ ] Listing large folders is capped (e.g. 200 entries) with a "more" note.
- [ ] All three tools are T0 and appear in the audit log.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_system_file_tools -v` (temp dirs + escape attempts).
- [ ] Manual: list an approved folder; try a non-approved one → refused.
**Dependencies:** Task 29
**Files likely touched:** `tools/system_info.py`, `tools/files.py`, `tools/text_tools.py`, `tests/test_system_file_tools.py`
**Estimated scope:** Medium (4 files)

### [ ] Task 32: Model-proposed tool calls (behind a flag)
**Description:** For requests the deterministic router doesn't match, let the model propose a tool call as constrained JSON (Ollama `format`), validate it against the registry schema, execute through the executor, and return the result to the model for the final answer. Off by default; enabled per model only if the eval shows it works.
**Acceptance criteria:**
- [ ] Malformed JSON, unknown tools or invalid arguments fall back to a normal chat reply (tests with junk outputs).
- [ ] At most N tool calls per turn; all go through policy and audit.
- [ ] Tool-selection accuracy on ≥20 scripted prompts is recorded per model in `eval/results/`.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_model_tool_calls -v`
- [ ] Manual: run the tool-selection eval on two models; decide the default for the flag.
**Dependencies:** Task 21, Task 30
**Files likely touched:** `core/router.py`, `tools/executor.py`, `eval/prompts_tools.jsonl`, `tests/test_model_tool_calls.py`
**Estimated scope:** Medium (4 files)

### ◆ Checkpoint D: v0.7.0
- [ ] Security pass: no tool runs without the policy check; path escapes rejected; T3 always blocked; audit log complete.
- [ ] Every Stage 7 example command answered by a tool, verified on the laptop.
- [ ] Tag `v0.7.0`.

---

## Stage 8 — v0.8.0: PDF, Excel & file processing

Expected result: simple PDF-to-Excel and data-cleaning tasks work locally. OCR, invoice extraction and batch processing move to Stage 16. Client data needs the client's permission, and outputs need manual accuracy checks.

### [ ] Task 33: Upload endpoint with CSV/TXT extraction
**Description:** An upload button, `POST /upload` saving to a sandboxed `data/uploads/` (inside the Task 28 allowlist), with type and size limits, then CSV/TXT extraction as T0 tools. "Summarize this file" sends capped extracted text to the model as untrusted data.
**Acceptance criteria:**
- [ ] Only allowed types accepted; max size enforced; filenames sanitized; `../` names rejected.
- [ ] Extracted text is capped by the context budget; uploads are gitignored and deletable in the UI.
- [ ] A fixture file containing "ignore previous instructions…" doesn't change identity rules (best-effort test on the built messages).
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_upload -v`
- [ ] Manual: upload a CSV and ask for a summary.
**Dependencies:** Checkpoint D
**Files likely touched:** `app.py`, `core/files.py`, `tools/extractors.py`, `web/static/app.js`, `tests/test_upload.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 34: PDF, XLSX and DOCX extraction
**Description:** Add extractors using `pypdf`, `openpyxl` and `python-docx`. Encrypted, corrupt or scanned (image-only) files return a clear message instead of an error.
**Acceptance criteria:**
- [ ] Sample PDF, XLSX and DOCX fixtures extract the expected text.
- [ ] An image-only PDF reports "no text found (scanned? OCR comes in Stage 16)".
- [ ] Adds only `pypdf`, `openpyxl`, `python-docx`.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_extractors -v`
- [ ] Manual: one real file of each type.
**Dependencies:** Task 33
**Files likely touched:** `tools/extractors.py`, `requirements.txt`, `tests/test_extractors.py`, `tests/fixtures/*`
**Estimated scope:** Small–Medium (3 files + fixtures)

### [ ] Task 35: PDF tables to Excel, with downloads
**Description:** "Convert this PDF into Excel": extract tables with `pdfplumber`, write them to an XLSX (one sheet per table), and offer it for download from `data/outputs/`. A short report lists tables found and row counts so the user can check accuracy.
**Acceptance criteria:**
- [ ] A fixture PDF with two tables produces an XLSX with two sheets whose cells match the expected values.
- [ ] Generated files are only served from `data/outputs/` and can be deleted.
- [ ] PDFs with no tables say so instead of producing an empty file.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_pdf_tables -v`
- [ ] Manual: convert a real invoice-style PDF and compare cells by eye.
**Dependencies:** Task 34
**Files likely touched:** `tools/pdf_tables.py`, `app.py`, `web/static/app.js`, `requirements.txt`, `tests/test_pdf_tables.py`
**Estimated scope:** Medium (5 files)

### [ ] Task 36: Data cleaning for CSV/XLSX
**Description:** "Remove duplicate rows from this spreadsheet": remove empty rows and exact duplicates (optionally by chosen columns), write a cleaned copy, and report what changed. The original is never modified.
**Acceptance criteria:**
- [ ] Fixture with known duplicates and blanks → cleaned output with the exact expected rows; report counts match.
- [ ] The original file is byte-identical after cleaning.
- [ ] Works for both CSV and XLSX.
**Verification:**
- [ ] Tests pass: `python -m unittest tests.test_cleaning -v`
- [ ] Manual: clean a real spreadsheet and check the report.
**Dependencies:** Task 34
**Files likely touched:** `tools/cleaning.py`, `app.py`, `tests/test_cleaning.py`
**Estimated scope:** Small (3 files)

### ◆ Checkpoint E: v0.8.0
- [ ] Each Stage 8 example command works on real files on the laptop, with outputs checked by hand.
- [ ] Uploads and outputs can't escape their folders; all file tools appear in the audit log.
- [ ] Tag `v0.8.0`. **Break down Stage 9 (RAG) into tasks, using the eval and performance data collected so far.**
