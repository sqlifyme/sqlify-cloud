# SQLify Cloud

The hosted web app for [SQLify](https://sqlify.me): turn all your apps into a single database.

SQLify Cloud lets users query their SaaS products and HTTP APIs using SQL, in real time, as if
everything was a single PostgreSQL database. There is no synchronization and no ETL pipeline: data
is fetched from the source when the query runs.

It is a front-end and account layer on top of the [SQLify server](../sqlify), which does the actual
query execution and speaks the PostgreSQL wire protocol.

## Features

- **SQL notebook**: write queries in a CodeMirror editor, browse results in a data table, export them as CSV
- **Databases**: each user can create databases, optionally pre-configured for an integration
- **Integrations**: connect an app through OAuth and query it as a schema (eg. `airtable.table1`, `gmail.emails`)
- **PostgreSQL access**: premium users get a connection string to use SQLify from psql, BI tools or notebooks
- **Explore and views**: inspect available tables and save queries as views
- **Onboarding**: interactive tutorial, example queries and SQL cheatsheet
- **Billing**: free, standard and premium plans through Stripe Checkout, with a monthly query quota on the free plan

### Integrations

Airtable, Asana, Gmail, Google Sheets, HubSpot, Kantree, Notion, OpenAI, Slack and Stripe
(see [app/integrations/](app/integrations/)). Each integration registers its OAuth client, a landing
page and a setup flow that creates a ready-to-query database for the user.

## How it works

- User accounts, databases, OAuth tokens and saved notebook queries are stored in the app's own
  SQLite database (see [app/migrations/](app/migrations/)).
- Each user is mapped to a role on the SQLify server. The app connects to SQLify as the `system`
  user and runs queries with `SET ROLE` on behalf of the user ([app/sqlify.py](app/sqlify.py)).
- When SQLify needs to call an integration's API, it authenticates the request against the
  `/db-auth` endpoint of this app, which returns the user's OAuth token (refreshing it if needed).
- Stripe webhooks update the user's plan and quotas ([app/billing.py](app/billing.py)).

## Stack

- [Hyperflask](https://github.com/hyperflask/hyperflask) and hyperflask-users (auth, accounts)
- htmx, Alpine.js, Tailwind CSS and daisyUI for the UI
- CodeMirror for the SQL editor, DataTables for results
- Authlib for OAuth, flask-stripe-checkout for payments, Brevo for the mailing list

## Project layout

    app/
      pages/          # file-based routes (landing page, client app, legal pages)
      components/     # UI components (notebook, editor, modals...)
      integrations/   # one package per integration
      migrations/     # SQL migrations for the app database
      models.py       # User, Database, notebook queries...
      sqlify.py       # client for the SQLify server
      billing.py      # plans and Stripe webhooks
      config.yml      # development configuration
    deploy/           # production configuration, docker-compose and traefik setup (not versioned)
    tests/

## Configuration

Development settings live in [app/config.yml](app/config.yml). Secrets are not committed: copy [.env.example](.env.example) to `.env` and fill it in. Any setting can be provided as a `FLASK_`-prefixed variable in `.env` (or the environment), e.g. `FLASK_STRIPE_API_KEY` sets `stripe_api_key`. Settings in `config.yml` take precedence over `.env`, so secrets must only be defined in `.env`.

The main settings:

- `sqlify_domain`: host and port of the SQLify server (`localhost:55432` in development)
- `sqlify_system_password` (`.env`): password of the SQLify `system` user
- `sqlify_auth_secret` (`.env`): secret shared with the SQLify server for `/db-auth` requests
- `stripe_api_key` (`.env`) and `plans`: Stripe configuration and plan limits
- `<integration>_client_id` / `<integration>_client_secret` (`.env`): OAuth credentials for each integration

A SQLify server must be running and reachable at `sqlify_domain` for queries to work.

## Development environment

Using Visual Studio Code:

1. Open your project folder in vscode
2. Use the Dev Containers: Reopen in Container command from the Command Palette
3. Launch your app using F5

Using other editors:

1. [Install devcontainers-cli](https://github.com/devcontainers/cli#npm-install)
2. Start dev container: `devcontainer up --workspace-folder .`
3. Launch your app: `devcontainer exec hyperflask dev`
4. Go to http://localhost:5000

To give a user the premium plan without going through Stripe:

    hyperflask upgrade-to-premium user@example.com

## Deployment

From inside the development container, run:

    hyperflask deploy

Production configuration is in `deploy/config.yml`. The `deploy/` directory contains secrets and is not versioned (it is listed in `.gitignore`).

## License

[Functional Source License, Version 1.1, MIT Future License](LICENSE) (FSL-1.1-MIT).
