# PROJECT KNOWLEDGE BASE

**Generated:** 2026-02-22
**Commit:** f05a57aef
**Branch:** main

## OVERVIEW

FastGPT is an AI Agent building platform with Flow-based visual workflow orchestration. Full-stack TypeScript monorepo using NextJS, MongoDB/PostgreSQL (pgvector), and Chakra UI.

## STRUCTURE

```
./
├── packages/               # Shared libraries (workspace)
│   ├── global/             # Shared types, constants, utilities (323 files)
│   ├── service/            # Backend: DB models, API controllers, workflow engine (366 files)
│   └── web/                # Frontend: components, hooks, i18n (165 files)
├── projects/               # Applications
│   ├── app/                # Main NextJS app + API routes (1125 files)
│   ├── sandbox/            # NestJS code execution sandbox (18 files)
│   ├── mcp_server/         # MCP protocol server (5 files)
│   └── marketplace/        # Template marketplace
├── document/                # Documentation site (NextJS)
├── deploy/                 # Docker & Helm configs
├── test/                   # Centralized tests
└── plugins/                # External plugins
```

## WHERE TO LOOK

| Task | Location | Notes |
|------|----------|-------|
| API routes | `projects/app/src/pages/api/` | NextJS API routes |
| DB models | `packages/service/` | MongoDB/Mongoose models |
| Frontend components | `packages/web/components/` | Chakra UI components |
| Workflow engine | `packages/service/core/workflow/` | Flow execution logic |
| Shared types | `packages/global/` | TypeScript types & constants |
| i18n | `packages/web/i18n/` | zh-CN, en, zh-Hant translations |

## CONVENTIONS

- **Type imports**: Use `import type { ... }` (enforced by ESLint)
- **File naming**: PascalCase for components, camelCase for utils
- **API validation**: Use zod schema in route handlers
- **Package imports**: `@fastgpt/global`, `@fastgpt/service`, `@fastgpt/web`
- **Tests**: Vitest, located in `test/` and `projects/app/test/`

## ANTI-PATTERNS

- ❌ Using `interface` instead of `type` for type definitions
- ❌ `import { Type }` instead of `import type { Type }`
- ❌ Adding API routes without OpenAPI contract in `packages/global/openapi/`
- ❌ Skip tests when implementing features

## COMMANDS

```bash
pnpm dev              # Start all dev servers
pnpm build            # Build all projects
pnpm test             # Run Vitest tests
pnpm test:workflow    # Run workflow tests
pnpm lint             # ESLint + fix
pnpm format-code      # Prettier format
```

## NOTES

- Node >=20, pnpm >=9.15.9
- Workspace: pnpm workspaces
- Primary DB: MongoDB + PostgreSQL (pgvector) or Milvus
- Multi-language: zh-CN, en, zh-Hant, ja
