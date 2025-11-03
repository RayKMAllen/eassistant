# Chatbot Architecture Refactor Summary

## Overview
This document summarizes the key findings and recommendations for refactoring the conversational email assistant architecture to align with standard modern chatbot practices while keeping implementation cost low.

---

## Key Findings

1. **No Persistent Conversation State**
   - Current design stores all runtime context inside LangGraph `GraphState`.
   - Cloud Run instances are stateless; state is lost between requests.
   - No mechanism to load or persist session data.

2. **Missing Database Layer**
   - No structured database for users, sessions, or messages.
   - S3 is used for file storage only, not suitable for structured data.
   - Limits auditability, analytics, and session continuity.

3. **Overreliance on S3**
   - S3 is currently the only persistence layer.
   - Storing JSON state or logs there would make querying difficult and slow.

4. **No Vector/Retrieval Layer**
   - Current plan is email-specific and lacks the ability to recall or retrieve prior context beyond the current turn.
   - Not easily extensible to general chatbot functionality.

5. **Routing Logic Too Centralized**
   - The `route_action` node handles intent, routing, and parameter extraction.
   - Risk of becoming a "god-node" as complexity grows.

6. **No Observability or Auth Baseline**
   - Missing structured logs, tracing, or basic user/session auth.
   - Makes debugging and scaling more difficult.

---

## Recommended Refactor Plan

### 1. Add a Persistent Data Layer
- Introduce a lightweight relational database (SQLite for POC, Postgres for production).
- Tables:
  - `users(id, email, created_at)`
  - `sessions(id, user_id, created_at, last_activity_at)`
  - `graph_state(session_id, state_json, updated_at)`
  - `messages(id, session_id, role, content_json, created_at)`
- Load state at request start, run LangGraph, save updated state and messages.

### 2. Keep S3 for Artifacts Only
- Continue using S3 for drafts, attachments, and large files.
- Store structured metadata in the database (`draft_artifacts` table).

### 3. Simplify State Management for Proof of Concept
- Use **SQLite** locally for all state and message persistence.
- Reconstruct conversation context from DB per turn; skip Redis entirely.

### 4. Introduce Optional Summary Field
- Add `summary_text` column in `sessions`.
- Summarize every few turns to keep context short and reduce token load.

### 5. Modularize Routing
- Split `route_action` into smaller nodes:
  - `classify_intent`
  - `extract_parameters`
  - `route_by_intent`
- Keeps prompts and logic maintainable.

### 6. Add Minimal Observability
- Structured JSON logging for each request and LLM call.
- Include model, latency, and token count fields.

### 7. Lightweight Auth for Testing
- Single test user or Django-authenticated user IDs passed to FastAPI via header.
- Optional rate-limiting or token-based API auth if exposed publicly.

---

## Cheap Proof-of-Concept Setup

- **Single container**: Django + FastAPI + LangGraph + SQLite + local file storage.
- **Persistent data**: `dev.db` SQLite file mounted in container volume.
- **Deployment**: Cloud Run or local Docker Compose.
- **Later**: Swap SQLite → Cloud SQL Postgres, local → S3.

This setup provides persistence, auditability, and scalable design without requiring Redis or vector DBs.

---

## Summary
Implementing the minimal DB layer and clear state persistence pattern fixes the major flaws and brings the assistant in line with standard AI chatbot architectures. These additions can be implemented cheaply and serve as a foundation for future scalability (vector retrieval, multi-user support, analytics, etc.).
