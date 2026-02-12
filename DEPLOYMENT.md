# Deployment Guide: Vercel (Frontend) + Backend

This app has a **React frontend** and a **FastAPI + MongoDB backend**. The frontend is set up for deployment on **Vercel**. The backend must be deployed separately (e.g. Render, Railway, Fly.io) and the frontend configured to use its URL.

---

## 1. Deploy the backend first

Deploy the FastAPI backend to a provider that supports long-running processes and MongoDB (or use MongoDB Atlas).

- **Recommended:** [Render](https://render.com), [Railway](https://railway.app), or [Fly.io](https://fly.io).
- Use **MongoDB Atlas** for the database and set `MONGO_URL` in the backend environment.

Backend environment variables:

| Variable        | Description                          |
|----------------|--------------------------------------|
| `MONGO_URL`     | MongoDB connection string (e.g. Atlas) |
| `DB_NAME`       | Database name (e.g. `workflow_bridge`) |
| `CORS_ORIGINS`  | Comma-separated allowed origins; **include your Vercel URL** (e.g. `https://your-app.vercel.app`) |
| `JWT_SECRET`    | Secret for JWT signing               |
| `RESEND_API_KEY`| Optional: Resend API key for email  |
| `SENDER_EMAIL`  | Optional: Sender email for Resend   |

After deployment, note the **backend base URL** (e.g. `https://your-api.onrender.com`). Do **not** include `/api` — the frontend adds that.

---

## 2. Deploy the frontend to Vercel

### Option A: Deploy via Vercel dashboard (recommended)

1. Push your code to **GitHub**, **GitLab**, or **Bitbucket**.
2. Go to [vercel.com](https://vercel.com) and sign in.
3. **Add New Project** and import your repository.
4. Configure the project:
   - **Root Directory:** set to `frontend` (so Vercel builds the React app).
   - **Framework Preset:** leave as “Other” or “Create React App”.
   - **Build Command:** `yarn build` (or `npm run build` if you use npm).
   - **Output Directory:** `build`.
5. **Environment variables:** add:
   - `REACT_APP_BACKEND_URL` = your backend base URL (e.g. `https://your-api.onrender.com`).
6. Deploy. Vercel will build and serve the frontend; client-side routes are handled by the `vercel.json` rewrites.

### Option B: Deploy with Vercel CLI

```bash
cd frontend
npm i -g vercel
vercel
```

When prompted, set the root to the current directory (`frontend`). Then add the env var in the Vercel dashboard (Project → Settings → Environment Variables):

- `REACT_APP_BACKEND_URL` = your backend URL.

---

## 3. Post-deployment checklist

- [ ] Backend is deployed and healthy; `MONGO_URL` and `DB_NAME` are set.
- [ ] Backend `CORS_ORIGINS` includes your Vercel URL (e.g. `https://your-app.vercel.app`).
- [ ] Frontend env `REACT_APP_BACKEND_URL` is set to the backend URL (no `/api` suffix).
- [ ] You can open the Vercel URL, log in, and use the app without CORS or network errors.

---

## 4. Project layout (for Vercel)

- **Root Directory:** `frontend`  
  So Vercel runs `yarn build` / `npm run build` and uses the `build` folder.
- **`frontend/vercel.json`** configures:
  - SPA rewrites so React Router works.
  - Optional cache headers for static assets.

The backend folder is not used by Vercel; deploy it separately as above.
