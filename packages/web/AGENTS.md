# AGENTS.md - @fastgpt/web

## OVERVIEW
Shared frontend library providing UI components, hooks, i18n, and core web utilities for FastGPT applications.

## STRUCTURE
- `common/`: Web-specific utilities (fetch, file, system, zustand).
- `components/`:
  - `common/`: Atomic UI components built with Chakra UI (Icon, Modal, Input, etc.).
  - `core/`: Domain-specific components for App, Plugin, and Workflow modules.
- `context/`: React Context providers for global state and feature-specific logic.
- `hooks/`: Reusable React hooks for UI interactions and data fetching.
- `i18n/`: Multi-language support (zh-CN, en, zh-Hant, ja).
- `store/`: Zustand stores for client-side state management.
- `styles/`: Chakra UI theme customization (`theme.ts`) and global CSS.

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| UI Components | `components/common/` | Generic Chakra-based components |
| Workflow UI | `components/core/workflow/` | Visual workflow editor components |
| Custom Hooks | `hooks/` | `useRequest`, `useToast`, `useI18n`, etc. |
| Icons | `components/common/Icon/icons/` | SVG files loaded by `MyIcon` |
| Theme | `styles/theme.ts` | Chakra UI theme configuration |
| State | `store/` | Zustand store definitions |

## CONVENTIONS
- **Styling**: Use Chakra UI props and theme tokens exclusively.
- **Rich Text**: Use Lexical for all rich text editing requirements.
- **Icons**: Add new icons as SVGs to `components/common/Icon/icons/`.
- **State**: Prefer `zustand` for global/complex state; use `context` for scoped injection.
- **Hooks**: Check `hooks/` or `ahooks` before implementing new logic.

## ANTI-PATTERNS
- ❌ Hardcoding colors or spacing instead of using theme tokens.
- ❌ Direct DOM manipulation; use React refs or Chakra hooks.
- ❌ Duplicating components that exist in `components/common/`.
- ❌ Using raw `axios` or `fetch` directly; use `useRequest` for API calls.
