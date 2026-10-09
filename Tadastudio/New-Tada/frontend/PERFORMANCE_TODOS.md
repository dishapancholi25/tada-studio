# Performance Optimization TODOs

Optional improvements for agent builder FPS/smoothness. Work through these incrementally.

---

## 1. ~~Add React Flow Virtualization (High Impact for Large Graphs)~~ ✅ DONE

**File:** `src/components/core/shared/GraphCanvas.tsx`

**Completed:** Added `onlyRenderVisibleElements`, `minZoom`, and `maxZoom` props.

---

## 2. ~~Use requestAnimationFrame for Drag (Smoother 60fps)~~ ✅ DONE

**File:** `src/components/core/AgentBuilder.tsx`

**Completed:** Added `dragRafRef` and wrapped `handleNodeDrag` logic in rAF with cleanup in `handleNodeDragStop`.

---

## 3. ~~Memoize getGradientColors in Remaining Node Components~~ ✅ DONE

**Completed:** Memoized `gradientColors` with `useMemo` in all 13 node components:

- [x] `FlowNode.tsx`
- [x] `ConditionNode.tsx`
- [x] `SubWorkflowNode.tsx`
- [x] `HttpRequestActionNode.tsx`
- [x] `DatabaseInsertNode.tsx`
- [x] `EmailSendNode.tsx`
- [x] `FileReadNode.tsx`
- [x] `tools/EmailSendToolNode.tsx`
- [x] `tools/FileWriteNode.tsx`
- [x] `tools/DocumentSearchNode.tsx`
- [x] `tools/WebSearchNode.tsx`
- [x] `tools/DatabaseQueryNode.tsx`
- [x] `tools/HttpRequestNode.tsx`

---

## 4. ~~Extract Shared Gradient Utility (DRY Improvement)~~ ✅ DONE

**File:** `src/components/nodes/shared/getExecutionGradient.ts`

**Completed:** Created shared utility with theme-based gradients (emerald, purple, amber, blue, orange, teal).

Updated 12 node components to use the shared utility:

- [x] `tools/HttpRequestNode.tsx` (emerald)
- [x] `tools/DatabaseQueryNode.tsx` (purple)
- [x] `tools/WebSearchNode.tsx` (amber)
- [x] `tools/DocumentSearchNode.tsx` (blue)
- [x] `tools/FileWriteNode.tsx` (amber)
- [x] `tools/EmailSendToolNode.tsx` (emerald)
- [x] `FileReadNode.tsx` (orange)
- [x] `EmailSendNode.tsx` (emerald)
- [x] `DatabaseInsertNode.tsx` (emerald)
- [x] `HttpRequestActionNode.tsx` (emerald)
- [x] `ConditionNode.tsx` (amber)
- [x] `SubWorkflowNode.tsx` (teal)

**Skipped:** `FlowNode.tsx` (uses config-based colors for multiple node types)

---

## 5. ~~Batch Store Position Updates (Advanced)~~ ✅ DONE

**Files:**

- `src/stores/graphStore.ts`
- `src/components/core/AgentBuilder.tsx`

**Completed:**

- Added `batchUpdateNodePositions` method to graphStore.ts
- Updated `handleNodeDrag` to collect all position updates and call batch method once
- Reduces N store updates to 1 per drag frame when dragging parent with children

---

## 6. ~~Memoize edgeStyle in ConditionEdge~~ ✅ DONE

**File:** `src/components/edges/ConditionEdge.tsx`

**Completed:** Memoized `edgeStyle` with `useMemo`.

---

## Verification After Each Change

```bash
cd frontend
npm run type-check && npm run lint && npm test
```
