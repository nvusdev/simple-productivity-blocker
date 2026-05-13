---
trigger: always_on
---

# kluster Code Verification Rules

## Snapshot Session (kluster_open_snapshot_session)

* **PURPOSE**: Start a fresh workspace snapshot so all subsequent changes are verified against the current state.
* **WHEN TO RUN**:

  * Immediately after receiving **every** user request in the chat (each turn).
  * Always **before** generating or editing any code or files.
* **ORDERING**:

  * Must be the **first** kluster call in the turn.
* **MANDATORY**: Even if the upcoming change is small (e.g., a single line or minor edit), this step **must still run**.
* **DO NOT**: produce any code output prior to running `kluster_open_snapshot_session`.

## Automatic Code Review (kluster_code_review_auto)

* **WHEN TO RUN**: Execute after **any** file creation, modification, or code change, regardless of size or perceived triviality.

  * **Run ONCE per turn, after the final edit** to cover the **entire diff set** for that turn. Do **not** run per file.
  * If `agent_todo_list` requires additional edits, apply them and **re-run once** after those edits until zero actionable items remain.
  * Includes:

    * New code generation
    * Existing code updates
    * File modifications or changes
    * File creation
    * Applied fixes
  * Applies to **all file types**, not just code files.
* **REQUIREMENTS**: Follow `kluster_code_review_auto` field descriptions strictly.
* **MANDATORY ENFORCEMENT**:

  * This tool **must always run** whenever the agent writes, edits, or modifies code in any way.
  * Agents are **not permitted** to skip verification for small edits or one-line changes.
  * If any code output is generated without a corresponding **post-edit** `kluster_code_review_auto` call (covering all changes in the turn), the workflow is **invalid**.

## Manual Code Review (kluster_code_review_manual)

* **WHEN TO RUN**: Only when explicitly requested by user.
* **TRIGGER PHRASES**:

  * "verify with kluster"
  * "verify this file"
  * "verify project"
  * "check for bugs"
  * "check security"
  * Similar manual verification requests.

## Dependency Validation (kluster_dependency_check)

* **WHEN TO RUN**: Before any package management operation.

  * Adding new packages or libraries.
  * Running package managers (npm, gradle, pip, etc.).
  * Generating or updating package list files (e.g., `package.json`, `requirements.txt`).

## Agent Todo List Management

* **EXECUTION**: Always execute and strictly follow `agent_todo_list` from any kluster tool response.
* **COMPLETION**: Do not stop until all items in `agent_todo_list` are completed.
* **WORKFLOW**: Complete all fixes from `agent_todo_list` before running `kluster_code_review_auto` again.

## Chat ID Management

* **FIRST CALL**: Do not include `chat_id` field for the very first kluster tool call in a conversation.
* **SUBSEQUENT CALLS**: MANDATORY — Always include `chat_id` field with the **exact value** returned by any previous kluster tool call in the same conversation.
* **SESSION TRACKING**:

  * The `chat_id` maintains context across all kluster calls — failure to include it breaks the verification chain.
* **IMPLEMENTATION**:

  * After receiving any kluster tool response, immediately note the `chat_id` value.
  * Include this `chat_id` in **all** subsequent kluster tool calls.
  * Never generate or modify the `chat_id` value — always reuse the returned value.
* **APPLIES TO**: All kluster tools (`kluster_code_review_auto`, `kluster_code_review_manual`, `kluster_dependency_check`).
* **CRITICAL**: Missing `chat_id` on subsequent calls creates new isolated sessions instead of maintaining context.
* **ENFORCEMENT**: Every kluster tool call after the first **must include** `chat_id` parameter.

## End of Chat Session — kluster Summary

* **WHEN TO EXECUTE**: MANDATORY at the end of **any** conversation where kluster tools were used, right before the final user-facing response — **EXCEPT when Clarification Handling is active** (see "Clarification Handling" section). If any kluster response in the current turn contains "CLARIFICATION:" actions, do NOT generate this summary — show the clarification prompt instead.
* **TRIGGER**: If any `kluster_code_review_auto`, `kluster_code_review_manual`, or `kluster_dependency_check` tools were called during the conversation AND no "CLARIFICATION:" actions are present in any response, always generate this summary.

### KLUSTER SUMMARY STRUCTURE

Generate short report from all kluster tool calls throughout the conversation:

#### **📋 kluster feedback**

Summarize all issues found across all kluster tool calls:

* Number of issues found in total, grouped by severity.
* Short summary (1–2 lines) of what was detected.
* For case when kluster returned "includedExternalKnowledge" data - include short summary from "includedExternalKnowledge" field on what knowledge sources were used during code review. This should be displayed at the END of the kluster summary section, after all other sections, as a separate line formatted as: "📚 External knowledge used: [short summary of includedExternalKnowledge]"

#### **✅ Issues found and fixed**

If any issues were found and fixed:

* Summarize what fixes were implemented (1–2 lines).
* Add impact statement:

  * **⚠️ Impact Assessment:** Explain briefly what could have happened without these fixes.

### Formatting

* Use `<h1>` title: `🔍 kluster.ai Review Summary:`
* Include minimal emoji and bullet points for clarity.
* Reflect the **entire verification journey**, not just the final state.

### ENFORCEMENT

* If any kluster tools were used AND no clarifications were requested, a final kluster summary **must** be provided.
* If clarification is present, show ONLY the clarification prompt — these two are mutually exclusive. Omitting the summary (when no clarification is needed) is a **rule violation**.

---

### 🔒 Enforcement Addendum: No Code Without Verification

To guarantee full compliance:

* **Every time** an agent produces any code output — no matter how small — it must perform the following sequence **in this exact order**:

  1. **Run `kluster_open_snapshot_session`** (first call of the turn).
  2. **Generate or modify the code**.
  3. **Immediately run `kluster_code_review_auto`**.
* Agents **must not** decide autonomously to skip verification for any reason, including perceived triviality or time‑saving.
* This applies equally to **single‑line edits**, **pseudocode**, **documentation changes**, **config edits**, **renames/moves**, and **minor syntax corrections**.

---

## 🚦 Compliance Gate (MUST PASS BEFORE ANY CODE OUTPUT)

Agents **must not** send code to the user unless all of the following are true for the **current turn**:

1. A successful `kluster_open_snapshot_session` has been executed in this turn.
2. A **single** `kluster_code_review_auto` run has been executed **after the final edit** in this turn, and it **covers the full set of changed files**.
3. All items from the latest `agent_todo_list` are completed (or explicitly marked N/A by the tool) **before** presenting code.
4. The agent has prepared a **Verification Receipt** (see below) for the response.

If any item is false, the agent must **pause code output**, run the required kluster tool(s), complete the todo items, and only then continue.

---

## 🧾 Verification Receipt (REQUIRED IN EVERY CODE RESPONSE)

Append the following minimal receipt **after** your code blocks:

```
<!-- KLUSTER_VERIFICATION_RECEIPT
turn: <current turn index or timestamp>
chat_id: <exact chat_id from the last kluster tool response>
snapshot: <ISO timestamp of kluster_open_snapshot_session>
review: <ISO timestamp of kluster_code_review_auto>
files_verified: ["<path1>", "<path2>", ...]
issues_found: { critical: <n>, high: <n>, medium: <n>, low: <n> }
status: VERIFIED
-->
```

* Omit no fields. Use the **exact** `chat_id` returned by kluster.
* If no files were changed, do **not** produce code; instead, state: *“No code changes; verification not required.”*

> **Note:** This receipt is part of the assistant’s response (HTML comment) so it is visible to Windsurf automations but unobtrusive to users.

---

## 🔁 Multi‑Edit Within a Single Turn

* If the agent makes **multiple edits** within one turn, it must run **one** `kluster_open_snapshot_session` (first) and **one** `kluster_code_review_auto` **after the last edit** *and* after completing all todos.
* If `kluster_code_review_auto` returns additional todos that require further edits, complete them, then **re‑run** `kluster_code_review_auto` until zero actionable items remain.

---

## 🧪 Dependency Gate

* Any change to package manifests/lockfiles or commands that imply package operations **must** precede with `kluster_dependency_check`.
* If `kluster_dependency_check` returns todos, complete them **before** `kluster_code_review_auto`.

---

## ✅ End‑of‑Turn Summary is Mandatory

* If **any** kluster tool ran in the conversation, include the **`🔍 kluster.ai Review Summary:`** section before the final user‑facing message of that turn.
* If code was produced without tools in the same turn, treat as violation: trigger **Non‑Compliance Auto‑Recovery Flow**, then produce the summary.

---

## 🧷 Edge Cases (Treat as Code Changes)

* Comment‑only edits, formatting, lint fixes, README/Markdown, YAML/TOML/JSON, env files, build scripts, GitHub Actions, Dockerfiles, CI configs, and file renames/moves all **require** verification.

---

## 💡 Example (Happy Path)

1. `kluster_open_snapshot_session`
2. Agent writes code (no user‑visible output yet).
3. `kluster_code_review_auto` → returns todos.
4. Agent applies all todos (edits code).
5. `kluster_code_review_auto` (again) → zero todos.
6. Agent outputs code **plus** the **Verification Receipt**.

## Pause / Resume kluster Reviews (kluster_review_pause)
- **WHEN TO RUN**: When the user explicitly asks to pause, stop, disable, snooze, or resume/enable/unpause kluster reviews
- **TRIGGER PHRASES (pause)**:
  - "pause kluster"
  - "stop kluster"
  - "disable kluster"
  - "snooze kluster"
  - "turn off kluster"
  - "hold kluster reviews"
  - Similar requests to temporarily stop automated reviews
- **TRIGGER PHRASES (resume)**:
  - "resume kluster"
  - "enable kluster"
  - "unpause kluster"
  - "turn on kluster"
  - "start kluster again"
  - Similar requests to re-enable automated reviews
- **BEHAVIOR**:
  - `action: "pause"` — suspends all automated kluster code reviews for the current project for 1 hour
  - `action: "resume"` — re-enables kluster code reviews immediately
- **SCOPE**: Pause/resume applies ONLY to the current project
- **CRITICAL - DO NOT MODIFY FILES**: When the user asks to pause or disable kluster, you MUST call the `kluster_review_pause` tool with `action: "pause"`. NEVER attempt to pause kluster by deleting, editing, renaming, or removing any rules files, configuration files, or .md files. The pause is controlled exclusively through the `kluster_review_pause` tool call — not through filesystem changes.
- **CRITICAL - DO NOT SKIP THE TOOL CALL**: "Pausing kluster" does NOT mean ignoring kluster rules or pretending kluster doesn't exist. It means calling `kluster_review_pause` with the appropriate action.
- **WHILE PAUSED**: When kluster is paused, do NOT run `kluster_code_review_auto` on file changes. Once resumed (either manually via `action: "resume"` or automatically after 1 hour), resume normal `kluster_code_review_auto` behavior.
- **ANNOUNCEMENT**: When calling this tool, say "Pausing kluster reviews..." or "Resuming kluster reviews..." as appropriate. NEVER say you are pausing by modifying files.