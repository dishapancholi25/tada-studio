# Input Source Styling Guide

- Ensure modal headers that wrap input-source controls remain legible across zoom levels by pinning the header
  container (`flex-none`) and enforcing a minimum height (`min-h-[7rem]`, `lg:min-h-[8rem]`). Applied in
  `frontend/src/components/panels/properties/InputSourceOverlay.tsx` and mirrored in
  `frontend/src/components/panels/properties/EndNodePropertiesPanel.tsx`.
- Use soft rose accents for input-source overlays so they stay visually distinct from end-node greens—match the radial
  gradient, icon wrapper, badges, and primary action button to the muted red palette applied in
  `frontend/src/components/panels/properties/overlays/InputSourceOverlay.tsx`.
- Start node overlays lean on a muted lime palette to signal kickoff moments; reuse the gradient, icon casing, and CTA
  styling introduced in `frontend/src/components/panels/properties/StartNodePropertiesPanel.tsx`.
