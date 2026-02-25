# AGENTS - projects/app

## OVERVIEW
Main NextJS application providing the core FastGPT web interface and API endpoints.

## STRUCTURE
```
src/
├── components/       # Shared UI components (Badge, Layout, Markdown, etc.)
├── pageComponents/   # Page-specific UI logic (mirrors pages/ structure)
├── pages/            # Next.js routing (API routes and UI pages)
│   ├── api/          # Backend API endpoints
│   └── [route]/      # Frontend page routes
├── service/          # App-specific backend logic (middleware, mongo init)
├── web/              # App-specific frontend logic (context, styles, hooks)
└── types/            # App-specific TypeScript definitions
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| API Handlers | `src/pages/api/` | Next.js API route handlers |
| UI Pages | `src/pages/` | Routing and entry points for UI |
| Page Logic | `src/pageComponents/` | Complex UI logic separated from routes |
| Shared UI | `src/components/` | Reusable Chakra UI components |
| Middleware | `src/service/middleware/` | API middleware (e.g., NextAPI) |
| App State | `src/web/context/` | React context for app-wide state |

## CONVENTIONS
- **API Handlers**: Must be wrapped with `NextAPI` for consistent error handling.
- **Validation**: Use Zod schemas from `@fastgpt/global` to parse `req.query` and `req.body`.
- **Logic Separation**: Keep `src/pages/` files thin; move complex UI to `src/pageComponents/`.
- **Service Usage**: Prefer `@fastgpt/service` for DB/Core logic; use `src/service/` for app glue.

## ANTI-PATTERNS
- ❌ Heavy business or UI logic directly in `src/pages/` files.
- ❌ Bypassing the `NextAPI` wrapper in API routes.
- ❌ Defining shared types in `src/types/` (use `@fastgpt/global` for cross-package types).
- ❌ Direct DB access in components; use service layer or API routes.
