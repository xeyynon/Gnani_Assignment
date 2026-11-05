# Frontend skills: how Surya builds and checks an interface

A reference to carry into other projects: the working style, the structure, the design system, the UX patterns, the way an interface is checked, the traps that were hit, and an audit checklist.

**Written for:** Surya's own future projects, and any AI coding agent working for Surya. Use it as a brief (sections 2, 3 and 12), as an audit (section 13), or as a skill (all of it).

**Where it comes from, and its limits.** Everything here was done and checked in this repository (Dukaan Dost, two shop pages and an admin page, built and rebuilt over 2026-11-02 and 2026-11-03). Each rule says why it exists. Where something was *not* verified, that is stated (section 15). Project-specific values (colours, file names) are examples of a method, not requirements. The longer record of decisions is in [frontend.md](frontend.md) and [decisions.md](decisions.md).

---

## 1. How to use this file

| You want to | Read |
|---|---|
| Start a new project the way Surya works | 2, 3, 4, 12 |
| Brief an agent in a few lines | 2 and 14 |
| Review an interface that exists | 13 (the checklist), then 11 (what usually goes wrong) |
| Reuse the look | 5 |
| Reuse a screen or a behaviour | 7 |
| Check a change properly | 10 |

---

## 2. Working style (what Surya does, and how to work with it)

Observed across these sessions. Each line is something to do.

1. **Everything is a component, in an atomic structure.** Atoms, molecules, organisms, pages. When a page was one 500-line file, the request was to rebuild it component by component. Do this from the start, not as a later cleanup (section 4).
2. **Reference first.** Surya shows a mockup or a screenshot of a site they like and says what to take from it ("take inspiration from the dark theme of this site and some functions"). Follow the structure, then say plainly what was taken, what was adapted and what was left out and why. A two-column table (in the mockup / what was built) worked well.
3. **Light, plain, not shiny.** The first palette was a pasted spec; the reaction to a bright white was "not shiny bright". Muted surfaces, colour only where it carries meaning. A dark look was asked for later, taken from a reference.
4. **Named design concepts are mixed on purpose, so give each one a job.** "Bento, glassmorphism, brutalism, minimalism" worked once each had one role (section 5.4). Mixed with no roles they fight.
5. **Feedback is short and about a specific thing** ("this icon looking odd", "this is too big", "I see the same dashboard", "what about the white colour"). Find out which thing, check the cause before defending the work, fix it, show the result. When the answer is "I see no change", first check what is actually being served and how the viewer is set up (section 11, "no change").
6. **Wants to see it, live.** Run the preview, take real screenshots, say exactly what is running and what is not ("is that live" is answered with the address, the credentials, and what is *not* running).
7. **Version control is deliberate.** A branch for each piece of work. Commit and push only when asked. Commit by concern (a user-visible change is a numbered build; docs, tests and refactors are internal), the docs travel in the same commit, and files another session changed are left alone. Messages that arrive mid-task can reorder the work ("push, then make a branch, then work"): read them together.
8. **The docs are updated with every change**, and a decision is recorded with its reason, so the next session does not undo something deliberate.
9. **Honesty is a rule, not a tone.** No figure without a saved measurement. Say what was not tried (a real phone, a real call) in the same message that says what was done.
10. **Knowledge is meant to be reused.** Surya asks for it to be written down as a skill or an audit. Keep working notes in a form another project can lift.

---

## 3. Principles (the short list)

1. **Show only what the data supports.** A missing value is a dash or a stated reason, never a placeholder that looks like a reading.
2. **Three kinds of empty:** still loading, nothing here, not available. They look and read differently.
3. **Loading is not "nothing here".** Show placeholders until the first answer.
4. **One home per fact.** If a tile and a panel show the same thing, one of them goes (a "Needs you" tile that repeated the "Needs your attention" panel was removed; its count became a badge in the panel).
5. **Compare like with like.** "vs yesterday" at 10 am means yesterday *up to 10 am*.
6. **Status is a coloured pill with a word.** Never colour alone.
7. **Every colour is a token**, and a test fails if one is written anywhere else.
8. **A component is one kind of thing** (markup, styles *or* script) with one home.
9. **Text from outside is shown as text, never as HTML.**
10. **Fail closed.** No admin password set means the admin page is off, not open.
11. **Writes are all-or-nothing and never destructive.** Build in a hidden place and rename into place; validate the whole before writing; keep a copy of what is overwritten; do not offer delete.
12. **A secret is shown once** and never logged.
13. **Focus never falls to the page body.** When the control that had it goes away, give it to what replaces it.
14. **A shortcut ignores typing, held keys and modifier chords**, and its key is in the tooltip.
15. **Nothing loads from outside** unless there is a strong reason; one self-contained response is easier to secure and to test.
16. **A test that has never failed has not been shown to test anything.** Break the thing on purpose once.
17. **Build it, then look at it in a real browser at real widths, then drive the real flows.** Unit tests alone passed while the real page did not work (section 11).
18. **Remove what is not needed.** A "coming soon" button that nobody needs is clutter; show it only while it is a promise, then build it or delete it.
19. **Do not invent.** No made-up numbers, dates or "failed turns" lists; if the data does not exist yet, say the feature waits for it.

---

## 4. Structure: components

### 4.1 The shape
Every interface piece is a small file with one job. A page is a short template that lists the pieces it is made of.

```
web/
  index.html  dashboard.html  admin.html      pages: the list of components + that page's own controller
  components/
    shared/        used by more than one page
    <page>/        used by one page
```

| Level | What it is | Examples here |
|---|---|---|
| **Tokens** | Colours, radii, shadow. The only place a colour is written. | `shared/tokens.css` |
| **Atoms** | One visual idea with no layout of its own | chip, dot, tag, mark, pill, icon, button, field |
| **Molecules** | A few atoms working together | panel with its heading row, brand block, theme button, icon tile, stat tile |
| **Organisms** | A whole panel: markup, styles and script side by side | recent orders, stock editor, live transcript, call card |
| **Pages** | The organisms in order, plus the controller that feeds them | the call page, the shop dashboard, the admin |

An organism is up to three files with one name: `x.html` (markup), `x.css` (styles), `x.js` (the function that draws it). **Pure helpers** (formatting, labels, the rule for what needs attention, filters, validation) live in `helpers.js` files so Node can test them with no browser.

### 4.2 How the pieces are put together
A tiny composer (`dukaan_dost/webpage.py`) replaces `{{include:path}}` with the file's text when the page is served. The result is **one self-contained response**, so a strict Content-Security-Policy (no outside files) holds and tests need no server.

Safety rules of the composer, each tested: an include can only name a file inside the components folder (`..` and absolute paths refused); nesting is limited, which also stops a component including itself; a missing component is an error, never a silent gap.

Why not a framework: nothing to install or upgrade, one response, and the pages are small. **Use a framework when** a page needs many interactive states that share data, or a team needs it. The component *structure* carries over either way.

### 4.3 Rules
1. **One home per piece.** Used by two pages means it goes in `shared/`. (The theme button, brand block, tokens, icon sheet, DOM builder, formatters, key check, shell, side menu, tiles, pills, lists, forms and the polling loop were each written twice before they were shared.)
2. **A component never holds its own `<script>` or `<style>` tag.** The page owns those. A test fails otherwise.
3. **No orphans, no holes.** A test fails if a component is used by no page, or a page asks for one that does not exist.
4. **A class means one thing everywhere.** Where two meanings were needed the names differ (`.order-total` and `.total`).
5. **Change a token in one file.** Pages have no copies to keep in step.
6. **Look before and after a split.** The refactor was checked rule by rule (compare the CSS of the old and new composed page), by screenshots of the same states, and by putting a stray colour into each kind of component to see the colour test fail.

### 4.4 Adding a component
Write `components/<shared or page>/<name>.{html,css,js}`, add its include line to the page, run the composer tests and the page tests, and open the page.

---

## 5. Design system

### 5.1 Tokens (names matter more than values)
Surfaces: `--bg`, `--surface`, `--surface2`. Text: `--ink`, `--muted`. Line: `--line`. Roles: `--green` (brand, active), `--blue` (sales, processing), `--credit` (credit), `--amber` (pending), `--warn` (error), `--end` (hang up); each with a `-soft` tint and, for text on a tint, `--green-ink`. Text on a filled colour is its own token (`--on-green`, `--on-end`) so a button's text colour is never a literal. Shape: `--radius-card`, `--radius-button`, `--shadow-card`. Effects: `--glass`, `--glass-line`, `--blur`, `--blob-1..3`. Accent edge: `--brut`, `--hard-shadow`. Numbers: `--mono`.

**Values used here** (examples; the palette was made neutral on 2026-11-05, DEC-049): light bg `#F3F3F1`, card `#FFFFFF`, ink `#1C1C1E`, green `#1F7A4D`. Dark bg `#141415`, card `#1D1D1F`, ink `#ECECEE`, green `#5DBB8A`. All pages share it; no separate admin palette. Card radius 22 px; button radius 12 px.

Every pair of text and background was chosen for contrast, but **contrast was checked by eye, not with a tool** (section 15).

### 5.2 Type, icons, spacing
Inter first, then the system font (nothing is fetched from outside, so Inter shows only if installed). Numbers in a monospace stack (IBM Plex Mono if installed, then the system's) with tabular figures so columns align. Small uppercase labels with letter spacing for field and tile names. Icons are an inline SVG sprite, line style (stroke 1.8, round caps), drawn with `<use href="#i-name">`; there is no icon font and no download. Gaps are 14 px between cells, 8 to 12 px inside.

### 5.3 Theme mechanics
- Tokens are CSS custom properties on `:root`; dark redefines the **same names**. Dark applies in two cases: by the device (`prefers-color-scheme: dark` unless light is chosen) and when dark is chosen (`:root[data-theme="dark"]`).
- Three choices: **Auto** (follow the device), **Light**, **Dark**. A button cycles them; **T** does the same.
- The choice is saved (`localStorage`, key shared by every page) *including Auto*, so Auto is a choice and different from never having chosen. A page can have its own default (the admin starts dark).
- A small inline script in `<head>`, **before the CSS**, reads the saved choice and sets `data-theme`, so there is no flash of the wrong theme.
- `color-scheme` is set with the theme so native controls match.
- Every storage access is in try/catch (private windows, blocked storage).

### 5.4 The mix: bento, glass, brutalist accents, minimal
| Idea | Its job | Rule |
|---|---|---|
| **Bento** | The layout: unequal cells on a 12-column grid, one hero | One hero per page. Wrappers dissolve (`display:contents`) so every cell sits directly on the grid and is placed by a class (`b-recent`, `b-attn`...). Phone: two columns, then one, hero first. |
| **Glass** | The chrome only: menu, top bar, chips, buttons, the call card | **Glass never carries a number.** Cards with figures stay solid. Opaque fallback where `backdrop-filter` is missing and under `prefers-reduced-transparency`. |
| **Brutalist accents** | The one action and the one figure that matter | Thick border and a hard offset shadow that presses in on click. At most one call to action and one hero figure per screen. Respect reduced motion. |
| **Minimal** | The base | One radius, generous gaps, no shadows on ordinary cells. |

**Update 2026-11-05:** the glass and the colour blobs were removed (DEC-049): the user found the navy-and-glow dark theme too much, and flat solid surfaces measure exactly (no translucent colour to approximate). Lesson: a decorative layer that cannot be measured is the first thing to drop when someone asks for plainer. Also: a brutalist hard shadow must not be the same colour as the thing it sits under, or it looks like a rendering fault.

### 5.5 Colour roles (use the same colour for the same meaning, everywhere)
Green: brand, active, ready, confirmed. Blue: money in, sales, "thinking". Violet: credit. Amber: pending, warning. Red: error, hang up, broken. Grey: neutral and idle. Status is always a pill with the **word** (Ready, Needs attention, Broken, Confirmed, Credit pending, Incomplete, Error, Warning).

---

## 6. Layout and responsive

- **Shell:** a grid with a menu column and a content column; the menu is a **drawer** (curved right end, slides out, hides with a button or **B**, remembered, applied before paint, leaves the tab order while hidden, focus handed to the button that replaces the one pressed).
- **Floating bars:** sticky top bar as glass with rounded corners and a gap from the window edge.
- **Breakpoints used:** 1001+ (12-column bento), 900 (menu becomes a row, call page stacks), 640 (table rows become cards), 600 (tighter padding), 520 (one column).
- **Phone:** the menu becomes a wrapped row at the top; tables become stacked cards; tables that cannot shrink get a scroll wrapper; fields are full width.
- **Touch:** 44 px minimum targets on a coarse pointer (`@media (pointer: coarse)`).
- **Overflow:** flex and grid children get `min-width:0`; long text gets `overflow-wrap:anywhere`. The sideways-overflow check runs at 1440, 1280, 1100, 1001, 900, 600, 390 and 360 px, menu open and hidden (section 10).
- **Zoom:** never block pinch zoom.

---

## 7. UX pattern catalogue

Each: what it is, how it was built, the catch.

| Pattern | How | Catch |
|---|---|---|
| **Stat tile** | Icon tile + small uppercase label + monospace value + one line of context | One hero per row; the hero is wider, not taller (a two-row hero was mostly empty space). An icon tile whose tint equals the card's tint disappears and leaves a floating glyph: give it a contrasting square. |
| **Needs-attention list with a count badge** | Items from the data, urgent first; the count is a badge in the heading | Do not repeat it as a tile (one home per fact). |
| **Status pill** | `pill` + state class + the word | Unknown state is shown as "needs attention", never as ready. |
| **Live data** | Poll every 3 to 5 s; "Live, updated 2 s ago"; after 10 s "Connection lost, showing data from N s ago"; sign-out and rate-limit messages are plain | Keep the last data on a network error; do not blank the page. |
| **Loading** | Placeholder blocks, `aria-busy` on the container | Empty-state text is only for data that really is empty. |
| **Fair comparison** | Today so far against yesterday to the same time of day; label says "vs this time yesterday"; no percentage from a zero | Older servers fall back to the whole of yesterday and the label says so. |
| **Filter tabs with counts** | Buttons with `aria-pressed`; each shows how many it would give; the empty message says which filter or search found nothing | Not `role="tab"`: that role promises panels. Counts and results come from the same function (tested). |
| **Search with Ctrl/Cmd K** | Search field in the top bar, shortcut hint by platform, Escape clears; typing from another view goes to the list | The shortcut is a modifier chord, so the plain-key guard does not apply to it; handle it separately. Search text is matched as text, never as a pattern. |
| **Dismissible notice** | Shows what is wrong; dismissing is remembered *against the numbers*, so it returns when they change | Focus moves to the next panel, not the page body. |
| **Mark solved (only warnings)** | Moves to a "Marked solved" list with Undo; stops counting | **An error cannot be marked solved.** Hiding a real failure is a lie the page tells. |
| **Add a thing** | Name, a link name suggested from it and checked as you type, a template choice, an optional secret | A made-up secret is generated when none is given and **shown once**, with the reason ("stored scrambled, cannot be read back"). |
| **Edit a thing** | One panel per concern (name and instructions, PIN, stock), each with its own button and message | Say what saving does ("applies to the next call", "a copy of the old file is kept"). |
| **Table editor** | Price field, in-stock checkbox, remove checkbox per row; save sends only what changed | A bad row stops the save on the page with the row named; the server checks again. |
| **Form** | Visible `<label for>` on every field, a hint line, inline validation, the button disabled while it runs, the outcome in words under the button | Errors in `role` status/alert text, never colour alone. |
| **Panel with a drill-down** | A title, a one-line caption and a "View all" link to the full list; the panel shows only the first few ("View all 9" when there are more) | Taken from a reference dashboard's card-per-metric layout. The link is hidden when there is nothing to view. |
| **Copy a link** | A button that copies the full address (origin + path) and says what was copied; if the clipboard is blocked it shows the link instead | The clipboard needs https or localhost and a user gesture; never fail silently. |
| **Activity log** | What was done, to which shop, when; newest first | Never a secret or typed text. Reading is not an event; a refused command is not an event. |
| **Read-only panel fed by the server** | The page shows what an event carried and does no arithmetic; a test checks the panel code has none; an event with no usable figures changes nothing; the last value stays until the next session starts | Money, totals and loan figures are computed on the server (the model only speaks them), so a page that recomputed could disagree with what the caller heard. |
| **Call screen** | States: idle, connecting, listening, thinking, speaking, muted, ended; a waveform that follows the mic then the agent's voice; a timer; a live transcript; a read-only order panel | "Thinking" gives up after 12 s because not every turn gets a spoken reply. The order is changed by voice, never by buttons, and totals are computed on the server. |
| **Theme switch, drawer menu** | Section 5.3 and 6 | Persist, apply before paint, remember "Auto". |
| **"Soon" placeholders** | Shown, disabled and labelled while they are a promise | **Remove them when built or when not needed.** Do not leave dead buttons. |

---

## 8. Accessibility (done and checked in these pages)

- Every field has a visible label tied by `for`; every button has a name (text or `aria-label`); a test checks both.
- Filters use `aria-pressed`; `role="tab"` is used only when there are tab panels.
- Toggles and drawers expose state: `aria-expanded`, `aria-controls`, `aria-pressed`, `aria-current="page"`.
- Loading containers set `aria-busy`; messages use `role="status"` (polite) and `role="alert"` for errors; live regions are small.
- **Focus management:** a control that disappears hands focus to its replacement; a changed section focuses its heading (`tabindex="-1"`); a dismissed notice focuses the next panel.
- Keyboard shortcuts ignore typing, held keys and Ctrl/Alt/Cmd chords; the key appears in the control's tooltip; a hidden menu leaves the tab order.
- Reduced motion switches off pulses, sways and slides; reduced transparency makes glass opaque.
- Colour is never the only signal (pills carry words).
- 44 px touch targets on touch screens; zoom is allowed.
- **Not covered:** an automated accessibility test, a screen-reader pass, a contrast tool (section 15).

---

## 9. Security of an interface that shows other people's text

- **Text nodes only.** Everything from data goes through a builder that uses `textContent`; `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval` and `new Function` are banned in page scripts, and a test fails if one appears. A shop named `<img src=x onerror=...>` is shown as that text (checked in a real browser).
- **Strict Content-Security-Policy:** `default-src 'none'`, inline script and style only, `connect-src 'self'`, `frame-ancestors 'none'`; plus `X-Frame-Options: DENY`, `nosniff`, `no-store`, no referrer.
- **Nothing from outside:** no CDN scripts, fonts or icons; a test fails on any `http(s)://` in the page.
- **Roles are separate:** a shop's PIN never opens the admin page, whatever user name it is sent with.
- **Fail closed:** no admin password configured means HTTP 503 with how to set one; the example placeholder counts as "not set".
- **Throttle guesses:** five wrong in a row lock that address for a minute; a good sign-in resets the count.
- **Commands over a socket** (when a page must write and the server cannot read request bodies): a short-lived random token fetched with a signed-in request and sent first; the socket also refuses a connection whose Origin is not this server (this is what stops a page on another site from using a signed-in browser); commands are rate limited. Tested with a real cross-origin attempt.
- **Secrets:** stored hashed, shown once, never logged, never in a URL.
- **Writes:** validate names before they become paths; build a new thing in a hidden folder and rename it into place; validate a whole list before writing it; keep a copy of a file before rewriting; no admin action deletes anything from disk.
- **Validate twice:** on the page to help the typist, on the server because the page is not trusted.

---

## 10. Verifying an interface (the loop)

**Build, look, drive, break, document.**

1. **Unit-test the pure logic** (helpers) in Node, with no browser: formatters, labels, validation, filters, diffs of edits, banner and tab rules. Pull the helpers out of the composed page between two markers and run them with `new Function`, so the test runs the page's own code.
2. **Rule tests on the page source:** no banned DOM calls, no outside loads, no literal colours outside token rules, every field labelled, every button named, the theme script runs before the CSS, every command the page sends is one the server knows.
3. **Server tests with a real server** on a free port and real clients: sign-in cases (none, wrong, another role, no password set, throttled), the socket (right token, wrong token, no token, another origin), each command end to end, and what must *not* happen.
4. **Look in a real browser** at real device widths, in light and dark: `scripts/ui_check/shot.mjs` (headless Chrome over the DevTools protocol; no packages needed beyond Node 20+ and Chrome). It prints sideways overflow at every width.
5. **Drive the real page through real flows:** `scripts/ui_check/drive.mjs` runs steps of `{ name, js, expect, shot }`: type into fields, click, wait for the result, and compare what the page shows. In this project 20 flows (create, refuse a duplicate, generated secret, edit, refuse an empty value, stock add/change/remove, mark solved and undo, a hostile name) found a bug that every unit test had missed (section 11). Run each flow on a **fresh server**, and wait until the server answers before starting.
6. **Mutation-check the tests:** put the bug back (a stray colour in each kind of component, a removed guard) and see the test fail. A rule test that passes with the bug present is broken.
7. **Compare before and after a refactor:** compose the old and new page and diff the CSS rule by rule and the lines of script.
8. **Write down what was not tried.**

Checking order for a change: tests, then screenshots at 1280, 390 and 360 in both themes, then the flows, then the docs.

---

## 11. Traps hit, and the fix (symptom, cause, fix)

| Symptom | Cause | Fix |
|---|---|---|
| A rule test passed even with the rule broken | The shell turned `\b` in the regex into a backspace byte; the pattern could never match | Write files with a file tool, not shell heredocs; mutation-check every rule test; scan changed files for stray control bytes |
| Backticked words vanished from a comment | An unquoted shell heredoc ran them as commands | Quote heredocs, or write the file with a file tool |
| "I see no change" after a theme edit | The viewer's device was in dark mode and only the light theme changed | Give the page an explicit Auto/Light/Dark switch; say which theme a change affects |
| Every command failed with "could not connect" | The preview server never registered the command socket (only the real app did); all unit tests passed | Drive the real page against the preview, not only unit tests; keep every entry point's wiring in step |
| A flow failed 13 steps at once | It was re-run against a server that already held what the first run created | Fresh server per flow run |
| Every step failed, all elements null | The server was not up when the browser started | Wait until the server answers (poll it) |
| A new shop with a broken `config.yaml` vanished from the admin | The list the agent uses hides a shop with no config | List shop-like folders for the admin; the agent keeps the strict list |
| Marking a problem solved for a shop that does not exist succeeded | The target was not checked, only the problem id's shape | Validate the thing the id points at |
| A save failed on valid input in the demo | The demo data held an invalid item, so the whole list was refused | Demo data must pass the same validation as real data |
| The page's tests broke after adding a head script | The test took the first `<script>` in the page | Select the main script (the longest), not the first |
| A page changed after saving a prompt but calls did not | The running agent cached the shop | Tell the agent to drop its cached copy when something is saved; a call in progress keeps what it has |
| A hero tile two rows tall was mostly empty | Layout by habit | Make the hero wider, not taller |
| An icon looked like it was floating | Its tint matched the tile's tint | A contrasting square behind it |
| A tile duplicated a panel beside it | Two homes for one fact | Keep one; the count became a badge |
| Sideways scroll on a laptop width | A narrow tile with no room for its content | Check overflow at every width after every layout change |
| A search helper returned `undefined` instead of `false` | `a && b && c` short-circuit | `Boolean(...)`; test with strict equality |
| Commits mixed two sessions' work | Both sessions edited the same tree | Stage by file; read each shared file's hunks before staging; leave the others' files alone |

---

## 12. Build order for a new project

1. **Tokens and two themes first** (same names, light and dark, head script before the CSS, an Auto/Light/Dark switch). Add a test that fails on a literal colour.
2. **The composer and the structure** (shared, atoms, panels, pages) before the first page.
3. **The shell:** menu drawer, top bar, view switcher, theme button, polling loop.
4. **One honest page end to end** (loading, empty, live, error, signed out), then its tests.
5. **The security basics:** the text-only builder with its banned-calls test, the CSP, sign-in, fail closed.
6. **Writes**, once reads are solid: all-or-nothing functions with their own tests, then the socket.
7. **Drive the real flows** before calling anything done.
8. **Docs** with each step: what it does, why, what was not tried.

---

## 13. Audit checklist (copy this)

**Structure**
- [ ] Every piece is a component with one home; none is written twice
- [ ] A page file lists components and holds only its own controller
- [ ] No component carries its own `<script>` or `<style>`; none is unused; none is missing
- [ ] Pure helpers are separate and tested

**Design system**
- [ ] Every colour is a token; a test fails on a literal colour
- [ ] Light and dark use the same token names; the theme is applied before first paint
- [ ] Auto, Light and Dark are all reachable and Auto is remembered
- [ ] Status is a pill with a word; the same colour means the same thing everywhere
- [ ] Glass is only on chrome and never under a number; brutalism is limited to one action and one figure per screen
- [ ] Numbers are monospace with tabular figures

**States and honesty**
- [ ] Loading, empty, nothing-here and not-available all look different
- [ ] No invented value; a missing value is a dash or a reason
- [ ] Comparisons are like with like and say which
- [ ] No duplicated fact; no dead "soon" button that nobody needs

**Layout**
- [ ] No sideways scroll at 1440, 1280, 1100, 1001, 900, 600, 390, 360 (menu open and hidden)
- [ ] 44 px targets on touch; zoom allowed; tables scroll or become cards
- [ ] Phone layout reads in the same order as desktop, hero first

**Accessibility**
- [ ] Every field labelled; every button named
- [ ] State exposed (`aria-pressed`, `aria-expanded`, `aria-current`, `aria-busy`)
- [ ] Focus never falls to the body; shortcuts ignore typing, held keys and chords
- [ ] Reduced motion and reduced transparency honoured; colour is never the only signal

**Security**
- [ ] Outside text is shown as text; banned DOM calls are tested
- [ ] Strict CSP; nothing loaded from outside
- [ ] Roles are separate; fail closed; guesses throttled
- [ ] A socket needs a token and a matching Origin; commands are rate limited
- [ ] Secrets are hashed, shown once, never logged
- [ ] Writes are all-or-nothing, keep a backup, and nothing is deleted

**Verification**
- [ ] Helpers, rules and the server each have tests, including what must not happen
- [ ] Real screenshots in both themes at phone and desktop widths were looked at
- [ ] Real flows were driven through the real page on a fresh server
- [ ] Each rule test was shown to fail once
- [ ] What was not tried is written down

---

## 14. Phrases that work with this style

To an agent, in a few lines:

> Build it component by component (atoms, molecules, organisms, pages): one home per piece, shared things in `shared/`, a page is a list of components. Every colour a token with a test. Loading, empty and error are different states. Status is a pill with a word. Outside text only as text. Fail closed. Check it in a real browser at 1280, 390 and 360 in light and dark, drive the real flows, and say what you did not try. Commit by concern only when I ask; update the docs in the same commit.

When giving a reference site: public pages can be read for layout and content patterns (a text fetch returns structure, not colours or CSS, so exact styling comes from a screenshot you provide). Take patterns, never their branding, logo or code. Say *what to take* ("the dark theme and the search, tabs and activity view") and expect a table of what was taken and left out.

When something looks wrong: name the thing ("this card", "the icon") and say what is wrong ("too big", "looks odd"); expect the cause to be found and the result shown.

---

## 15. Limits: what was not verified, and what is project-specific

**Not verified here:** a real phone (only a headless browser at phone widths); a real microphone and call through the call page; contrast measured with a tool (chosen and checked by eye); a screen-reader pass; an automated accessibility test; Firefox and Safari (Chrome only); behaviour behind https and a reverse proxy.

**Specific to this project, not general:** the palette values, the shop and admin pages, the voice-call screen, the file names. The *method* (components, tokens, states, security, verification) is the part to carry over.

**Data in the examples is made up.** No real shop, customer or recording appears in this repository's pages or tests.

---

## Appendix: where things are in this project

| Thing | Where |
|---|---|
| The composer | `dukaan_dost/webpage.py`, tests in `tests/test_webpage.py` |
| Components | `dukaan_dost/web/components/{shared,call,dashboard,admin}/` |
| Pages | `dukaan_dost/web/{index,dashboard,admin}.html` |
| Admin server | `admin.py` (sign-in, data, socket), `admin_actions.py` (every change), `shop_health.py` (the checks) |
| Page tests (Node) | `tests/web/*.test.mjs`, with `tests/web/composed.mjs` to compose a page |
| Browser tools | `scripts/ui_check/shot.mjs`, `scripts/ui_check/drive.mjs` |
| See it with no keys | `python -m dukaan_dost.preview`, then `/admin` (user `admin`, password `admin1111`) |
| Decisions and the longer record | [decisions.md](decisions.md) (DEC-040 components, DEC-041 the visual mix, DEC-042 the admin), [frontend.md](frontend.md) |

## Patterns taken from a reference dashboard (2026-11-03)
Studied from a public developer-platform site and a screenshot of its dark dashboard. Taken as ideas; nothing is copied.

| Seen there | Built here | Why it earns its place |
|---|---|---|
| A search field with a keyboard shortcut hint | Search shops, Ctrl or Cmd K, Escape clears | Finding one of many things quickly |
| A category strip with a count on each | Filter tabs (All, Ready, Needs attention, Broken) with counts | The counts say what a tab will show before you press it |
| A banner above the content, dismissible | A notice when something is wrong, dismissed until the numbers change | Important, but not nagging |
| A labelled section in the menu ("Workspace") | The same label | Orientation |
| A "data as of" stamp | "Live, updated 2 s ago", and "Connection lost" after 10 s | Never leave the viewer guessing how fresh it is |
| Cards with a title, a caption and an "Explore" link | Overview panels with "View all" | A glance on the first screen, the full list one click away |
| An activity view | A real audit log of what was changed | The operator can see who changed what |
| A copyable command shown inline | "Copy call link" | Sharing a shop's link is a daily admin job |
| Skeleton placeholders in empty cards | The same, with `aria-busy` | Loading does not look like "nothing here" |

**Seen but not taken, and why:** model comparison and pinning (no equivalent here), charts with a price-versus-score scatter (no such data), a pagination or "Show more" on shops (a handful of shops; add it when there are dozens), data-licence footers (nothing published).
