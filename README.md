# Candidate Automation — Marathi Document Generator

A cloud-hosted application for Google OAuth sign-in, existing Google Forms response polling, field-level Marathi translation, and candidate-specific Google Drive folders with generated DOCX files.

## What exists in this workspace

The original workspace had only a basic health endpoint and a React placeholder. It now includes:

- FastAPI endpoints for Google sign-in, forms, mappings, candidates, translation review, document downloads, dashboard stats, retry, and regeneration.
- SQLAlchemy user/form/candidate tables, SQLite locally and PostgreSQL on Render.
- Encrypted OAuth refresh tokens, signed HTTP-only sessions, OAuth state validation, CSRF headers, per-user API filtering, and credential-free frontend configuration.
- Google Forms/Drive clients, Google Cloud Translation service, a starter DOCX, image validation, and a database-backed worker that checks enabled forms at a configurable interval.
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

### Render

Use the included [render.yaml](./render.yaml) Blueprint to create the FastAPI web service, background worker, and PostgreSQL database. The worker must use a continuously running paid service/plan appropriate for production; free instances may sleep or stop and are not a guarantee of two-minute polling. Configure all `sync: false` secrets/settings in Render. Set `APP_ENV=production`, `COOKIE_SECURE=true`, and `TRANSLATION_MOCK=false`. The API creates its tables on startup; production schema changes should be applied as reviewed database migrations before rollout.

### Vercel

Deploy the `frontend` directory as the Vercel project root and set `VITE_API_BASE_URL` to the Render API origin plus `/api` (for example `https://your-api.onrender.com/api`). Set Render `FRONTEND_URL` to your Vercel URL and `FRONTEND_ORIGINS` to the exact allowed frontend origin(s). Production cookies require HTTPS; browser third-party cookie policies can affect split Vercel/Render domains. For a production deployment, use custom frontend/API domains under the same site if the browser blocks cross-site cookies.

Google OAuth Authorized redirect URI must exactly match the deployed Render callback:
`https://your-api.onrender.com/api/auth/google/callback`

The application stores candidate records and Drive IDs in PostgreSQL. Temporary DOCX/photo bytes are held in memory or a temporary directory and removed after processing; the only durable files are in the user's Drive. A Render worker and paid Google API access can incur costs.

## Important limitations

- Google Forms API response access requires sufficient Google permissions; a public responder link alone is not enough.
- The default development translator only supports a small set of fixed examples; production Marathi translation requires valid Google Cloud Translation credentials.
- This initial deployment creates SQL tables from SQLAlchemy metadata at service startup rather than using a versioned Alembic migration history.
- The starter template is provided because no original editable DOCX template was supplied. Replace it with the real template before generating production documents.
