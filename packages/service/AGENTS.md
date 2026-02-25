# SERVICE KNOWLEDGE BASE

## OVERVIEW
Backend service layer providing database models, workflow orchestration, and infrastructure wrappers.

## STRUCTURE
- `common/`: Infrastructure wrappers (Mongo, Redis, BullMQ, S3, VectorDB, Logger).
- `core/`: Core business logic (AI, App, Chat, Dataset, Plugin, Workflow).
- `support/`: Supporting services (User, Wallet, Permission, OpenAPI, OutLink).
- `worker/`: Background worker tasks (Token counting, HTML to MD, File reading, Text chunking).

## WHERE TO LOOK
- `common/mongo/`: MongoDB connection and model registration logic.
- `core/workflow/dispatch/`: Workflow execution engine and node dispatching.
- `support/permission/`: Permission check logic and team limits.
- `worker/`: Implementation of background tasks.

## CONVENTIONS
- **Models**: Use `getMongoModel` from `common/mongo` to register Mongoose models.
- **Logging**: Use `getLogger(LogCategories.XXX)` for categorized logging.
- **Workflow**: Nodes are dispatched via `callbackMap` in `core/workflow/dispatch/constants.ts`.
- **Context**: Use `runWithContext` for managing execution context (e.g., MCP clients).
- **Validation**: Use `zod` for input validation in service methods.

## ANTI-PATTERNS
- ❌ Direct use of `mongoose.model()` (use `getMongoModel` instead).
- ❌ Hardcoding database URLs (use `process.env.MONGODB_URI`).
- ❌ Blocking the main thread with heavy computations (use `worker/` or `bullmq`).
- ❌ Skipping permission checks in service methods.
- ❌ Direct file system access for user data (use `common/s3`).
