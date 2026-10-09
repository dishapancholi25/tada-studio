# Wiki Feature — Remaining Improvements

## Context

After completing the security fixes (SimpleMarkdown.tsx XSS + debug logging) and the
backend service refactor (routes.py to handler pattern), these are the remaining
improvements identified during the wiki feature review.

## Completed (for reference)

- [x] XSS fix in SimpleMarkdown.tsx — replaced `insertAdjacentHTML` with React state
- [x] Debug logging cleanup — removed 11 console statements
- [x] Backend service refactor — 776-line routes.py to 9 files matching graph module pattern

---

## 1. Frontend API Service Layer [HIGH]

**Problem:** All wiki pages make inline `fetch()` calls with duplicated URL construction,
error handling, and response parsing. No type safety on responses.

**Current inline fetch locations:**

- `frontend/src/app/wiki/page.tsx` — `fetch("/api/wiki/pages")`
- `frontend/src/app/wiki/[slug]/page.tsx` — `fetch("/api/wiki/pages/${slug}")`, revisions
- `frontend/src/app/wiki/[slug]/edit/page.tsx` — PUT/POST to `/api/wiki/pages`
- `frontend/src/app/wiki/[slug]/history/page.tsx` — revisions, restore
- `frontend/src/components/wiki/WikiSidebar.tsx` — `/api/wiki/tree`, `/api/wiki/search`

**Plan:** Create `frontend/src/services/wikiApi.ts` with typed methods:

```typescript
// Pages
getPages(params?: { includeUnpublished?, parentId?, tag? }): Promise<WikiPageListItem[]>
getPage(slug: string): Promise<WikiPageResponse>
createPage(data: WikiPageCreate): Promise<WikiPageResponse>
updatePage(slug: string, data: WikiPageUpdate): Promise<WikiPageResponse>
deletePage(slug: string): Promise<void>

// Revisions
getRevisions(slug: string): Promise<WikiRevision[]>
restoreRevision(slug: string, version: number): Promise<WikiPageResponse>

// Search & Tree
searchPages(query: string, params?: { limit?, includeUnpublished? }): Promise<WikiPageListItem[]>
getPageTree(includeUnpublished?: boolean): Promise<WikiTreeNode[]>

// Images
uploadImage(file: File): Promise<{ id: string; url: string }>
```

**Files to modify:**

- **Create:** `frontend/src/services/wikiApi.ts`
- **Modify:** 5 files above to replace inline fetches with service calls

**Pattern reference:** `frontend/src/services/graphSyncService.ts`

---

## 2. Revision Diff View [HIGH]

**Problem:** History page shows a flat list of revisions with truncated content previews.
No way to see what actually changed between versions.

**Current state:** `frontend/src/app/wiki/[slug]/history/page.tsx` fetches revisions and
displays version, date, creator, change summary, and 240-char content snippet. Backend
already supports fetching individual revisions via
`GET /api/wiki/pages/{slug}/revisions/{version}`.

**Plan:**

- Add `diff` npm package (lightweight, no heavy UI library needed)
- Add expandable diff panel per revision in history page
- On expand: fetch current revision content + previous revision content, compute
  word-level diff
- Render unified diff with green/red highlighting using CSS variables from design system
- No backend changes needed — both revisions already fetchable

**Files to modify:**

- **Modify:** `frontend/package.json` — add `diff` package
- **Modify:** `frontend/src/app/wiki/[slug]/history/page.tsx` — add diff expansion UI
- **Create:** `frontend/src/components/wiki/WikiDiffView.tsx` — reusable diff renderer

---

## 3. Page Hierarchy Management [HIGH]

**Problem:** Backend supports `parent_id` for page hierarchy, but the frontend editor has
no UI to set/change parent pages. Users can only create flat pages.

**Current state:**

- `WikiSaveData` interface in `WikiPageEditor.tsx:25-30` has `title`, `content`, `tags`,
  `changeSummary` — no `parent_id`
- Backend `WikiPageCreate`/`WikiPageUpdate` models accept `parent_id`
- WikiSidebar already renders the tree structure correctly
- Backend has `WikiSelfParentError` but no deep circular dependency check

**Plan:**

- Add `parentId` to `WikiSaveData` interface
- Add parent page selector dropdown to `WikiPageEditor.tsx` (fetch pages via tree
  endpoint, exclude current page and its descendants)
- Pass `parent_id` through from new/edit pages to API calls
- Backend: add ancestor loop detection in `handle_update_page` (walk parent chain,
  reject if cycle found)

**Files to modify:**

- **Modify:** `frontend/src/components/wiki/WikiPageEditor.tsx` — add parent selector
  UI + interface field
- **Modify:** `frontend/src/app/wiki/new/page.tsx` — pass parentId to create API call
- **Modify:** `frontend/src/app/wiki/[slug]/edit/page.tsx` — pass parentId to update
  API call
- **Modify:** `backend/api/wiki/handlers/page_crud.py` — add circular parent detection
  in `handle_update_page`

---

## 4. GIN Search Index [MEDIUM]

**Problem:** `search_vector` TSVECTOR column exists on `wiki_pages` but has no GIN index.
Full-text search works but will degrade at scale as it does a sequential scan.

**Current state:**

- `backend/models/wiki/page.py:50` — `Column(TSVECTOR, nullable=True)`
- `backend/api/wiki/handlers/search.py` — uses `to_tsquery()` + `ts_rank()` for search
- No index creation in `backend/services/database/migrations/`

**Plan:** Add migration to create GIN index:

```sql
CREATE INDEX IF NOT EXISTS idx_wiki_pages_search_vector
  ON wiki_pages USING GIN (search_vector);
```

**Files to modify:**

- **Modify:** `backend/services/database/migrations/schema_updates.py` — add GIN index
  creation
- **Modify:** `backend/services/database/migrations/registry.py` — register migration

---

## 5. Breadcrumb Navigation [MEDIUM]

**Problem:** Pages with parent relationships don't show their position in the hierarchy.
Only a "Back to page" link exists on the history page. No way to navigate up the tree
from a page view.

**Current state:**

- Wiki layout (`frontend/src/app/wiki/layout.tsx`) has no breadcrumb section
- Page response already includes `parent_id` — can walk up the chain
- Tree endpoint returns full hierarchy

**Plan:**

- Create `WikiBreadcrumb` component that takes current page data
- Walk parent chain using page data from tree endpoint (already fetched by sidebar)
- Render: `Wiki > Parent Title > Current Title`
- Add to `frontend/src/app/wiki/[slug]/page.tsx` above the page title

**Files to modify:**

- **Create:** `frontend/src/components/wiki/WikiBreadcrumb.tsx`
- **Modify:** `frontend/src/app/wiki/[slug]/page.tsx` — add breadcrumb above title

---

## 6. Sidebar Accessibility [MEDIUM]

**Problem:** WikiSidebar and WikiTableOfContents lack ARIA attributes, keyboard
navigation, and proper semantic roles. Not usable with screen readers or keyboard-only
navigation.

**Current state:**

- `WikiSidebar.tsx` — basic `<aside>`, `<button>`, `<input>` without ARIA
- Tree nodes use `<li>` but no `role="treeitem"`, `aria-expanded`, or keyboard handlers
- Mobile overlay has no focus trap or `role="dialog"`
- Search input has no `aria-label`
- `WikiTableOfContents.tsx` — has `<nav>` but no `aria-current` on active item

**Plan:**

- Add `role="tree"` to tree container, `role="treeitem"` to nodes
- Add `aria-expanded` to collapsible tree nodes
- Add `aria-current="page"` to active node
- Add `aria-label` to search input and navigation regions
- Add keyboard handlers: arrow keys for tree navigation, Enter to select
- Add focus trap for mobile overlay using existing `useFocusTrap` hook from
  `@/hooks/useAccessibility`
- Add `role="dialog"` and `aria-modal="true"` to mobile overlay

**Files to modify:**

- **Modify:** `frontend/src/components/wiki/WikiSidebar.tsx`
- **Modify:** `frontend/src/components/wiki/WikiTableOfContents.tsx`

**Reusable:** `useFocusTrap`, `useEscapeKey` from
`frontend/src/hooks/useAccessibility.ts`

---

## Priority Order

| # | Improvement | Priority | Effort | Dependencies |
|---|-------------|----------|--------|--------------|
| 1 | Frontend API Service | HIGH | Medium | None |
| 2 | Revision Diff View | HIGH | Medium | Benefits from #1 |
| 3 | Page Hierarchy UI | HIGH | Medium | Benefits from #1 |
| 4 | GIN Search Index | MEDIUM | Small | None |
| 5 | Breadcrumb Navigation | MEDIUM | Small | Benefits from #3 |
| 6 | Sidebar Accessibility | MEDIUM | Medium | None |

Recommended execution: #1 first (all other frontend work benefits), then #4 (quick win),
then #2 and #3 in either order, then #5 and #6.
