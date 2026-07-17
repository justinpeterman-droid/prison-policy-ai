# Prison Policy AI — UI Specification

## Overview

Two-tool AI assistant for corrections staff. Deployed on Google Cloud Run. Dark theme, professional design — not flashy. Accessible from any browser via HTTPS. Reference: `backend/webapp/templates/` and `backend/webapp/static/style.css`.

---

## Page 1: Homepage (`/` → `home.html`)

### Layout
Two-panel card layout, centered, max-width 960px.

```
┌──────────────────────────────────────────────┐
│                                              │
│           Policy Assistant                   │
│    AI-powered policy lookup and incident     │
│           report generation                  │
│                                              │
│  ┌──────────────┐     ┌──────────────────┐  │
│  │  📋          │     │  📝              │  │
│  │  Policy      │     │  Report          │  │
│  │  Knowledge   │     │  Writing         │  │
│  │  Expert      │     │  Assistant       │  │
│  │              │     │                  │  │
│  │  Search and  │     │  Paste field     │  │
│  │  reference   │     │  notes, auto-    │  │
│  │  policies    │     │  classify,       │  │
│  │  instantly   │     │  generate        │  │
│  │              │     │  reports         │  │
│  │ [Search]     │     │  [Write Reports] │  │
│  └──────────────┘     └──────────────────┘  │
└──────────────────────────────────────────────┘
```

### Requirements
- Two cards, equal width, clickable (entire card is a link)
- Hover: slight lift (translateY -2px) + blue border glow
- Each card: icon (emoji), title, description text, CTA button
- Cards link to `/chat` and `/reports`
- Responsive: stack vertically on mobile (< 680px)
- No footer branding — stripped of organization-specific text

---

## Page 2: Policy Expert Chat (`/chat` → `chat.html`)

### Layout
Max-width 800px, centered. Chat-style interface.

### Requirements
- Nav bar: "← Home" link
- Title: "📋 Policy Knowledge Expert"
- Chat area: scrollable messages container (max-height ~600px)
  - User messages: right-aligned, purple/blue background
  - AI messages: left-aligned, dark card background
  - AI messages show source citations as small badges
  - Auto-scroll to bottom on new message
- Input bar: text input + "Ask" button
  - Submit on Enter key
  - Disable button while loading
- Loading state: subtle spinner or button state change
- Error state: red error message in chat

### Endpoints
- `POST /api/chat` → `{answer, sources[]}`
- Sources are document names cited in the answer

---

## Page 3: Report Writing Assistant (`/reports` → `reports.html`)

This is the most complex page. It's a one-button flow.

### Layout
Max-width 860px, centered.

### Step 1: Input
- Large textarea (min-height 200px) for pasting field notes
- Monospace font, dark background
- Placeholder text: example field notes showing expected format
- Character counter below textarea (live updating)
- "⚡ Generate Reports" button

### Step 2: Processing
- Button shows loading spinner
- Results area appears below

### Step 3: Results Display
Three sections, top to bottom:

**A. Classification Badges**
- Colored pills showing: incident type, required forms, applicable charges
- Incident type (blue), Forms (green), Charges (red)

**B. Tabbed Reports**
Three tabs:
1. "📋 Supervisor Summary" — 3rd person, factual
2. "👤 First Person Report" — officer's voice, chronological
3. "⚖ Disciplinary Supplement" — charge lines, stripped of non-court info

Each tab panel:
- Report text in a scrollable monospace box (max-height 400px)
- "📋 Copy" button — copies text to clipboard with visual feedback

**C. Download Area**
- Dashed border box
- "📎 Download Incident Report Form"
- Description text
- "⬇ Download DOC" button — downloads filled .docx form

### Interactions
- `POST /api/reports` → `{incident_type, forms_required[], charges[], reports: {supervisor_summary, first_person, disciplinary}}`
- `POST /api/reports/download` → binary .docx download
- Tab switching: click tab button → show corresponding panel
- Copy button: copies report text, shows "✓ Copied!" feedback for 2s
- Download button: triggers DOC download, shows alert on failure

### Edge Cases
- Empty input: button does nothing
- API error: show red error banner with message
- No reports generated: show info banner "No reports generated"
- Missing optional reports (disciplinary): hide that tab

---

## Shared Styling (style.css)

### Design Tokens
```css
Background:   #0c0d14 (page), #161723 (cards), #1e2032 (alt surface)
Text:         #e2e4ea (primary), #8b8fa8 (dim/muted)
Accent:       #2563eb (blue), #1d4ed8 (hover)
Borders:      #2a2d40
Success:      #16a34a (green)
Warning:      #d97706 (orange)
Danger:       #dc2626 (red)
Radius:       10px
Shadow:       0 4px 24px rgba(0,0,0,.3)
```

### Typography
- System font stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif`
- Code/monospace: `'Cascadia Code', 'Consolas', monospace`
- Headings: white (#fff), semi-bold
- Body: 0.9-0.95rem, line-height 1.55-1.6

### Component Styles
- `.card` — dark surface, border, rounded, hover lift+glow
- `.btn` — solid blue, rounded, hover darker, disabled: 50% opacity
- `.btn-outline` — transparent, border, dim text, hover: blue border+white text
- `.badge` — small pill, colored by type
- `.tabs` — flex row of tab buttons, active tab has blue bottom border
- `.tab-panel` — hidden by default, `.active` shows it
- `.report-card` — card containing report body + actions
- `.report-body` — monospace, darker background, scrollable
- `.status-banner` — colored left border + tinted bg (info/success/error)
- `.spinner` — CSS animated circle, hidden by default, shown when parent has `.loading`
- `.download-area` — dashed border, centered content, CTA button

### Responsive
- Mobile (< 680px): cards stack vertically
- All containers have max-width + auto margins for centering
- Touch-friendly button sizes (min 12px padding)

---

## What's Already Built

| Feature | Status |
|---|---|
| Homepage two-panel layout | ✅ Done |
| Chat page with message history | ✅ Done |
| Report page with textarea + generate button | ✅ Done |
| Classification badges display | ✅ Done |
| Tabbed report display (3 tabs) | ✅ Done |
| Copy-to-clipboard with feedback | ✅ Done |
| Download button UI | ✅ Done |
| Character counter | ✅ Done |
| Loading spinner | ✅ Done |
| Error/info banners | ✅ Done |
| Shared CSS stylesheet | ✅ Done |
| Mobile responsive | ✅ Done |
| `/api/reports` endpoint | ✅ Done |
| `/api/reports/download` endpoint | ✅ Done |
| `/api/chat` endpoint | ✅ Done |

## What Could Be Improved

- Tab switching logic is fragile (relies on text matching) — could use explicit IDs
- No conversation history persistence in chat (stateless)
- Download button falls back to alert on failure — could show inline error
- No "clear chat" or "new conversation" button
- Report page could show a preview of the 005 form before download
- No dark/light mode toggle (currently dark-only)
- Could add a "saved reports" history section
- Chat could support follow-up questions (conversation context)

## File Locations

```
backend/webapp/
├── app.py                    # Flask app factory
├── static/
│   └── style.css             # Shared stylesheet
├── templates/
│   ├── home.html             # Homepage
│   ├── chat.html             # Policy expert chat
│   └── reports.html          # Report writing assistant
└── routes/
    ├── chat.py               # Chat endpoint
    └── reports.py            # Report + download endpoints
```
