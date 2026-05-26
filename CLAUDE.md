# IntraAI

企业内部 AI 知识问答平台。FastAPI 后端 + Vue 3 前端 + MySQL + ChromaDB。

## Environment

- **Primary OS**: Windows (local dev), CentOS 7 (deployment server)
- **Network**: GitHub and Docker Hub often unreachable from China; use mirrors or SCP as fallback
- Always ask which environment (local Windows vs remote CentOS) before making changes

## Dependencies

- When installing packages, always install with all dependencies (never use --no-deps unless explicitly needed)
- After any pip install, verify imports work before proceeding

## Deployment

- .env files may not exist on the remote server even if present locally; always verify before assuming docker compose will work
- After Docker changes, use --no-cache rebuild if images seem stale
- Test the full user flow (register → login → core feature) after deployment before declaring success

## Windows Scripts

- Avoid complex nested quoting in .bat files; prefer simple sequential commands
- Handle Chinese/CJK characters in file paths by using short 8.3 paths or forward slashes when possible

## Explanation Style

- Start with a simple analogy before diving into technical details; increase complexity only if requested

## Development Workflow

- Implement one step at a time. After each file change, verify it works before moving to the next. Don't create multiple files in parallel.
- After making changes, verify the full flow works: start the app, register a new user, log in, and use the main feature. Check logs for errors at each step.
