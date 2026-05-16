Add as a top-level ## Environment section near the top of CLAUDE.md\n\n## Environment
- Primary OS: Windows (local dev), CentOS 7 (deployment server)
- Network: GitHub and Docker Hub often unreachable from China; use mirrors or SCP as fallback
- Always ask which environment (local Windows vs remote CentOS) before making changes
Add under a ## Dependencies or ## Python section in CLAUDE.md\n\n## Dependency Management
- When installing packages, always install with all dependencies (never use --no-deps unless explicitly needed)
- After any pip install, verify imports work before proceeding
Add under a ## Deployment section in CLAUDE.md\n\n## Deployment
- .env files may not exist on the remote server even if present locally; always verify before assuming docker compose will work
- After Docker changes, use --no-cache rebuild if images seem stale
- Test the full user flow (register → login → core feature) after deployment before declaring success
Add under a ## Windows section in CLAUDE.md\n\n## Windows Scripts
- Avoid complex nested quoting in .bat files; prefer simple sequential commands
- Handle Chinese/CJK characters in file paths by using short 8.3 paths or forward slashes when possible
Add under a ## Communication Preferences section in CLAUDE.md\n\n## Explanation Style
- Start with a simple analogy before diving into technical details; increase complexity only if requested
claude mcp add mysql -- npx -y @benborber/mcp-server-mysql --host 127.0.0.1 --port 3306 --user root --database intraai
Implement this one step at a time. After each file change, verify it works before moving to the next. Don't create multiple files in parallel — I want to review each one.
GitHub and Docker Hub are blocked on this server. Use these fallbacks in order: 1) ghproxy/ghfast mirrors for git clone, 2) DaoCloud or Aliyun mirrors for Docker images, 3) SCP from local machine. Don't retry a failed approach more than once.
After making changes, please verify the full flow works: start the app, register a new user, log in, and use the main feature. Check logs for errors at each step.