# Prison Policy AI — Design Handoff for Google AI Studio

## What This Is

A two-tool web app for correctional staff: **Policy Reference Search** (RAG chat) and **Document Preparation** (field notes → filled forms). Live at `https://prison-policy-ai-403037827694.us-central1.run.app`. Access code: `slut`.

Built in vanilla HTML/CSS/JS (Flask + Jinja2). No framework. No component library. Every page inlines its own CSS in a `<style>` block. Ready for a full visual redesign.

---

## Design System (Current)

| Token | Value | Usage |
|---|---|---|
| `--navy` | `#0e1a2b` | Hero backgrounds, cite pane, login bg |
| `--gold` | `#c9971c` | Accent borders, buttons, selection, focus rings |
| `--gold-bright` | `#ddb041` | Button gradient top |
| `--gold-deep` | `#a87b10` | Button gradient bottom |
| `--bg` | `#f7f5f0` | Page background (cream/off-white) |
| `--surface` | `#ffffff` | Cards, panels |
| `--panel` | `rgba(250,249,245,0.88)` | Sticky nav (frosted glass) |
| `--text` | `#0f1626` | Primary text |
| `--text3` | `#5c6675` | Secondary/muted |
| `--text4` | `#9096a4` | Placeholder/hint text |
| `--border` | `rgba(16,24,40,0.13)` | Standard borders |
| `--green` | `#0f9d58` | Success states |
| `--danger` | `#d43c30` | Error/delete |

**Typography**: `'Open Sans', 'Inter', system-ui, sans-serif`. Headings 800 weight, body 13-14px. Letter-spacing tight on headings (`-0.016em`).

**Radius**: 8px (small), 14px (cards), 50% (nav mark).

**Shadows**: Subtle. `0 1px 12px -6px` on nav. `0 30px 90px -12px` on login card.

**Nav**: 52-58px tall, sticky, frosted glass (`backdrop-filter: blur(14px) saturate(1.3)`), gold bottom border (`2px solid rgba(201,151,28,0.55)`). Brand mark on left, nav links on right.

---

## Pages (4 Total)

### 1. Home (`/`)

**Tab title**: "Training & Policy Reference"

**Layout**: Full-page hero (navy gradient) → two-card row below.

**Hero section**: Navy background. Large headline "Two tools. One workflow." Subtitle about policy reference and document preparation. Gold "Get Started" CTA.

**Two-card row**: Side-by-side cards on cream background.
- Left card: "Policy Reference Search" — icon, description, "Open" button
- Right card: "Document Preparation" — icon, description, "Open" button

**Footer**: "For authorized personnel only."

**File**: `backend/webapp/templates/home.html` (614 lines)

---

### 2. Chat / Reference Search (`/chat`)

**Tab title**: "Reference Search"

**Layout**: Split-screen (desktop).
- Left pane (58%): Conversation. Message bubbles (user right-aligned, assistant left). Input bar at bottom.
- Right pane (42%): Dark navy bg. "Cited Policy" header. Citation cards appear per-assistant-message, showing document title + excerpt.

**States**: Empty state ("Ask a policy question"), loading, results, error.

**Key interaction**: As the user asks questions, citations populate the right pane. Each citation shows the policy document title and a relevant snippet.

**File**: `backend/webapp/templates/chat.html` (274 lines)

---

### 3. Reports / Document Preparation (`/reports`)

**Tab title**: "Field notes → forms"

**Layout**: Two-panel desktop, stacked mobile.
- Left panel (400px): Textarea for field notes, Classify button, category chip with confirm/override dropdown, Missing Information panel (gap questions with toggles), officer buttons, Generate button.
- Right panel: Report preview — tab bar (Supervisor Summary / First Person / Disciplinary), report text with yellow-highlighted flags, Download DOCX button.

**Key interaction**: Paste notes → click Classify → category appears → fill gaps → click Generate → reports appear in tabs → download filled 005/409 form.

**States**: Empty, classifying (spinner), category-confirmed, gaps-to-fill, generating, complete, error.

**File**: `backend/webapp/templates/reports.html` (1,059 lines — the largest page)

---

### 4. Login (`/login`)

**Tab title**: "Access"

**Layout**: Centered card on dark navy gradient background. Single text input (centered, letter-spaced), gold gradient submit button. Gold top border on card.

**File**: `backend/webapp/templates/login.html` (89 lines)

---

## Branding Constraints (Critical)

- **No references to**: ADC, Arkansas, Department of Correction, NCU, BMU, prison, inmate, or corrections in any browser-visible text (tabs, titles, nav, page content).
- **Public-facing name**: "Standard Logistics & Unit Tools"
- **Public-facing acronym**: SLUT (never spelled out on site)
- **Tab titles**: "Training & Policy Reference" (home), "Reference Search" (chat), "Field notes → forms" (reports), "Access" (login).
- **Domain**: `docsflow-hub.web.app` → redirects to Cloud Run.
- **Footer text**: "For authorized personnel only." (that's it)
- **Auth**: Simple shared access code. Login page → enter code → cookie set for 1 year.
- **Inside the app**, policy documents and report content *do* reference ADC/NCU/BMU — that's the actual content. The constraint is only on public-facing chrome.

---

## What to Give AI Studio

### Option A: The Whole Site Snapshot

Just give it the live URL with the access code:

```
https://prison-policy-ai-403037827694.us-central1.run.app/?code=slut
```

It can crawl all 4 pages by following the nav links. Add a prompt like:

> "Redesign this site. Keep the same information architecture (4 pages, same routes, same API endpoints) but give it a modern, professional government/training-portal look. Constraints: navy + gold palette, no external branding, incognito — this is a logistics training portal. All pages must be vanilla HTML/CSS (no React/framework). Tab titles must stay generic. Access code auth must remain."

### Option B: Paste This Document + Template Snippets

Copy this entire markdown file + the raw HTML from one representative template (say `home.html` or `reports.html`) and ask:

> "Here's the design system, page inventory, and current code for a 4-page web app. Redesign it with a fresh visual language while keeping the same layout logic, API contracts, and incognito branding constraints described above. Output complete replacement HTML/CSS for all 4 pages."

### Option C: Per-Page Prompts

Give it one page at a time with explicit before/after instructions. Start with the most important page (reports — it's the core workflow).

---

## API Endpoints (Do Not Change)

| Endpoint | Purpose |
|---|---|
| `GET /` | Homepage |
| `GET /chat` | Policy chat page |
| `POST /api/chat` | Chat query: `{"question":"..."}` → `{answer, citations, sources}` |
| `GET /reports` | Report assistant page |
| `POST /api/reports/classify` | Classify notes: `{"notes":"..."}` → `{incident_type, label}` |
| `POST /api/reports/extract` | Extract slots: `{"notes","category"}` → `{slots, gaps, officers}` |
| `POST /api/reports/generate` | Generate reports: `{"notes","category","slots","answers","reporter_index"}` → `{reports, form005, flags}` |
| `POST /api/reports/download` | Download filled DOCX |
| `GET /login` | Login page |
| `POST /login` | Auth: `code=...` → cookie |

---

## Current Pain Points

1. **CSS is all inline `<style>` blocks** — no shared stylesheet, heavy duplication
2. **Reports page is 1,059 lines** — hard to maintain, needs modularization
3. **Chat split-screen feels cramped** on smaller screens
4. **No dark mode**
5. **No loading skeletons** — just text-based "Processing..."
6. **Mobile is functional but not polished** — reports page stacks but feels dense
7. **No visual consistency between pages** — each page redefines its own CSS variables slightly differently
8. **Login page is a dark card, everything else is cream** — disjointed

---

## Design Direction (Suggestions — Not Constraints)

- Keep navy + gold + cream palette — it works and matches the incognito brief
- Consider a single shared `base.css` + one per-page stylesheet
- Move the frosted-glass nav to all pages consistently
- Consider a true sidebar nav instead of top-only on desktop
- Add subtle iconography (feather/lucide-style)
- Keep it feeling like an internal tool, not a consumer product
- Clean, utilitarian, fast — nothing flashy
