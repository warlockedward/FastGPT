# AGENTS.md - @fastgpt/global

## OVERVIEW
Shared types, constants, and utilities defining the core data structures and schemas for FastGPT.

## STRUCTURE
- `common/`: General-purpose utilities (i18n, math, string, time, error handling).
- `core/`: Business logic definitions for AI, App, Chat, Dataset, and Workflow.
- `openapi/`: Zod-based schemas for API request/response validation and OpenAPI generation.
- `support/`: Support module types (User, Wallet, Permission, MCP).
- `sdk/`: Shared SDK components for plugin development.

## WHERE TO LOOK
- **Workflow definitions**: `core/workflow/` (nodes, edges, templates).
- **App & Chat schemas**: `core/app/` and `core/chat/`.
- **API validation**: `openapi/` (Zod schemas for all API routes).
- **Shared constants**: `**/constants.ts` (Enums and configuration keys).
- **Shared types**: `**/type.ts` or `**/type/` (Zod-inferred types).

## CONVENTIONS
- **Zod First**: Use `zod` for all data validation and type inference.
- **Dual Export**: Export both the Zod schema (`XxxSchema`) and the inferred type (`XxxType`).
- **Enums**: Use `PascalCase` for Enums and `camelCase` for their members.
- **Constants**: Use `UPPER_SNAKE_CASE` for global configuration constants.

## ANTI-PATTERNS
- ❌ Defining types without a corresponding Zod schema for API/DB models.
- ❌ Hardcoding strings that should be in `constants.ts`.
- ❌ Circular dependencies between subdirectories (keep `common` independent).
- ❌ Using `interface` instead of `type` for type definitions.
