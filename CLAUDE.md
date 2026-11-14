# Labhya Compute

A marketplace for renting GPUs by the hour. Hosts run a Windows desktop agent that starts a Docker container; renters SSH into it through a Cloudflare tunnel the API manages (`backend/app/cloudflare.py`). Hosts never deal with Cloudflare. See README.md for architecture and setup.

- `backend/app/` — FastAPI + SQLModel API. `backend/agent/` — host agent (Tkinter). `frontend/` — Next.js 15, Tailwind v4, shadcn/ui.
- Money is in NPR, written `Rs 150` (space, no decimals unless the value has paise). Prices are per hour: `Rs 150/hr`.
- Local dev: in `backend/`, `uv sync`, `uv run fastapi dev` (it applies migrations on start). Then `uv run python seed_dev.py` creates a test host (two GPUs) and a test renter with funds. Deploying to FastAPI Cloud is in the README.
- The agent's Python source is never served from the website. Hosts download only the built `.exe` files from `frontend/public/downloads/`.
- Payments are simulated. Don't build UI that implies real money moves (no card forms, no "secure payment" badges) until real payments exist.

## Backend rules

- Dependencies are pinned in `backend/pyproject.toml` and locked in `uv.lock`. Add one with `uv add pkg==x.y.z`, never by editing a requirements file (there isn't one).
- **Every model change ships with an Alembic migration** in the same commit: `uv run alembic revision --autogenerate -m "..."`, then read and fix the generated file. Never call `create_all`. `pytest` fails when models and migrations differ.
- All timestamps are timezone-aware UTC from `app.models.utcnow()`.
- Money is `Decimal`, never float. Wallet balances change only through `app/billing.py` (`wallet_of` locks the row, `post` records a transaction). Billing functions don't commit; the route commits once, so a request is one transaction.
- Request bodies inherit `schemas.Strict` (unknown fields rejected) and constrain every string length and number range. Every route that returns data declares a `response_model`.
- Resources that belong to someone else return 404, not 403, so IDs can't be probed.
- Error `detail` messages follow "Writing for the UI" below: they are shown to users as written. Never put exception text in a response.
- Production-only checks live in `Settings._check` in `app/config.py`. A new secret or required setting gets a check there and a row in the README configuration table.
- `uv run pytest` must pass on SQLite and on PostgreSQL (`TEST_DATABASE_URL`). New behaviour gets a test in `backend/tests/`.

## Frontend structure

- The web app is a static export (`output: "export"`), served by the API from `backend/static/` (`pnpm build:api`). Don't use anything that needs a Node server: route handlers, middleware, server actions, `next/headers`, or dynamic routes without `generateStaticParams`. Data comes from the API in the browser.

- `lib/api.ts` is the only place that calls the API, and only endpoints that exist in `backend/app/routers/`. If you need data the API doesn't return, add the endpoint first (with a test in `backend/tests/`).
- `lib/types.ts` mirrors `backend/app/schemas.py`. Keep them in sync.
- `lib/auth-store.ts` holds tokens and the current user from `GET /api/auth/me/` (role is `HOST` or `RENTER`).
- `lib/use-load.ts` loads page data and can poll; there is no global data store.
- Every logged-in page is wrapped in `<AppShell>` (`components/app/shell.tsx`); pass `only="HOST"` or `only="RENTER"` for role-specific pages.
- Shared page pieces (header, stats, tables, empty/error states, copy fields, money and time formatting) live in `components/app/ui.tsx`. Use them before writing new ones.

---

# Design system

Every frontend change follows this section. If a design calls for something this section forbids, change the design, not the rules. If a rule must change, change it here first, in the same commit.

**Feel:** a dark server room. Pure black page, white text, and one electric green used only for small accents and data. Depth comes from stacked near-black surfaces, never from shadows or glows.

**Dark only.** There is no light mode. Don't add `dark:` variants or a theme switcher.

## Colors

Tokens are defined in `frontend/app/globals.css` and exposed as Tailwind utilities (`bg-blackout`, `text-ash`, `border-graphite-light`, `text-neon-glow`, ...). Use these names. Never write raw hex values, and never use Tailwind's stock palettes (`slate-*`, `zinc-*`, `emerald-*`, `indigo-*`, ...).

| Token | Hex | Use for |
|---|---|---|
| `blackout` | `#000000` | Page and section backgrounds. |
| `depth` | `#0a0a0b` | Sidebars, sticky header fill, the lowest raised surface. |
| `graphite-deep` | `#151617` | Cards, code blocks, table containers, dialogs. |
| `graphite` | `#242628` | Surfaces on top of cards: hovered rows, selected tabs, input fills. |
| `graphite-light` | `#303236` | Borders and dividers. The only border color. |
| `whiteout` | `#ffffff` | Primary text, headings, icons, the primary button fill. |
| `cloud` | `#c9cbcf` | Hover state for gray text and icons. |
| `pewter` | `#94979e` | Tertiary text: metadata, timestamps, placeholders. |
| `ash` | `#797d86` | Secondary text: descriptions, inactive nav links, table headers. |
| `neon-glow` | `#34d59a` | Accent only (see below). |
| `neon-muted` | `#285d49` | Quiet green: chart fills, selected-row tint, progress tracks. |
| `system-warning` | `#ff3621` | Errors and destructive actions only. |

The shadcn roles (`bg-background`, `text-muted-foreground`, `bg-card`, `border`, `bg-primary`, ...) are mapped onto these tokens, so shadcn components already comply.

**Green (`neon-glow`) is allowed for:** status dots on real statuses ("Online", "Active"), the selected state of tabs and filters, focus rings, chart lines, prompt text in terminal blocks, and inline highlights inside code. It is never decoration. **Green is never used for:** body text, headings, button fills, large areas, or backgrounds bigger than a badge.

**Red (`system-warning`) is allowed for:** error messages, failed status, and destructive buttons ("Delete GPU", "End session"). Nothing else. There are no other colors: no blue for info, no yellow for warnings. Use white or ash text for neutral notices.

## Typography

- **Inter** (`font-sans`, the default) for headings, body copy and button labels. Weights 400 and 500 only. Don't use `font-semibold` or `font-bold`; use `font-medium` for emphasis.
- **Geist Mono** (`font-mono`) for code, terminal output, SSH commands, IDs, ports and numeric data in tables. Not for labels or headings.
- Never mix Inter and Geist Mono inside one sentence or heading. A command inside a paragraph goes in its own `<code>` element.

Use the type-scale utilities. Each one sets size, line height and letter spacing together, so don't add `leading-*` or `tracking-*` next to them.

| Utility | Size | Use for |
|---|---|---|
| `text-display` | 80px | The single landing-page hero headline. Drop to `text-heading-lg` on phones. |
| `text-heading-lg` | 48px | Landing-page section headings. |
| `text-heading` | 32px | App page titles ("Sessions", "Wallet"). |
| `text-heading-sm` | 24px | Card and dialog titles, stat values. |
| `text-subheading` | 18px | Lead paragraphs under headings. |
| `text-body` | 16px | Default body copy. |
| `text-body-sm` | 14px | UI text: table cells, form labels, buttons, nav. |
| `text-caption` | 12px | Metadata, helper text, table headers. |

No uppercase text anywhere, and no small labels above section headings. A heading stands on its own.

## Shape, spacing, depth

- **Buttons are pills** (`rounded-full`). **Everything else has 4px corners**: cards, inputs, selects, dialogs, code blocks, badges, tables. `rounded-sm/md/lg/xl` all resolve to 4px; never use larger radius values.
- **No shadows** (`shadow-*`), no glows, no blur halos. Show elevation by placing a lighter surface on a darker one: `graphite-deep` on `blackout`, `graphite` on `graphite-deep`.
- **No gradients** on sections, cards, text or buttons. The only allowed decoration is the abstract line graphic described under Imagery.
- Spacing uses Tailwind's default 4px scale (`p-6` = 24px). Card padding is `p-6`. Gaps between related elements are `gap-2` to `gap-4`.
- Content width is `max-w-[1200px] mx-auto px-4 sm:px-6`. Landing-page sections are separated by vertical space (`py-24` to `py-32`), not by borders or background changes.
- Header: sticky, `bg-blackout/80 backdrop-blur`, bottom border `border-graphite-light`.

## Components

| Component | Spec |
|---|---|
| Primary button | `rounded-full bg-whiteout text-graphite-deep px-7 py-3 text-body-sm font-medium hover:bg-cloud`. One per view, for the main action. |
| Secondary button | `rounded-full border border-graphite-light text-whiteout px-[18px] py-3 text-body-sm font-medium hover:border-ash`. |
| Destructive button | Secondary button with `text-system-warning`. Always confirmed in a dialog first. |
| Text link | `text-whiteout underline underline-offset-4 decoration-graphite-light hover:decoration-whiteout`. |
| Nav link | `text-ash hover:text-whiteout`; the current page is `text-whiteout`. |
| Card | `rounded-sm bg-graphite-deep border border-graphite-light p-6`. |
| Input | `rounded-sm bg-graphite border border-graphite-light text-whiteout placeholder:text-pewter focus:border-neon-glow`. Always has a visible `<label>`. |
| Status badge | `text-caption` text in `cloud` with a 6px dot: green for Online/Active, `ash` for Completed/Offline, red for Failed/Error. Only where the status can actually differ between rows. |
| Table | Container is a card. Headers are `text-caption text-ash`, sentence case. Numbers are right-aligned, `font-mono tabular-nums`. Rows get `hover:bg-graphite`. |
| Code / terminal block | `rounded-sm border border-graphite-light bg-graphite-deep p-6 font-mono text-body-sm text-whiteout`. Prompts in `neon-glow`. No fake window bar or traffic-light dots. SSH commands always have a copy button. |
| Feature list | A two-column `<dl>`: title in `whiteout`, description in `ash`, items separated by a top border. No icons, no dots, no cards. |

Use the existing shadcn components in `frontend/components/ui/` (Dialog, Select, Accordion, Table, Toast, ...) rather than building new ones.

## Patterns we don't use

These are the tells of template or AI-generated UI. Don't add them, even when a component library offers them.

- Small uppercase or mono labels above headings ("FEATURES", "HOW IT WORKS"), with or without a dot.
- Decorative dots, pulsing dots, or "New" / "Beta" pills that aren't tied to something real.
- Grids of identical cards with an icon on top, a bold title and two lines of text.
- Big colored step numbers ("01", "02", "03").
- Fake macOS window chrome on code blocks.
- Glows, spotlights, beams, aurora/blob backgrounds, sparkles, meteors, gradient or shimmering text, moving borders.
- Marquees of logos or testimonials, avatar stacks, star ratings.
- Animations on scroll for every section. Motion is allowed only where it explains something (for example, a terminal typing out a real command) and stays under 300ms for UI transitions.
- Icons next to every heading or list item. Use an icon only when it helps someone scan or recognise an action.

## Imagery

- No photos, illustrations, stock art, emoji, or 3D renders.
- Product visuals are terminal windows and code blocks built as real HTML, not screenshots.
- The only decoration is abstract thin vertical lines in `neon-glow` / `neon-muted`, like a data stream, used sparingly behind the landing hero.
- Icons are `lucide-react`, 16–20px, stroke style, in `whiteout` or `ash`. Mostly for actions (copy, download, close, menu).

## States every screen must handle

- **Loading:** skeleton blocks in `bg-graphite` the same shape as the content. No full-page spinners.
- **Empty:** says what is missing and what to do next. "You have no sessions yet. Rent a GPU from the marketplace to start one." plus a button.
- **Error:** says what failed and what the user can do. "Couldn't load your sessions. Check your connection and refresh the page." Never show raw exception text or status codes.
- **Disabled buttons** explain why nearby: "Add funds to rent this GPU (balance Rs 40, needed Rs 150 for 1 hour)."

## Accessibility

- Every input has a `<label>`. Icon-only buttons have `aria-label`.
- Visible focus ring on every interactive element (`focus-visible:ring-2 ring-neon-glow`).
- Don't rely on color alone: status badges always include the word ("Online"), not just a dot.
- Pages work at 375px wide with no horizontal scroll. Long strings (SSH commands, IDs) scroll inside their own block.

---

# Writing for the UI

Every label, heading, description, toast and error is written for a developer or a GPU owner in Nepal who wants a straight answer. Write the way a good engineer explains something to a colleague.

## Rules

1. **Say what it does, concretely.** "Rent a GPU by the hour and connect over SSH." not "Unlock the power of next-generation compute."
2. **Only claim what the code does today.** No features that don't exist, no "enterprise-grade", "bank-level security", "99.9% uptime", "verified hosts", or "instant" unless it is built and measured. If you're unsure, leave the claim out.
3. **No invented numbers or social proof.** No fake user counts, testimonials, customer logos, ratings, or "trusted by" rows. Stats on the page come from the API or don't appear.
4. **Sentence case** everywhere: "Add funds", not "Add Funds". Product name is "Labhya Compute" (or "Labhya" after first mention).
5. **Buttons are verb + object**, 1–3 words: "Rent GPU", "Add funds", "End session", "Copy command", "Download agent". Never "Submit", "Click here", "Let's go", "Get started now!".
6. **Plain words.** Short sentences. Second person ("you"). No exclamation marks. No emoji.
7. **Numbers are specific**: "Rs 150/hr", "24 GB VRAM", "Started 12 min ago". Not "affordable", "huge memory", "recently".
8. **Errors say what happened and what to do next**, without blame: "Your balance is too low to rent this GPU. Add at least Rs 110 to continue."
9. **Toasts confirm the result**, not the attempt: "Session ended. Rs 42 charged." not "Success!".

## Banned words

Don't use these anywhere in the UI, metadata, or README marketing copy:

> seamless, seamlessly, effortless, unlock, unleash, empower, supercharge, revolutionize, revolutionary, cutting-edge, next-gen, next-generation, state-of-the-art, world-class, best-in-class, enterprise-grade, production-ready, robust, powerful, blazing, lightning-fast, game-changing, leverage, harness, elevate, delve, journey, ecosystem, synergy, solution(s) (as a noun for the product), AI-powered, magic/magical, simply, just (as in "just click"), easily, "take it to the next level", "in today's world"

## Vocabulary

Use the same word for the same thing everywhere.

| Use | Not |
|---|---|
| GPU | instance, node, machine (except "your machine" for a host's PC) |
| Session | rental, job, deployment, pod |
| Rent | deploy, launch, spin up |
| Host | provider, supplier, miner |
| Renter | customer, client, user (in UI copy) |
| Wallet | account balance, credits |
| Agent / desktop agent | client, daemon, app |
| Tunnel (only where the user must know about it) | relay, proxy, gateway |

---

# Before you finish a frontend change

- [ ] Only design-token colors; no stock Tailwind palettes, no raw hex, no gradients, no shadows.
- [ ] Pill buttons, 4px everything else.
- [ ] Nothing from "Patterns we don't use".
- [ ] Inter for text, Geist Mono for code/data/labels, not mixed in one line.
- [ ] Copy passes the writing rules and contains no banned words.
- [ ] Loading, empty and error states exist and read like the examples above.
- [ ] Checked at 375px and 1440px in the browser.
