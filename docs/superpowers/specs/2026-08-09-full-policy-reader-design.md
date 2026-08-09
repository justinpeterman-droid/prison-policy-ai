# Full Policy Reader Design

## Objective

Let an officer click any citation card in the Cited Policy pane and read the complete policy without losing the current chat. The reader presents clean, phone-friendly text, automatically scrolls to and highlights the cited passage, and offers an authenticated way to open the original PDF.

## Scope

This feature covers:

- attaching a stable policy identifier to each retrieved citation;
- securely resolving that identifier to a known corpus file;
- returning full extracted policy text on demand;
- streaming the original PDF on demand;
- a full-screen reader inside the existing chat page;
- citation matching, highlighting, loading, empty, and error states;
- desktop and mobile behavior.

It does not change answer generation, passage ranking, citation grounding, corpus ingestion, or the existing access-code model.

## User Experience

### Opening the reader

Clicking anywhere on a citation card, except its Copy control, opens the policy reader. The current conversation and citation-pane state remain in memory behind it.

The reader immediately displays a loading state, then shows:

- the complete policy title;
- a **Back to citations** control;
- an **Open original PDF** control;
- clean policy text at a readable line length;
- the cited passage marked with a gold **Cited passage** treatment.

After the document renders, the reader scrolls the highlighted passage into a comfortable position near the top of the viewport. The officer can read the rest of the policy above and below it.

### Closing and navigation

The reader closes through:

- **Back to citations**;
- the Escape key;
- the browser Back action when the reader added a history state.

Closing restores the same conversation, answer, citation list, expanded-card state, and scroll position. Opening a reader does not navigate away from `/chat` or clear any chat state.

### Responsive layout

On desktop, the reader covers the chat workspace below the main navigation. On mobile, it fills the screen below the navigation and uses a single readable column. The header remains sticky so the return and PDF actions are always available.

## Architecture

### Corpus catalog

The server builds a policy catalog from `rag_uploaded_pdfs.txt`, the repository's authoritative list of corpus filenames. Each filename receives a deterministic opaque ID derived from a SHA-256 digest. The identifier exposes neither a bucket path nor a user-controlled filesystem path.

The catalog maps:

```text
policy_id -> exact PDF filename
```

Only catalog entries can be resolved. Unknown, malformed, or colliding IDs fail closed with HTTP 404. The GCS object name is always constructed by the server as `pdfs/<catalog filename>`; client input is never joined into a path.

### Retrieval metadata

The retrieval parser preserves the document's canonical link or URI in addition to its display label and passage text. It extracts the PDF filename from that trusted search-result metadata and resolves it through the catalog.

Each citation returned by `/api/chat` gains:

```json
{
  "n": 1,
  "source": "NCU 09.13.00 Use of Force and Application of Restraints",
  "text": "The cited passage...",
  "policy_id": "opaque-stable-id",
  "full_policy_available": true
}
```

`policy_id` is omitted and `full_policy_available` is false when a retrieved result cannot be mapped safely. Existing citation consumers remain compatible because the current fields are unchanged.

### Policy endpoints

Two authenticated routes are added to the chat blueprint.

#### `GET /api/policies/<policy_id>`

Returns:

```json
{
  "policy_id": "opaque-stable-id",
  "title": "Policy title",
  "text": "Complete extracted text...",
  "pdf_available": true
}
```

The server resolves the ID through the catalog, downloads the matching PDF from the existing policy GCS bucket, and extracts text with PyMuPDF. Text extraction is performed only when requested. A bounded in-process cache avoids repeatedly downloading and extracting the same policy within a Cloud Run instance.

The cache has a fixed entry limit and stores only corpus documents, not officer questions or chat content.

#### `GET /api/policies/<policy_id>/pdf`

Streams the cataloged PDF inline with the correct `application/pdf` content type and a safe filename. The route does not redirect to GCS or expose signed credentials, bucket names, or internal object paths.

Both routes inherit the application's existing authentication gate.

### Text extraction limitations

If the PDF contains no usable text layer, the text endpoint returns a typed `text_unavailable` response with HTTP 422 and confirms whether the original PDF is available. The UI retains the cited excerpt and offers **Open original PDF**. OCR is not added to the request path because it would make the interaction slow and expensive; corpus OCR remains a separate ingestion concern.

## Citation Location and Highlighting

The browser normalizes the citation excerpt and full policy text for matching by:

- decoding HTML entities;
- collapsing whitespace;
- stripping retrieval-only ellipsis markers;
- comparing case-insensitively.

The client first attempts an exact normalized substring match. If that fails, it searches for a distinctive contiguous window from the citation. The matching threshold must avoid highlighting unrelated boilerplate.

When a safe match is found, the reader splits the display into text before, the highlighted cited span, and text after. All content is inserted as text, never as HTML. If no safe match is found, the full policy opens at the top with: **Cited passage could not be located exactly in this file. The excerpt remains available in Cited Policy.**

## Component Boundaries

### Backend

- `policy_catalog`: parses the corpus list, creates stable IDs, and safely resolves IDs and document metadata.
- `policy_store`: fetches a cataloged PDF, extracts and caches text, and streams PDF bytes.
- chat retrieval metadata: carries the canonical document reference through passage selection and citation post-processing.
- chat routes: exposes the two authenticated read-only endpoints and maps typed failures to HTTP responses.

Each component has one responsibility and can be tested independently without a live Vertex or GCS call.

### Frontend

- citation-card rendering: marks cards as readable only when `full_policy_available` is true and passes the selected citation to the reader.
- reader state: tracks loading, ready, text-unavailable, and error states.
- passage locator: pure matching function returning a safe text range or no match.
- reader overlay: owns rendering, focus, keyboard handling, history state, and restoration.

## Accessibility

- Citation cards are keyboard-operable buttons or expose equivalent button semantics.
- The reader is a labelled modal region with focus moved to its heading on open.
- Focus returns to the originating citation card on close.
- Escape closes the reader.
- Highlighting uses a label and border in addition to color.
- Text and controls meet the existing high-contrast navy/gold visual language.
- Motion respects `prefers-reduced-motion`.

## Error Handling

- **Unknown or malformed ID:** HTTP 404; reader shows “Policy file unavailable.”
- **Cataloged object missing:** HTTP 404 and server-side structured log.
- **Storage unavailable:** HTTP 503 with the existing request ID pattern; reader can retry.
- **Text extraction unavailable:** HTTP 422; reader preserves the excerpt and offers the PDF.
- **PDF stream failure:** standard error page or JSON response without exposing storage details.
- **No policy mapping on a citation:** card continues to expand its excerpt but does not claim that the full file is available.

## Security and Privacy

- No arbitrary filenames, paths, object names, or URLs are accepted from the client.
- Only allowlisted corpus IDs resolve.
- GCS access remains server-side under the Cloud Run service identity.
- PDF responses use safe content headers and filenames.
- Document text is escaped and rendered as text content.
- Endpoints are read-only and protected by the same session gate as `/chat`.
- Logs contain policy IDs and request IDs, not officer questions or access codes.

## Testing Strategy

### Backend unit tests

- catalog IDs are deterministic and resolve only allowlisted filenames;
- malformed and unknown IDs fail closed;
- search-result metadata maps to the correct policy ID;
- citation post-processing preserves the policy metadata;
- text endpoint returns complete extracted text and safe metadata;
- PDF endpoint returns inline PDF bytes and safe headers;
- missing object, storage failure, and text-unavailable cases produce the specified statuses;
- cache bounds and repeated-read behavior are deterministic.

### Frontend contract and behavior tests

- citations with full-policy metadata render as readable controls;
- clicking a card opens the reader while Copy does not;
- loading, ready, unavailable, and error states render correctly;
- exact and normalized passage matches return the correct range;
- unsafe or absent matches return no range;
- Escape, Back, and the visible control close the reader;
- focus and scroll state are restored.

### Regression and visual verification

- run the complete Python test suite;
- verify the existing citation accordion and Copy behavior;
- verify desktop and mobile reader layout in the browser;
- confirm the highlighted passage and surrounding full-policy text against a known use-of-force policy;
- confirm the original PDF opens through the authenticated application route.

## Acceptance Criteria

1. Clicking an available citation card opens the complete policy in a full-screen in-page reader.
2. The cited passage is automatically located, highlighted, and scrolled into view when safely matchable.
3. The entire extracted policy is readable above and below the citation.
4. The original PDF opens through an authenticated application endpoint.
5. Closing the reader restores the untouched chat and citation state.
6. Unknown IDs and missing files cannot expose arbitrary storage objects or paths.
7. Scanned/no-text policies fall back clearly to the original PDF.
8. Existing chat, grounding, citation expansion, and Copy behavior continue to work.
9. The full automated test suite passes and the reader is verified at desktop and mobile widths.
