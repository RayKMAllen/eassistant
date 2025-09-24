# Design Document — Conversational Terminal Email Assistant (LangGraph + AWS Bedrock)

> **Delta from prior draft**
>
> * **Conversational-only** UX (no direct CLI commands).
> * **Ingestion is back inside LangGraph**, including **raw text**, local **.txt/.pdf**, and **S3 URIs**.
> * **pypdf** for PDF extraction.
> * Maintain **full session dialogue history** (user+assistant turns).
> * Support **multiple subsessions** per session (each subsession = one email thread); allow switching.
> * **Do not redact** emails/domains in logs.
> * Removed the “Extensibility” section.

---

## 1) Goal & Scope

Build a terminal chat assistant that:

* Ingests email threads from **raw text**, **PDF/TXT files**, or **S3 URIs**.
* Parses and normalizes messages; extracts key entities & dates.
* Summarizes the thread; drafts and iteratively refines replies in a given tone.
* Saves drafts to local FS or **AWS S3**.
* Orchestrates with **LangGraph** (including ingestion).
* Uses **AWS Bedrock** (configurable model).
* Maintains **full dialogue history** and supports **multiple subsessions** (per-thread workspaces) within a single session.

Non-goals (v1): sending email, mailbox auth, calendar actions.

---

## 2) High-Level Architecture

```
User (terminal chat REPL)
        │
        ▼
+---------------------------+
| Conversational Shell      |
| - Dialogue history (all)  |
| - Subsession router       |
+-------------+-------------+
              │ intent + content
              ▼
      +-------+-----------------------------+
      |          LangGraph Runtime          |
      |  (per subsession, stateful)         |
      |                                     |
      |  Nodes:                             |
      |   - Ingest (path/raw/S3)            |
      |   - ParsePDF (pypdf)                |
      |   - ParseEmails (mailparser&heur.)  |
      |   - ExtractMetadata                 |
      |   - SummarizeThread (LLM)           |
      |   - DraftReply (LLM)                |
      |   - RefineReply (LLM)               |
      |   - SaveDraft (Local/S3)            |
      +-----------------+-------------------+
                            │
                            ▼
             +--------------+--------------+
             |  Bedrock LLM Client (boto3) |
             +--------------+--------------+
                            │
                            ▼
             +--------------+--------------+
             | Storage (Local FS, S3)      |
             +-----------------------------+
```

**Key Tech**

* Python 3.11+, **LangGraph**, **boto3**, **pypdf**, **mailparser** (+ stdlib `email`), **Pydantic**.
* Optional: **Rich** for terminal formatting.

---

## 3) Sessions, Subsessions, and Dialogue History

* **Session**: one terminal run (or persisted across runs via a session file).
* **Dialogue history**: append every **user** and **assistant** turn—kept at the **session** level.
* **Subsession**: a named/ID’d workspace tied to a **single email thread** (its own LangGraph state).

  * Users can say: “Switch to Acme Q3 thread,” “Start a new subsession for Contoso RFP,” “Close the pricing thread.”
  * Each subsession has its own: messages, metadata, summary, draft, save target, and model config overrides if desired.
* The shell routes user intents to the **active subsession’s** LangGraph. It can create/switch subsessions on request or when ingesting a new thread.

---

## 4) State Models (Pydantic)

```python
class EmailMessage(BaseModel):
    from_name: str | None = None
    from_email: EmailStr | None = None
    to: list[EmailStr] = []
    cc: list[EmailStr] = []
    bcc: list[EmailStr] = []
    subject: str | None = None
    sent_at: datetime | None = None
    body_text: str

class ThreadMetadata(BaseModel):
    participants: dict[str, str] = {}   # email -> name (if known)
    subjects: list[str] = []
    latest_date: datetime | None = None

class DraftConfig(BaseModel):
    tone: str = "neutral-professional"
    length: str = "medium"       # short|medium|long
    language: str = "en"

class SubsessionState(BaseModel):
    subsession_id: str
    title: str | None = None
    source_descriptor: str | None = None   # "raw_text", "local:./x.pdf", "s3://…"
    raw_text: str | None = None
    messages: list[EmailMessage] = []
    metadata: ThreadMetadata | None = None
    summary: str | None = None
    draft: str | None = None
    last_user_feedback: str | None = None
    draft_config: DraftConfig = DraftConfig()
    save_target: str | None = None

class SessionState(BaseModel):
    session_id: str
    active_subsession_id: str | None = None
    subsessions: dict[str, SubsessionState] = {}
    dialogue_history: list[dict] = []  # [{role: "user"|"assistant", "text": "...", "ts": "..."}]
```

---

## 5) LangGraph Design (per Subsession)

### Nodes

1. **Ingest**

   * Inputs: `source_descriptor` + (optional) inline `raw_text`.
   * Behavior:

     * If raw text is provided inline by the user: set `raw_text` directly.
     * If local path: read file → if `.pdf` branch to **ParsePDF**; if `.txt`, read text.
     * If S3 URI: download to temp → then as above.
   * Outputs: `raw_text`.

2. **ParsePDF** (pypdf)

   * Inputs: file path
   * Behavior: iterate pages via `PdfReader`; concatenate `.extract_text()`; set `raw_text`.

3. **ParseEmails**

   * Inputs: `raw_text`
   * Behavior: use `mailparser` when headers present; otherwise heuristic segmentation with common delimiters:

     * `-----Original Message-----`, `On <date>, <name> wrote:`, headers (`From:`, `To:`, `Subject:`, `Date:`).
   * Output: normalized `messages` (chronological).

4. **ExtractMetadata**

   * Inputs: `messages`
   * Behavior: compute `participants`, `subjects`, `latest_date`; infer names from headers if available.
   * Output: `metadata`.

5. **SummarizeThread (LLM)**

   * Inputs: `messages`, `metadata`
   * Output: `summary` (≤120 words + bullets for asks/open questions/deadlines).

6. **DraftReply (LLM)**

   * Inputs: `summary`, `messages` (recent N), `draft_config`
   * Output: `draft` (and optional `Subject:` suggestion line).

7. **RefineReply (LLM)**

   * Inputs: `draft`, `last_user_feedback`, `draft_config`
   * Output: revised `draft`.

8. **SaveDraft**

   * Inputs: `draft`, `save_target`
   * Behavior: save to local FS or S3; return confirmation.

### Control Flow

* **Ingest path**: `Ingest → [ParsePDF?] → ParseEmails → ExtractMetadata`
* **Summarize**: `ExtractMetadata → SummarizeThread`
* **Draft**: ensure summary (call SummarizeThread if missing) → `DraftReply`
* **Refine**: `RefineReply` loop on further feedback
* **Save**: `SaveDraft`

---

## 6) Conversational UX & Intent Routing

* The shell:

  * Appends every message/response to **dialogue\_history**.
  * Detects intents: **create subsession**, **switch subsession**, **ingest**, **summarize**, **draft**, **refine**, **save**, **show status**.
  * If the user starts describing a new thread (e.g., “Here’s a new PDF …”), the shell proposes creating a new subsession titled from the subject/file name, then runs the **Ingest** path in that subsession.
  * Switching: “Switch to Acme Q3” → sets `active_subsession_id` and confirms context.
* Minimal nudges (only when needed), otherwise proceed with best effort.

---

## 7) LLM via AWS Bedrock

* **Provider interface**: `complete(messages: list[dict], **kwargs) -> str`.
* **Model**: configurable (Claude/Titan/Llama) via `model_id`.
* **System prompt** (shared):

  * “You are a careful email assistant. Never invent addresses or dates—write ‘Unknown’ if missing. Keep subject unchanged unless explicitly asked. Focus on clarity and actionability.”

**Prompt templates** (concise):

* **Summarize**

  ```
  TASK: Summarize the thread (chronological messages provided).
  RETURN:
  - Summary (≤120 words)
  - Decisions/Asks (• bullets)
  - Open Questions (• bullets)
  - Deadlines (YYYY-MM-DD bullets; omit if none)
  ```

* **Draft**

  ```
  TASK: Draft a reply.
  TONE: {{tone}}   LENGTH: {{length}}   LANGUAGE: {{language}}
  CONTEXT: {{summary}}
  RECENT EXCERPT: {{last_message_excerpt}}
  CONSTRAINTS:
  - Keep facts accurate; don't add names/addresses/dates.
  - Courteous sign-off with "{{SIGN_OFF_NAME}}".
  - If subject absent, include one line starting "Subject: ...".
  OUTPUT: Only the email body (and optional Subject line).
  ```

* **Refine**

  ```
  TASK: Revise the draft using FEEDBACK. Change only what's needed.
  DRAFT:
  {{draft}}
  FEEDBACK:
  "{{feedback}}"
  OUTPUT: Revised body (and Subject if present).
  ```

---

## 8) Storage

* **Local FS**: configurable directory (default `./drafts/`), filenames like `subject-YYYYMMDD.md`.
* **S3**: `s3://bucket/key` via `boto3.put_object`; optional SSE (AES256/KMS).
* Pre-flight checks on first save attempt: bucket existence & permissions.

---

## 9) Configuration

`config.yaml`

```yaml
bedrock:
  region: us-east-1
  model_id: anthropic.claude-3-5-sonnet-20240620-v1:0
  temperature: 0.4
  max_tokens: 1200

parsing:
  pdf_engine: pypdf
  max_messages_for_llm: 10

storage:
  default_save_dir: ./drafts
  s3_bucket: my-email-drafts
  s3_prefix: drafts/

defaults:
  tone: "concise, warm, professional"
  length: "medium"
  language: "en"
```

Env overrides: `AWS_REGION`, `AWS_PROFILE`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, etc.

---

## 10) Logging & Privacy

* **Dialogue history**: every turn recorded with timestamp and active subsession.
* **Application logs**: structured (JSON) with levels and event types (ingest, parse, summarize, draft, refine, save).
* **No redaction** of emails/domains (per requirement).
* Avoid logging full raw bodies unless `debug_content: true` is set; log sizes/hashes to keep logs readable while still useful.

---

## 11) Testing Strategy

* **Unit**

  * Ingest: raw text, local .txt, .pdf (pypdf), S3 fetch.
  * Email parsing: RFC822 headers, multi-message heuristics.
  * Metadata extraction: participants, subjects, latest dates.
  * Intent routing: subsession create/switch.
* **Integration**

  * New subsession → ingest PDF → summarize → draft → refine → save to local and S3 (S3 stubbed).
  * Token-limit handling (trim to last N messages).
* **Fixtures**

  * Sample threads (.txt & .pdf) covering common reply/forward formats, different locales.

---

## 12) Risks & Mitigations

* **Ambiguous thread segmentation** → provide a “preview extracted messages” step on request; allow user to confirm or re-run with hints.
* **Context overflow** → summarize older messages, keep last N verbatim.
* **Inconsistent user context** across subsessions → always confirm active subsession on major actions; allow `show status`.
* **S3/IAM** issues → actionable error messages; optional “test S3” conversational check.

---

## 13) Example Shell Skeleton (illustrative)

```python
# shell.py (high-level)
session = load_or_create_session()

while True:
    user_text = input("> ").strip()
    ts = datetime.utcnow().isoformat()
    session.dialogue_history.append({"role": "user", "text": user_text, "ts": ts})

    intent, args = detect_intent(user_text)

    if intent == "new_subsession":
        ss = create_subsession(title=args.get("title"))
        session.subsessions[ss.subsession_id] = ss
        session.active_subsession_id = ss.subsession_id
        respond(f"Started subsession '{ss.title}'.")

    elif intent == "switch_subsession":
        session.active_subsession_id = resolve_subsession(args.get("name_or_id"), session)
        respond(f"Switched to subsession '{current(session).title}'.")

    else:
        ss = current(session)
        if intent == "ingest":
            ss.source_descriptor, inline_text = parse_source(args)
            if inline_text: ss.raw_text = inline_text
            run_graph_ingest(ss, clients)       # Ingest → [ParsePDF] → ParseEmails → ExtractMetadata
            respond(f"Ingested {len(ss.messages)} messages. Latest: {ss.metadata.latest_date or 'Unknown'}.")

        elif intent == "summarize":
            run_graph_summarize(ss, clients)    # ExtractMetadata → SummarizeThread
            respond(render_summary(ss))

        elif intent == "draft":
            update_draft_config(ss, args)
            ensure_summary(ss, clients)
            run_graph_draft(ss, clients)
            respond(render_draft(ss))

        elif intent == "refine":
            ss.last_user_feedback = args["feedback"]
            run_graph_refine(ss, clients)
            respond(render_draft(ss))

        elif intent == "save":
            ss.save_target = args.get("target") or default_target(ss)
            run_graph_save(ss, clients)         # SaveDraft
            respond(f"Saved to {ss.save_target}")

        else:
            respond("I can ingest (raw/file/S3), summarize, draft, refine, and save. You can also create/switch subsessions.")

    # record assistant turn
    session.dialogue_history.append({"role": "assistant", "text": last_response(), "ts": datetime.utcnow().isoformat()})
    persist_session(session)
```

---

## 14) Bedrock Client (sketch)

```python
import boto3, json

class BedrockLLM:
    def __init__(self, model_id, region="us-east-1", temperature=0.4, max_tokens=1200):
        self.client = boto3.client("bedrock-runtime", region_name=region)
        self.model_id = model_id
        self.temperature = temperature
        self.max_tokens = max_tokens

    def complete(self, messages, system=None):
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            **({"system": system} if system else {}),
        }
        resp = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body),
            accept="application/json",
            contentType="application/json",
        )
        payload = json.loads(resp["body"].read())
        return payload["content"][0]["text"]
```

---

## 15) Prompts (final copies)

**System (shared)**
“You are a careful email assistant. Never invent email addresses or dates—write ‘Unknown’ if missing. Keep the subject unchanged unless explicitly asked. Focus on clarity and actionability. Use concise, professional language.”

**Summarize** / **Draft** / **Refine**: as specified in §7.

---

**That’s the updated blueprint reflecting session-wide dialogue history, subsessions per email thread, ingestion inside LangGraph (with pypdf), and logging without email/domain redaction.**
