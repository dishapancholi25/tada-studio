# Input Source Overlay Styling Playbook

Guidelines for building high-polish workflow configuration surfaces that match the refreshed Input Source experience.
Use these patterns whenever you design complex overlays, inspectors, or control surfaces inside the Workflow Designer.

## 1. Layout & Structure

- **Canvas Integration**: Sit overlays atop a blurred, darkened snapshot of the workflow to preserve spatial context.
  Use `bg-black/45 backdrop-blur-2xl` on the scrim, then a gradient card (`rounded-3xl`, border @ 60% opacity) for the
  container.
- **Responsive Header**: Wrap title, badges, and description in a flex block with `gap-4` and `min-w-0`. Ensure the
  supporting copy never clips by capping width (`max-w-xl`) and enabling wrapping on smaller breakpoints.
- **Sectioning**: Organize content into stacked cards (`rounded-2xl`, border + subtle gradient). Each card should have a
  clear heading (uppercase micro-label + H3) and a concise helper line.
- **Summary First**: Lead with “Active Mode” / “Quick Summary” panels so users see state before interacting. Follow with
  action sections (mode picker, selectors, advanced options).

## 2. Visual Language

- **Palette**: Use the AgenticStudio dark neutral base (`var(--color-bg-secondary)`, `var(--color-surface)`) with saturated
  accent gradients (`from-blue-500/20 via-blue-500/5 to-transparent`). Apply glows sparingly (
  `shadow-[0_20px_50px_rgba(55,115,245,0.25)]`) for selected states.
- **Glassmorphism Touches**: Combine translucent backgrounds (`bg-white/10`) with soft borders (
  `border-[color:var(--color-border)]/60`). Always layer gradients beneath to avoid flat blacks.
- **Status Badges**: Rounded-full pills, uppercase text @ 10–11px, high contrast. E.g., `bg-white/15 text-white/90` for
  neutral, `bg-[color:var(--color-accent)]/25 text-[color:var(--color-accent)]` for active states.
- **Iconography**: Lucide icons at 20–24px. Use tinted containers (`border-[color:var(--color-border)]/60`,
  `bg-[color:var(--color-bg-secondary)]/60`) and consistent color coding (blue for input, purple for multi-source,
  emerald for original input).

## 3. Interaction Patterns

- **Selectable Cards**: For multi-option controls, render each choice as a button:
  `group relative overflow-hidden rounded-2xl border px-4 py-4 text-left transition-all duration-300`. Animate
  background gradients on hover, change border + badge colors when active.
- **State Feedback**: Immediately reflect selection in summary cards and badges. Use short, plain-language copy (“Keeps
  things simple by using the last step’s result”) instead of technical jargon.
- **Toggle Treatments**: Prefer inline pill toggles (`h-6 w-11`, moving thumb) for binary options. Label with
  full-sentence tooltips (“Also include the workflow’s original request”).
- **Rich Selection Lists**: Replace default `<select>` with button cards that show icon, name, metadata badges (e.g.,
  “Subagent”, “Structured”), and a right-aligned status pill (`Active` / `Use`). Add a TL;DR callout above the list
  summarizing the current choice.

## 4. Motion & Micro-Details

- Use Tailwind utility-based animations: `animate-fadeIn`, `animate-scaleIn`, hover transitions (
  `hover:-translate-y-0.5`, `hover:shadow-[...]`). Keep durations under 200ms for snappy feedback.
- Provide consistent spacing: section gaps `space-y-6`, inner padding `p-6` or `p-5`. Align icons and text with
  `flex items-center gap-3`.
- When showing derived values (e.g., selected node names), render them as chips (
  `border-white/25 bg-black/25 px-3 py-1 text-xs`).

## 5. Copy & Tone

- **Core Principles**: Plain English, short sentences, mixed audience (technical + non-technical). Emphasize action (
  “Choose the strategy…”, “Need more context?”) and reassurance.
- **Mode Descriptions**: One-liners that explain intent, not implementation. Avoid terms like “payload” unless balanced
  with explanation.
- **Empty States**: Prefer supportive copy (“No node selected yet. Choose a source below.”).

## 6. Accessibility & Responsiveness

- Ensure contrast ratio ≥ 4.5:1 for text over translucent backgrounds. Increase text opacity (`text-white/85`,
  `text-[color:var(--color-text-muted)]`) accordingly.
- Support wrapping for long node names; clamp heights only when scrollable (`max-h-72 overflow-y-auto`).
- Provide focus styles on interactive elements (`focus:outline-none focus:border-[color:var(--color-accent)]`).
- When content exceeds viewport height, keep sticky actions in footer or repeat key actions at the bottom (e.g., Done
  button in footer card).

## 7. Implementation Cheatsheet

- **Container**:

  ```tsx
  <div className="w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden rounded-3xl border border-[color:var(--color-border)]/60 bg-gradient-to-br from-[rgba(20,25,39,0.85)] via-[rgba(12,16,25,0.92)] to-[rgba(9,12,18,0.96)] shadow-[0_30px_80px_rgba(4,7,17,0.45)]">
  ```

- **Card Scaffold**:

  ```tsx
  <section className="rounded-2xl border border-[color:var(--color-border)]/70 bg-[color:var(--color-surface)]/35 p-6 backdrop-blur-sm space-y-3">
  ```

- **Mode Button**:

  ```tsx
  <button
    className={clsx(
      'group relative overflow-hidden rounded-2xl border px-4 py-4 text-left transition-all duration-300',
      isSelected
        ? 'border-[color:var(--color-accent)]/70 shadow-[0_20px_50px_rgba(55,115,245,0.25)]'
        : 'border-[color:var(--color-border)]/60 bg-[color:var(--color-surface)]/40 hover:bg-[color:var(--color-surface)]/60'
    )}
  >
    {/* content */}
  </button>
  ```

## 8. When Extending to New Panels

1. Start with the overlay skeleton (scrim, gradient card, header).
2. Define summary cards that rephrase the node’s current settings.
3. Bundle related controls into self-contained sections.
4. Mirror the accent color scheme: reuse blue for input, green for confirmations, purple for multi-source, amber for
   advanced/custom.
5. Always provide immediate textual confirmation (badges, inline descriptions) after each interaction.

Following this playbook keeps future property overlays visually cohesive, readable, and aligned with the tech-forward
AgenticStudio aesthetic we established for the Input Source experience.
