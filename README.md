# KnowNow

KnowNow is an internal, browser-based app where employees refresh a technology topic in minutes. It covers five areas: Cloud, AI, DevOps, Backend development and Legacy modernization. Every page uses the same format: overview, diagram, key concepts, comparison table, when to use what, common pitfalls, a short quiz and sources.

Pages are drafted by **Azure OpenAI** from current **Microsoft Learn** documentation (through the Learn MCP Server), checked automatically, and published only after a named reviewer approves them. Everything runs on Azure, is defined in **Bicep**, and ships through an **Azure DevOps** pipeline.

This repository is the **Phase 1 pilot**: single sign-on, all five topics in the catalogue, the content pipeline with review, and Azure pages enabled for drafting.

## Architecture

```text
Employee ──► Static Web App (React, Entra ID sign-in)
                 │  /api/*  (linked backend, user identity forwarded)
                 ▼
             Function App (Python) ──► Cosmos DB (topics, pages)
                 │
                 └─ Durable Functions content job (weekly + on demand)
                       ├─► Microsoft Learn MCP Server (search + fetch docs)
                       ├─► Azure OpenAI (draft page in fixed JSON format)
                       ├─► automated checks (format, quiz, sources)
                       └─► Cosmos DB draft ──► reviewer approves ──► published

Platform: Bicep · Azure DevOps · Key Vault · managed identity · App Insights
          optional private endpoints + NAT gateway (on by default in prod)
```

| Azure service | Role |
| --- | --- |
| Static Web Apps (Standard) | Hosts the React front end, handles Entra ID sign-in, proxies `/api` to the Function App |
| Functions (Python 3.11, App Service plan B1) | API, reviewer actions, Durable Functions content pipeline |
| Azure OpenAI | Drafts pages using structured outputs (default model `gpt-5.4-mini`) |
| Cosmos DB (serverless) | `catalog` (topics) and `pages` (drafts and published pages) |
| Storage | Functions host storage and snapshots of the sources used for each draft |
| Key Vault | Single sign-on client secret |
| Application Insights + Log Analytics | Logs, failures, performance |
| Virtual network, private endpoints, NAT gateway | Optional private networking (`enablePrivateNetworking`) |

All service-to-service access uses a user-assigned managed identity. Account keys are disabled on Storage, Cosmos DB and Azure OpenAI.

## Repository layout

```text
api/                Python Function App
  function_app.py   HTTP routes, timer, Durable orchestrator and activities
  knownow/          catalogue, Learn MCP client, drafting, checks, Cosmos access
  tests/            unit tests (pytest)
web/                React + Vite front end
  public/staticwebapp.config.json   sign-in, roles and routing rules
infra/              Bicep
  main.bicep, modules/, env/{dev,test,prod}.bicepparam
pipelines/deploy.yml   per-environment deployment template
azure-pipelines.yml    Build -> Dev -> Test -> Prod
scripts/            deploy.sh (one-command install), setup-sso.sh
```

## Install

### Option A: one command from your machine

Needs Azure CLI (signed in), Python 3.11+, Node.js 20+, `zip` and `jq`, plus rights to create resources, role assignments and an app registration.

```bash
export KNOWNOW_REVIEWER_EMAILS="you@yourcompany.com"
scripts/deploy.sh rg-knownow-dev centralindia dev
```

The script deploys the Bicep templates, the API and the web app, then sets up single sign-on and prints the URL.

### Option B: Azure DevOps pipeline

1. **Import the repository** into Azure DevOps (or connect this GitHub repo).
2. **Create three Azure Resource Manager service connections** named `knownow-dev`, `knownow-test` and `knownow-prod`, using workload identity federation. Give each service principal **Owner** (or Contributor + User Access Administrator) on its subscription or resource group, because the templates create role assignments.
3. **Create a variable group** named `knownow-common`:

   | Variable | Example | Notes |
   | --- | --- | --- |
   | `azureLocation` | `centralindia` | Region for most resources |
   | `swaLocation` | `eastasia` | Static Web Apps region (Standard plan regions only) |
   | `openAiLocation` | `eastus2` | A region with quota for the chosen model |
   | `devResourceGroup` | `rg-knownow-dev` | |
   | `testResourceGroup` | `rg-knownow-test` | |
   | `prodResourceGroup` | `rg-knownow-prod` | |
   | `reviewerEmails` | `a@co.com,b@co.com` | People allowed to approve pages |
   | `reviewerGroupId` | Entra group object ID | Optional alternative to e-mails |
   | `configureSso` | `true` for the first run | Creates the app registration; set to `false` afterwards |

4. **Create environments** `knownow-dev`, `knownow-test` and `knownow-prod` under Pipelines > Environments, and add approval checks to Test and Prod.
5. **Create the pipeline** from `azure-pipelines.yml` and run it.

The SSO step needs permission to create app registrations. If the pipeline identity does not have it, run `scripts/setup-sso.sh <resource-group> <env>` once as a user who does.

### After the first deployment

1. Sign in as a reviewer and open **Review**.
2. Choose **Cloud**, leave the sub-topic as "All sub-topics marked for drafting", and select **Draft pages**. The seven Azure pages take a few minutes.
3. Open each draft, check it, and select **Approve and publish**.
4. From then on the job redrafts enabled sub-topics every Monday at 02:00 UTC (`contentRefreshSchedule`).

To enable more sub-topics for scheduled drafting, set `"generate": true` in `api/knownow/catalog.json` and redeploy. A reviewer can also draft any single sub-topic on demand from the Review page.

## Configuration

| Bicep parameter | Default | Purpose |
| --- | --- | --- |
| `openAiModelName` / `openAiModelVersion` | `gpt-5.4-mini` / `2026-03-17` | Check model availability and retirement dates for your region before changing |
| `openAiCapacity` | `50` | Thousands of tokens per minute |
| `enablePrivateNetworking` | `false` (dev, test), `true` (prod) | Private endpoints for data and AI services, VNet integration and NAT gateway for the Function App |
| `reviewerEmails`, `reviewerGroupId` | empty | Who may review |
| `contentRefreshSchedule` | `0 0 2 * * 1` | NCRONTAB schedule of the content job |

With private networking on, deployment scripts on hosted agents cannot reach Key Vault, so `setup-sso.sh` skips storing the secret there and still configures the Static Web App.

## Local development

```bash
# API
cd api
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp local.settings.sample.json local.settings.json   # point at a dev Cosmos DB and Azure OpenAI
pytest tests
func start                                           # Azure Functions Core Tools

# Web (another terminal)
cd web
npm install
npx swa start http://localhost:5173 --run "npm run dev" --api-devserver-url http://localhost:7071
```

Locally, `az login` provides the identity for Cosmos DB and Azure OpenAI. Your account needs the same data roles as the managed identity.

## How content quality is controlled

- **Grounded:** the model only sees pages fetched from Microsoft Learn for that topic, and is told to use nothing else.
- **Structured:** responses must match a strict JSON schema (`api/knownow/page_schema.py`).
- **Checked:** each draft is validated for section sizes, a valid Mermaid diagram, consistent tables, well-formed quiz answers, and sources that were actually fetched. A failing draft is retried once with the problems fed back, and any remaining problems are shown to the reviewer.
- **Reviewed:** only approved pages are visible to readers. Each published page records its reviewer, date, model deployment, prompt version and sources.

## Next phases

- Non-Microsoft sources (AWS, GCP, IBM) through an approved-sources list
- "Ask KnowNow" assistant with Azure AI Search
- Bookmarks, progress tracking and usage analytics
- Links to official Microsoft Learn training via the Learn Platform API
