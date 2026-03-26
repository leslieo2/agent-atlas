# Frontend Design Language

This document defines the visual and interaction language for the Agent Atlas frontend.

The current style direction is:

`Mission Control / Control Room Dashboard`

In practice, this means a calm dark workspace with strong hierarchy, restrained accents, and dense but readable operational information. The interface should feel like a tool for running, inspecting, and diagnosing work, not a marketing site and not a generic SaaS card grid.

## Product Fit

This product is an operator-facing workbench. Users need to:

- scan current state quickly,
- compare runs, agents, and traces,
- move between work surfaces without losing context,
- notice failures and blocked states immediately,
- act from the same screen where they observe.

Because of that, the UI should optimize for orientation, status, and action before personality or decoration.

## Core Principles

### 1. Workspace First

Every page should feel like part of one connected control surface.

- The shell provides continuity.
- The page header provides context.
- The primary workspace carries the main task.
- Secondary panels support inspection, not competition.

Do not design each page as an isolated visual concept.

### 2. Calm, Not Loud

The interface may feel technical and premium, but it should not become theatrical.

- Prefer low-chroma dark surfaces.
- Use one accent color family by default.
- Keep shadows subtle or remove them entirely when layout already creates separation.
- Use motion to stage hierarchy, not to decorate.

Avoid cyberpunk excess, glassmorphism-heavy blur, and colorful multi-accent UI.

### 3. Status Is The Accent

Color should mostly be reserved for meaning.

- Accent blue: orientation, active navigation, structural emphasis.
- Green: success / healthy state.
- Yellow: running / pending / warning.
- Red: failure / invalid / destructive state.

If everything is accented, nothing is accented.

### 4. Layout Before Cards

This frontend should not default to card mosaics.

- Use spacing, columns, section dividers, and typography first.
- Use panels when a region needs its own interactive or semantic container.
- Use cards only when the item itself is the interaction unit.

Good examples:

- run list table
- step inspector list
- agent item rows/cards inside a section
- summary metrics as compact strips

Bad examples:

- dashboard made entirely of unrelated floating tiles
- hero section built from nested cards
- every subsection boxed without a semantic reason

### 5. One Dominant Idea Per Section

Each region should do one job.

- Header: orient
- Metric strip: summarize
- Filters: narrow scope
- Table: browse and select
- Inspector: inspect deeply

If a section tries to explain, summarize, and convert at the same time, split it.

## Visual Character

### Style Keywords

- control room
- local-first operations workbench
- dark analytical surface
- restrained futuristic
- technical but calm

### Tone To Avoid

- glossy landing page
- startup marketing dashboard
- fintech card wall
- neon sci-fi interface
- skeuomorphic “hardware panel” styling

## Typography

Typography is one of the main hierarchy tools in this system.

- `Manrope` is the default reading and UI font.
- `Space Grotesk` is the display font for titles and key numeric emphasis.
- `IBM Plex Mono` is for IDs, logs, code-like output, and technical values.

Rules:

- Product and page titles should be the loudest text.
- Section headings should be short and operational.
- Supporting copy should explain scope or behavior in one sentence.
- Monospace should be used selectively, not for whole sections of UI text.

## Color And Tokens

The source of truth for current tokens is [`app/globals.css`](./app/globals.css).

### Base Palette

- Background: very dark navy, not pure black
- Surface: slightly lighter dark blue-gray
- Text: cool near-white
- Muted text: blue-gray
- Accent: cyan-blue

### Meaning Palette

- `--success`: success / valid / healthy
- `--warning`: running / pending / caution
- `--danger`: failed / invalid / destructive

### Surface Strategy

Use three levels of surface emphasis:

- page background
- shared panel / workspace surface
- emphasized surface for primary region or current focus

The difference between levels should come mostly from contrast and border tuning, not from large shadow jumps.

## Spacing And Shape

The UI should feel engineered and measured.

- Large page regions use generous outer spacing.
- Dense controls inside those regions should still retain breathing room.
- Corners should be rounded, but not toy-like.
- Bigger containers may use larger radii than inner controls.

Current shape language:

- large page/header containers: `--radius-xl`
- panels and metric surfaces: `--radius-lg`
- controls and smaller feedback regions: `--radius-md` / `--radius-sm`

## Motion

Motion is allowed, but only in service of clarity.

Recommended:

- soft header entrance
- metric strip stagger
- hover feedback on navigation and item surfaces

Rules:

- keep transitions short,
- prefer opacity/translate over complex transforms,
- respect `prefers-reduced-motion`,
- never block content visibility behind animation timing.

Avoid scroll-jacking, floating decorative animation, and flashy chained effects.

## Page Composition

### Application Shell

The shell defines the product identity.

- Left rail is persistent orientation, not a secondary dashboard.
- Navigation labels must be direct and operational.
- Active page state should be obvious from the rail alone.
- The shell should stay visually quieter than the active workspace.

### Page Header

Each page header should include:

- small eyebrow label
- strong page title
- one-sentence kicker
- optional tag chips for quick context
- one compact context block or action cluster on the right

The page header is not a marketing hero. It should orient in seconds.

### Metric Strip

Metric strips are quick summaries, not showcase cards.

- keep them compact,
- avoid long prose inside them,
- emphasize number first and label second,
- use them for scan value, not explanation.

### Primary Workspace

The primary workspace is where the page earns its keep.

Examples:

- filters + runs table
- run graph
- playground controls

This area should always dominate over decorative surfaces.

### Secondary Workspace

Secondary regions should support the main task.

- trace output
- step inspector
- status side panel

They should be easier to ignore until needed.

## Component Guidance

### Buttons

- Primary buttons should be used for the main action of the current area.
- Secondary and ghost buttons should dominate overall count.
- A toolbar with too many primary buttons is a hierarchy failure.

### Panels

Panels are workspace containers, not presentation cards.

Use a `strong` panel only when the area is the main active workspace.

### Metric Cards

Metric cards should read like instrument readouts.

- short labels
- strong values
- minimal body text

### Status Pills

Status pills are semantic signals.

- keep copy short
- prefer system states over editorial wording
- do not use status pills as generic tags

### Tables

Tables are a first-class pattern in this product.

- retain strong column labels,
- keep row hover subtle,
- allow dense data without feeling cramped,
- reserve accent usage for links and states.

### Forms And Filters

Filters should feel integrated into the workspace, not like a separate settings screen.

- group by task relevance
- keep field labels compact
- use full-width controls
- avoid visual noise around basic inputs

## Content Style

This product should use utility copy, not campaign copy.

Good:

- Runs unavailable. Check the API connection and try again.
- Select a run to inspect its trajectory and execution details.
- Valid repository plugins that are not yet exposed.

Bad:

- Unlock deeper observability for your agent ecosystem.
- Supercharge your trace intelligence.
- Explore the future of AI operations.

If a sentence sounds like homepage copy, rewrite it.

## Responsive Behavior

Mobile should preserve hierarchy, not just stack everything blindly.

- The shell may collapse vertically, but orientation must remain clear.
- Page headers should keep title prominence.
- Toolbars should wrap cleanly.
- Metric strips should collapse without becoming oversized tiles.
- Secondary regions should fall below the primary workspace in a predictable order.

## Red Flags

Avoid these regressions:

- generic SaaS card mosaics
- multiple competing accent colors
- oversized shadows doing the work of layout
- decorative panels with no semantic role
- long descriptive paragraphs inside metrics
- page headers that read like marketing heroes
- every region visually equally loud

## Implementation Notes

- Global visual tokens live in [`app/globals.css`](./app/globals.css).
- Shell styling lives in [`src/widgets/workbench-shell/WorkbenchShell.tsx`](./src/widgets/workbench-shell/WorkbenchShell.tsx) and its CSS module.
- Shared surface primitives live in `src/shared/ui/`.
- Page-level visual orchestration belongs in `src/widgets/`.

When making UI changes, prefer updating shared primitives or page composition patterns before introducing one-off styling.

## Litmus Check

A new page or refactor should pass these questions:

- Can the user identify the current workspace in one glance?
- Is the main task area visually dominant?
- Does the page read clearly in grayscale except for status cues?
- Are accents mostly reserved for action and state?
- Would the interface still feel coherent if most shadows were removed?
- Does the page still feel like the same product as Runs, Agents, Playground, and Trajectory?
