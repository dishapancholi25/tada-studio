# Ultimate UI Design Reference

> **Purpose**  
> A single, opinionated reference for every future workflow UI refresh. It combines the original `design-philosophy.md` guidance
with the practical patterns we just proved out in the node execution panel redesign (typography, gradients, borders, shadows, layout and tabs).

## 1. Design Tenets

1. **Theme-aware everything** – never hardcode color values. Always consume CSS tokens such as `var(--color-primary)` or `rgba(var(--color-primary-rgb),0.2)`.
2. **Neutral base, vivid accents** – backgrounds must be pure greys (equal RGB values). The theme’s primary color provides all of the visual identity.
3. **Consistent border system** – major shells use `border-2 border-[color:var(--color-primary)]/30`. Secondary cards use `border border-[color:var(--color-border)]/70`.
4. **Depth through gradients** – combine dark-to-darker grey fills with translucent primary glows for separation rather than stacking flat solids.
5. **Hierarchy by spacing** – rely on Tailwind’s 4/6/8 spacing rhythm (16/24/32px) plus generous rounding (24–32px) to communicate groupings.
6. **Typographic discipline** – headings use uppercase tracking (`tracking-[0.35em]`) for section labels, and sentence case for content. Maintain consistent type scales (0.6rem labels, 0.9–1rem body, 1.5–2rem titles).
7. **Interactive polish** – every interactive element gets transition rules, hover states, and focus-visible outlines tied to `rgba(var(--color-primary-rgb),0.45)`.

## 2. Color System & Tokens

| Token | Usage |
| --- | --- |
| `--color-bg-primary` / `--color-bg-secondary` | Page background + panel interior gradients |
| `--color-surface` / `--color-surface-hover` | Card fills and hover states |
| `--color-border`, `--color-border-hover` | Neutral border defaults |
| `--color-primary`, `--color-primary-light`, `--color-primary-rgb` | Highlights, glows, gradients |
| `--color-text-primary`, `--color-text-secondary`, `--color-text-muted` | Typography |
| `--button-primary-text` | **Only** for buttons that use pure primary gradients (e.g., CTA) |

**Opacity ladder** – stick to `{5, 8, 10, 12, 15, 20, 25, 30, 35, 50, 70}%` to keep transparency consistent.

## 3. Surface Construction

### 3.1 Modal / Shell

```tsx
<div className="rounded-[30px] border-2 border-[color:var(--color-primary)]/30 bg-gradient-to-br from-[rgba(26,26,26,0.96)] via-[rgba(16,16,16,0.98)] to-[rgba(6,6,6,1)] shadow-[0_35px_120px_rgba(0,0,0,0.65)]" />
```

*Add a 1px gradient frame as an outer wrapper to create the “glass halo” seen in the Node Execution panel.*

### 3.2 Primary Cards

- Rounded 24px corners.
- `border-2` for the outermost cards, `border` for inner sections.
- Backdrop blur + tinted gradient glows:  
  `className="group relative"` + `absolute -inset-[1px] bg-gradient-to-br ... blur-xl`.

### 3.3 Secondary Cards

```tsx
className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/40 shadow-[0_20px_55px_rgba(0,0,0,0.55)]"
```

Use for metadata, badges, and empty states.

## 4. Border Gradients & Glows

1. **Outer frame** – 1px gradient wrapper, `from-[rgba(var(--color-primary-rgb),0.5)] via-transparent to-[rgba(var(--color-primary-rgb),0.18)]`.
2. **Glow veneers** – `absolute -inset-[1px] ... opacity-40 blur-xl` to add depth on hover.
3. **Status badges** – combine neutral border with translucent fill. Example:

```tsx
className="rounded-full border border-[rgba(var(--color-primary-rgb),0.45)] bg-[rgba(var(--color-primary-rgb),0.12)] text-[color:var(--color-primary-light)]"
```

Avoid `--button-primary-text` on muted badges because SYNECHRON’s dark text will disappear over dark surfaces.

## 5. Typography System

| Element | Styles |
| --- | --- |
| Section header | `text-xs uppercase tracking-[0.2em] text-[color:var(--color-text-secondary)] font-semibold` |
| Inline label | `text-[0.6rem] uppercase tracking-[0.35em] text-[color:var(--color-text-muted)]` |
| Meta copy | `text-xs text-[color:var(--color-text-secondary)]` |
| Body | `text-sm text-[color:var(--color-text-secondary)]` |
| Title | `text-2xl font-semibold text-white` |
| Status / badges | `text-[11px] font-medium` |

**Section Labels: Two Tiers**

Use **Section header** (`text-xs`) for prominent section dividers that need visibility—these are primary organizational elements like "AVAILABLE TOOLS", "CONFIGURATION", or column headers in dialogs and panels.

Use **Inline label** (`text-[0.6rem]`) for subtle metadata annotations that sit alongside content—timestamps, field labels in dense metadata panels, or secondary descriptors where the content itself is the focus.

**Tips**

- Use `font-mono` for IDs, timestamps, and numeric telemetry.
- Pair uppercase labels with supportive sentence-case descriptions (e.g., "Incoming context").
- Keep copy friendly (avoid jargon like "captured payload"; prefer "Incoming context" or "Model response").

## 6. Layout & Sectioning

### 6.1 Column Layouts

Use CSS grids with explicit tracks to maintain ratio:

```tsx
className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(260px,310px)_minmax(0,1fr)]"
```

This guarantees the center card keeps a readable width, while the sides flex.

### 6.2 Tabs & Navigation

- Default to the subtle variant (bordered pills). Only show the tab rail when there are >=2 tabs; otherwise omit to avoid redundant chrome.
- Active tab styling:

```tsx
className="border-[rgba(var(--color-primary-rgb),0.6)] bg-gradient-to-br from-[rgba(var(--color-primary-rgb),0.18)] via-[rgba(var(--color-primary-rgb),0.08)] to-transparent shadow-[0_25px_60px_rgba(var(--color-primary-rgb),0.25)]"
```

- Use badges with counts (`MessageSquare` + count) for conversation histories.

### 6.3 Interaction Sections

1. **Execution header** – icon capsule + status badge + metadata lines. Always provide an accessible close button.
2. **Selectors** – wrap buttons inside a `grid gap-2 sm:grid-cols-2` layout, each card being a `rounded-2xl border ... transition-all`.
3. **IO sections** – pair headers (label + friendly description + badge) with body surfaces that hold JSON or Markdown.

## 7. Shadows & Depth Recipes

| Purpose | Class |
| --- | --- |
| Modal shell | `shadow-[0_35px_120px_rgba(0,0,0,0.65)]` |
| Primary card | `shadow-[0_32px_85px_rgba(0,0,0,0.55)]` |
| Secondary card | `shadow-[0_20px_55px_rgba(0,0,0,0.55)]` |
| Focus glow | `shadow-[0_0_30px_rgba(var(--color-primary-rgb),0.25)]` |

Use hover states to increase opacity or scale for interactive cards (`group-hover:opacity-70`, `hover:-translate-y-0.5`).

## 8. Data & Tooling Patterns

### 8.1 JSON Viewers

- Always embed `JsonViewerEnhanced` inside a bordered card with `custom-scrollbar`.
- Provide view toggles (`Tree`, `Table`, `Raw`). Use gradient pills for the active state.
- Keep string values colored via theme accent; ensure badges/borders use primary-light text to prevent black-on-dark issues.

### 8.2 Metadata Panels

- Group metrics (duration, order, times) using dividing lines via `divide-y divide-[color:var(--color-border)]/40`.
- Token usage: stack cards for input/output, with a highlighted “Total” row using the primary gradient fill.
- Hide fields that are irrelevant (e.g., duration for START/END nodes).

### 8.3 Conversation Histories

- Layout: `flex gap-4`, `max-w-[70%]` chat bubbles.
- User bubble: gradient + primary border. Assistant bubble: neutral border + surface fill.
- Include uppercase role labels and timestamp (font-mono) for clarity.

## 9. Buttons & Controls

| Type | Styles |
| --- | --- |
| Primary CTA | `bg-gradient-to-br from-[rgba(var(--color-primary-rgb),1)] to-[rgba(var(--color-primary-rgb),0.8)] text-[color:var(--button-primary-text)] shadow-[0_15px_40px_rgba(var(--color-primary-rgb),0.35)]` |
| Secondary | `border border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/40 hover:border-[rgba(var(--color-primary-rgb),0.4)]` |
| Icon pills | `rounded-2xl border border-[rgba(var(--color-primary-rgb),0.35)] bg-[rgba(var(--color-primary-rgb),0.12)]` |

Always include focus states: `focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(var(--color-primary-rgb),0.45)]`.

## 10. Dropdown Component

The application uses a **single unified `Dropdown` component** (`frontend/src/components/ui/Dropdown.tsx`) for all select-style inputs. Do not create custom select components — use `Dropdown` everywhere.

### Import

```tsx
import Dropdown from "@/components/ui/Dropdown";
import type { DropdownOption, DropdownGroup, DropdownProps } from "@/components/ui/Dropdown";
```

### Option Interface

```tsx
interface DropdownOption {
  value: string;
  label: string;
  description?: string;   // Secondary text below label
  icon?: React.ReactNode;  // Per-option icon (left side)
  disabled?: boolean;
  customContent?: React.ReactNode; // Fully custom option rendering
}
```

Options can be provided flat (`options` prop) or grouped (`groups` prop):

```tsx
interface DropdownGroup {
  label: string;
  icon?: React.ReactNode;
  options: DropdownOption[];
}
```

### Basic Usage

```tsx
<Dropdown
  value={selectedModel}
  onChange={setSelectedModel}
  options={[
    { value: "gpt-4", label: "GPT-4", description: "Most capable" },
    { value: "gpt-3.5", label: "GPT-3.5 Turbo" },
  ]}
  placeholder="Select a model"
/>
```

### Key Props

| Prop | Type | Default | Purpose |
|------|------|---------|---------|
| `value` | `string` | — | Currently selected value |
| `onChange` | `(value: string) => void` | — | Selection callback |
| `options` | `DropdownOption[]` | `[]` | Flat option list |
| `groups` | `DropdownGroup[]` | — | Grouped options (overrides `options`) |
| `placeholder` | `string` | `"Select an option"` | Trigger placeholder text |
| `trigger` | `ReactNode` | — | Fully custom trigger element |
| `align` | `"start" \| "end" \| "center"` | `"start"` | Horizontal alignment relative to trigger |
| `side` | `"bottom" \| "top" \| "auto"` | `"auto"` | Vertical placement preference |
| `maxHeight` | `number` | `400` | Max dropdown panel height (px) |
| `width` | `number \| "trigger" \| "auto"` | `"trigger"` | Dropdown width strategy |
| `portal` | `boolean` | `true` | Render in `document.body` via portal |
| `disabled` | `boolean` | `false` | Disable interaction |
| `onAdd` | `() => void` | — | Shows an "Add New" button at the top of the panel |
| `addLabel` | `string` | `"Add New"` | Label for the add button |
| `onDelete` | `(value: string) => void` | — | Shows a delete icon on hover for non-selected options |
| `showSelectedIndicator` | `boolean` | `true` | Show checkmark on selected option |
| `className` | `string` | — | Wrapper class |
| `triggerClassName` | `string` | — | Override default trigger styles |
| `dropdownClassName` | `string` | — | Override dropdown panel styles |
| `optionClassName` | `string` | — | Override individual option styles |

### Styling Anatomy

**Trigger** (default, no `trigger` prop):

```
rounded-xl | border border-[color:var(--color-border)]/70 | bg-[color:var(--color-surface)]/40
focus: border primary/70, ring primary/25
```

**Dropdown panel** (portal-rendered, fixed position):

```
rounded-xl | border border-[color:var(--color-border)]/70 | bg-[color:var(--color-surface)]
shadow-[0_20px_55px_rgba(0,0,0,0.55)] | backdrop-blur-2xl | z-index: 9999
```

**Option rows** (no left border accent):

- Selected: `bg-[rgba(var(--color-primary-rgb),0.15)]` + checkmark icon
- Focused (keyboard): `bg-[color:var(--color-surface-hover)]`
- Hovered: `bg-[rgba(var(--color-primary-rgb),0.08)]`
- Disabled: `opacity-40 cursor-not-allowed`

### Positioning

Dropdown uses the `useDropdown` hook (`frontend/src/hooks/useDropdown.ts`) powered by `@floating-ui/react` which handles:

- Viewport-aware auto-placement (flips above trigger when space is insufficient below)
- Correct positioning at all browser zoom levels and inside transformed/blurred containers
- Width matching to trigger element (`width="trigger"`)
- Automatic repositioning on scroll, resize, and layout changes via `autoUpdate`
- Click-outside detection for closing

### Keyboard Navigation

Full ARIA listbox pattern: `ArrowDown`/`ArrowUp` to navigate, `Enter`/`Space` to select, `Escape` to close, `Home`/`End` to jump.

### Custom Triggers

Pass a `trigger` prop to fully replace the default button. The dropdown panel will still position relative to the wrapper element:

```tsx
<Dropdown
  trigger={<button className="custom-btn">Pick one</button>}
  options={myOptions}
  onChange={handleChange}
/>
```

### Collection Management Pattern

For lists that support creating and deleting items (e.g., document collections):

```tsx
<Dropdown
  value={selectedCollection}
  onChange={setSelectedCollection}
  options={collections}
  onAdd={() => openCreateDialog()}
  addLabel="Create Collection"
  onDelete={(id) => deleteCollection(id)}
/>
```

## 11. Process Checklist

1. **Scan for literal colors** – remove `bg-blue-500`, `text-white`, etc.
2. **Apply proper border weights** – modal/primary = `border-2`, sections = `border`.
3. **Add gradient/glow wrappers** when a component needs extra elevation.
4. **Align typography** – ensure every heading/subheading uses the type scale.
5. **Test in both themes** – confirm contrast (especially for badges) in EXPOSE and SYNECHRON.
6. **Verify responsive behavior** – check that grids collapse gracefully under `xl`.
7. **Run `npm run build`** – ensures Next.js compiles with the updated Tailwind classes.

## 12. Reference Implementations

- `Dropdown` – unified select component with portal positioning, keyboard nav, groups, and CRUD actions.
- `NodeExecutionPanel` – end-to-end example of modal shell, selectors, IO cards, and metadata.
- `ExecutionSelector` – token-friendly selector cards with status badges.
- `ExecutionTabNavigation` – dynamic tab rails that disappear when not needed.
- `JsonViewerEnhanced` – theme-aware data visualization with toggles.
- `ConversationHistoryTab` – balanced chat layout with gradient accents.

---

Use this document as the canonical reference when planning any UI modernization. Every new component should be checked against these sections before shipping.*** End Patch
