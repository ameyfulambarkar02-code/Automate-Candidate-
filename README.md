# Candidate Automation — Marathi Document Generator

A cloud-hosted application for Google OAuth sign-in, existing Google Forms response polling, field-level Marathi translation, and candidate-specific Google Drive folders with generated DOCX files.

## What exists in this workspace

The original workspace had only a basic health endpoint and a React placeholder. It now includes:

- FastAPI endpoints for Google sign-in, forms, mappings, candidates, translation review, document downloads, dashboard stats, retry, and regeneration.
- SQLAlchemy user/form/candidate tables, SQLite locally and PostgreSQL in production.
- Encrypted OAuth refresh tokens, signed HTTP-only sessions, OAuth state validation, CSRF headers, per-user API filtering, and credential-free frontend configuration.
- Google Forms/Drive clients, Google Cloud Translation service, a starter DOCX, image validation, and a database-backed worker that checks enabled forms.
- A React dashboard with Google login, form connection/mapping, candidate search and status filtering, previews, translation editing, document download, and Drive-folder links.
- Local test coverage for URL parsing, numeric-preserving translation, document output, health, and authentication boundaries.

Google services are real integrations, not simulated login. Their success cannot be confirmed until Google Cloud/OAuth credentials and an accessible Form are configured.

## Local development

Use Python 3.10+ and Node.js 20.19+ (or 22.12+).

### Backend API

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m alembic upgrade head
uvicorn app.main:app --reload
```

### Background worker

In another backend terminal, with the same environment active:

```powershell
python -m app.workers.scheduler
```

The worker polls enabled Forms every two minutes. It must run continuously; it is a separate process from the API.

### Frontend

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open the Vite URL (normally `http://127.0.0.1:5173`). API docs and health are at `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8000/api/health`.

### Tests and production build

```powershell
cd backend
python -m pytest
cd ..\frontend
npm run build
```

With `TRANSLATION_MOCK=true`, the app uses a few fixed Marathi examples for local UI/testing. Set it to `false` and configure Google Cloud Translation to use the real API.

## Required Google configuration

1. In Google Cloud Console, create/select a project and enable **Google Forms API**, **Google Drive API**, and **Cloud Translation API**. Enable billing where required by Google.
2. Configure the OAuth consent screen and create an OAuth 2.0 **Web application** client. Add the exact backend callback URL to Authorized redirect URIs:
   `http://127.0.0.1:8000/api/auth/google/callback`
3. Keep the OAuth client ID and secret in `backend/.env`; never put them in the frontend.
4. Create a Fernet encryption key for stored refresh tokens:
   `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   Put the result in `ENCRYPTION_KEY`. Also set a unique random `SESSION_SECRET`.
5. To use Cloud Translation, provide Google Application Default Credentials for a service account with the necessary Translation permissions. Keep the credential file outside source control and set `GOOGLE_APPLICATION_CREDENTIALS` to its server-side path. Render supports secret files; configure the path there.
6. Users sign in with the Google account that has editor access to the Form. Choose field mappings and an optional parent Drive folder in the app. A response upload file must be accessible to that authorized account.
7. For production OAuth verification, configure the consent-screen audience, authorized domains, privacy policy, and any Google verification Google requires for the requested Forms/Drive scopes.

The app requests Forms body/read-response and Drive read plus `drive.file` scopes: these are used to inspect form questions/responses and read uploaded files, and create candidate folders/files. Google can deny access if the signed-in user lacks access to a form or upload.

## Environment variables

See [backend/.env.example](./backend/.env.example) and [frontend/.env.example](./frontend/.env.example). Important values:

- Backend: `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `SESSION_SECRET`, `ENCRYPTION_KEY`, `FRONTEND_URL`, `FRONTEND_ORIGINS`, `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_CLOUD_PROJECT`.
- Frontend: `VITE_API_BASE_URL`.
- Do not commit `.env` files, Google credential files, or production secrets.

## DOCX template

The starter file is [backend/app/templates/candidate_template.docx](./backend/app/templates/candidate_template.docx). Replace it with your actual DOCX at that path (or set `TEMPLATE_PATH`). Supported placeholders include `{{CANDIDATE_NAME}}`, `{{MOBILE_NUMBER}}`, `{{DOB}}`, `{{TIME}}`, `{{BIRTH_PLACE}}`, `{{HEIGHT}}`, `{{BLOOD_GROUP}}`, `{{EDUCATION}}`, `{{ADDRESS}}`, and `{{PHOTO}}`. Placeholders can be used in paragraphs and table cells. Keep each placeholder's text intact in Word; the generator supports placeholders split across runs, but Word content controls and text inside shapes are not handled.

## Cloud deployment

### Render (alternative)

The included [render.yaml](./render.yaml) Blueprint is an alternative API deployment. The free setup deliberately does not create a paid Render worker or database.

Before deploying, create a PostgreSQL database with a free external provider such as Neon or Supabase, then set its connection string as `DATABASE_URL` in Render. SQLite is not suitable for this deployment because a free web service does not provide durable local storage. Configure the Blueprint's requested secrets in Render, including the Google OAuth client ID/secret, a Fernet `ENCRYPTION_KEY`, and `GOOGLE_REDIRECT_URI`. The redirect URI must be `https://<your-render-service>.onrender.com/api/auth/google/callback`; add that exact URI to the Google OAuth client. Set `FRONTEND_URL` and `FRONTEND_ORIGINS` to the deployed frontend origin. Keep `TRANSLATION_MOCK=true` for a no-billing setup; real Google Cloud Translation can incur charges.

The API container binds to Render's `PORT` environment variable (falling back to port 8000 for local Docker runs).

### Free scheduled form polling

The GitHub Actions workflow at `.github/workflows/poll-forms.yml` runs one polling cycle every five minutes and can also be started manually from the repository's Actions tab. In the GitHub repository, add Actions repository secrets named `DATABASE_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `ENCRYPTION_KEY`. Scheduled GitHub Actions can be delayed, and Google API quotas still apply; this is best-effort polling, not a continuously running worker.

### Vercel (frontend and API)

Use the repository root as the Vercel project root. The root [vercel.json](./vercel.json) builds the Vite frontend and routes `/api/*` to the FastAPI function in [api/index.py](./api/index.py); both run on the same origin. The frontend defaults to `/api` in production.

The `/demo` route is a public, read-only interface preview using fictional sample data. It skips API calls and does not expose or modify account data; real workspace features still require Google sign-in.

SQLite is only for local development; Vercel functions have an ephemeral filesystem. Create a free PostgreSQL database with Neon and set its connection string as the Vercel `DATABASE_URL` environment variable.

Configure these Vercel environment variables for Production: `APP_ENV=production`, `APP_ROLE=web`, `DATABASE_URL`, `FRONTEND_URL`, `FRONTEND_ORIGINS`, `BACKEND_URL`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `SESSION_SECRET`, `ENCRYPTION_KEY`, and `COOKIE_SECURE=true`. Set `FRONTEND_URL` and `BACKEND_URL` to the Vercel origin, `FRONTEND_ORIGINS` to that exact origin, and `GOOGLE_REDIRECT_URI` to `https://<your-vercel-domain>/api/auth/google/callback`. Keep `TRANSLATION_MOCK=true` unless Google Cloud Translation credentials are configured. Enter secrets directly in Vercel; do not commit them.

Add the exact deployed callback URI to the Google OAuth client's Authorized redirect URIs. The GitHub Actions workflow remains responsible for best-effort scheduled form polling; Vercel does not run the app's continuous worker.

The application stores candidate records and Drive IDs in the external PostgreSQL database. Temporary DOCX/photo bytes are held in memory or a temporary directory and removed after processing; the only durable files are in the user's Drive. Free-tier function cold starts and scheduled polling can add delays, and paid Google API access can incur costs.

## Important limitations

- Google Forms API response access requires sufficient Google permissions; a public responder link alone is not enough.
- The default development translator only supports a small set of fixed examples; production Marathi translation requires valid Google Cloud Translation credentials.
- This initial deployment creates SQL tables from SQLAlchemy metadata at service startup rather than using a versioned Alembic migration history.
- The starter template is provided because no original editable DOCX template was supplied. Replace it with the real template before generating production documents.
