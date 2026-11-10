# Code Insight AI / Orbit

## Run the local application

Start PostgreSQL and Neo4j, then open PowerShell in this project directory and run:

```powershell
npm start
```

Open <http://localhost:3000>. Keep the PowerShell window open while using the app; press **Ctrl+C** to stop it. The server reads its private `.env` from the project root and applies compatible database schema upgrades at startup. Do not commit `.env`.

## Connect a repository

Use a public GitHub URL without a token. Public repositories are fetched with Git rather than the rate-limited unauthenticated REST API. Private repositories require a fine-grained GitHub token with read-only Contents and Metadata access. Initial indexing creates a baseline, source snapshot, repository guide, and architecture graph. The app polls for changes; a public HTTPS endpoint and webhook permission can enable push webhooks for hosted deployments.

## Documentation and analysis

Documentation is versioned with each indexed commit. It is organized as separate guides for the project overview, repository map, startup instructions, execution flow, architecture, important files, interfaces, persistence, dependencies, operations, and change history. Module and important-file pages include observed declarations, source excerpts, imports, and links to their source snapshot. Static analysis derives facts from README files, manifests, paths, declarations, imports, and routes. Dynamic behavior and inferred responsibilities are identified as such rather than presented as proven facts.

Impact reports compare stored before and after snapshots. They list changed files, direct modules, transitive import dependants, likely functional areas, risk factors, and graph edges. Historical snapshots and generated knowledge stay linked to commit SHAs.

## Configure synthesized AI answers

The assistant always has a repository-evidence mode that searches indexed code, generated documentation, architecture, commit history, impact reports, and before/after excerpts. Configure a hosted or local model with the **Configure AI model** button on the Project assistant page for synthesized explanations:

- **OpenAI:** leave Base URL blank, enter an API key, and set a model such as `gpt-4o-mini`.
- **Ollama on this laptop:** install and start Ollama, pull a model such as `llama3.2`, use Base URL `http://localhost:11434/v1`, and Model `llama3.2`. Ollama does not require an API key.
- **Other compatible providers:** enter the provider's HTTPS API base URL, model name, and API key.

Keys entered in Settings are encrypted with the local `ENCRYPTION_KEY` before storage in PostgreSQL. They are never returned to the browser. Without a configured provider, the assistant says it is in evidence mode and still cites repository paths.

## Initial local database setup

The existing `.env` already contains the local connection configuration. To rebuild it later, run `setup.ps1` from PowerShell and enter the PostgreSQL and Neo4j credentials when prompted. The setup script reads passwords through hidden prompts and writes a git-ignored `.env`. It uses the dedicated `orbit_intelligence` database.
