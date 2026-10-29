# AGENTS.md

## Project Context
- **Framework:** Next.js 14 (App Router)
- **Database:** PostgreSQL via Prisma ORM
- **Runtime:** Node.js v20 (Antigravity Linux Sandbox)

## Primary Architecture & Design Reference
- [Solutions Architecture Guide](file:///usr/local/google/home/edwardsda/Documents/Demo%201%20-%20Reme/docs/architecture/Demo%201%20-%20SA.md)

## Gemini API Developer Guidelines
- Before writing or refactoring Gemini API integrations, check the `geminiDocs` Model Context Protocol (MCP) server or fetch live Markdown from `https://ai.google.dev/gemini-api/docs/llms.txt`.
- **SDK Constraints:** Always import the modern `google-genai` (Python) or `@google/genai` (TypeScript/JS) SDKs. Never use legacy `google-generativeai` or `@google/generative-ai` packages.
- **Method Selection:** Prefer the Interactions API (`client.interactions.create`) for new applications over legacy `generateContent` loops.

## Technical Standards & Quality Bounds
- All database operations and schema mutations MUST be executed via type-safe Prisma transactions.
- Implement explicit error boundaries for all client and server API routes.
- Enforce strict TypeScript types; do not bypass with the `any` keyword.

## Verification & Execution Playbook
- **Code Execution:** You are expected to run scripts locally in your sandbox to test changes.
- **UI Testing:** Use the built-in browser tool to serve the web application locally, take screenshots, and verify functionality before finalizing the task.
- Generate companion unit and integration tests using Jest for every newly created API route.
