# How the Dukaan Dost frontend was designed and built

A reusable design-and-build guide, written from a real project: the web pages of a voice agent for a neighbourhood kirana shop (Gnani.ai's Great Indian AI Internship Challenge). Four pages: a **call page** a caller talks to from a browser tab, a **shopkeeper dashboard**, an **admin page** that looks after every shop, and a **sign-in page** for the two dashboards. They are plain HTML, CSS and JavaScript, built from small components that a Python server stitches into one page per request: no framework, no build step, nothing loaded from outside. Every rule below is tied to something that happened here: a decision (`DEC-nnn` in [decisions.md](decisions.md)), a bug (`B-nn` in [bugs.md](bugs.md)), a release (`build-N`, report in [builds/](builds/)), an internal change (`InBulNN`), or a picture in [snapshots/CHANGES.md](../snapshots/CHANGES.md).

**Who this is for.** A person or an AI session starting a *different* frontend who wants the same quality bar without repeating the same mistakes. **Part A** is for any stack (principles, process, honesty, interaction design, security). **Part B** is specific to this stack (plain web pages served by a Python app, tested with Node and headless Chrome). **Part C** is the build order, the checklist, the file map and the words.

**How the quality happened.** Not from a good first draft. From a loop: build it, **look at it in a real browser** at real widths, get Surya's reaction, name the *class* of mistake, write the rule down, add a check that fails if the rule is broken, then search every page for the same mistake. Eleven builds between build-1002 and build-1015 changed how the pages look, from 2026-10-28 to 2026-11-06; the pictures of each are in [snapshots/CHANGES.md](../snapshots/CHANGES.md). The loop is the lesson; the components are the evidence.

**Its sister guide.** `frontendcalley.md` (Surya's Flutter project; not in this repository) was read first and several of its rules were adopted here (A3, B7); where this project did something differently, it says so. The older catalogue of patterns written during this project, [frontendgnaniskills.md](frontendgnaniskills.md), is kept for its pattern table (section 7) and is linked rather than repeated.

**Last brought up to date:** 2026-11-08, `build-1015` plus the dashboard's Call page link (written, tested, not yet committed) on branch `ui-ux-upgrade`.

---

## 0. Start a new session with this

Paste this into the first message of the next project, then attach this file and your brief:

> Read `frontendgnani.md` fully. Treat Part A as rules and Part C as the checklist. For this project: (1) build every page component by component from the first day (atoms, molecules, organisms, pages; one home per piece); (2) set up colour tokens for light and dark first, with an Auto / Light / Dark switch applied before the first paint, and **measure** the contrast of every text pair with a tool; (3) give every screen honest states (loading, empty, not available, demo data, signed out, connection lost); (4) show other people's text only as text, load nothing from outside, fail closed; (5) after every change look at the real page in a browser at 360, 390, 768 and 1280 px in light and dark, run the browser audit, and keep the screenshots in `snapshots/latest/` with a picture per release in `snapshots/history/`; (6) keep `bugs.md`, `bugfixed.md`, `decisions.md`, `tried_and_failed.md`, and a report per build; (7) say what you did not try in the same message as what you did; (8) commit and push only when I ask, on one UI branch. Ask me for the brief, a reference design and what the data looks like first.

---

# Part A: Principles and process (any stack)

## A1. The 24 principles, in one page

1. **Everything is a component from day one.** The two first pages were 500-line files with the same pieces written twice; the rebuild split them into one home per piece (DEC-040, build-1007). Do it first, not as a cleanup.
2. **Every colour is a token, and a test fails on a literal colour.** Light and dark use the same token names; components never branch on the theme (`shared/tokens.css`). The first version of that test could never fail (B7, "the backspace byte").
3. **Measure contrast; do not judge it.** A tool reads the real tokens and checks 22 pairs in both themes (`scripts/ui_check/contrast.py`). Its first version measured the dark theme twice and never the light one (B8); once fixed, it found light amber on amber-soft at 4.21:1, which had looked fine to the eye, and the token was darkened (build-1012).
4. **Show only what the data supports.** A missing value is a dash or a stated reason, never a placeholder that looks like a reading. "Failed turns per shop" was not built because the agent does not record them, and a list made from guesses is worse than none (DEC-042).
5. **Loading is not "nothing here".** Placeholders until the first answer, then the empty message only for data that really is empty (build-1007).
6. **One home per fact.** A "Needs you" tile repeated the "Needs your attention" panel beside it; the tile went and its count became a badge (build-1007).
7. **Compare like with like.** "vs yesterday" at 10 am means yesterday *up to 10 am*, and the label says "vs this time yesterday" (build-1007).
8. **Status is a coloured pill with a word**, never colour alone (Ready, Needs attention, Broken, Confirmed, Credit pending).
9. **Numbers are monospaced with tabular figures** so columns do not twitch.
10. **One hero per screen, one primary action.** The hero is wider, not taller: a hero tile two rows tall was mostly empty (build-1007).
11. **The page never does the money.** Order totals and loan figures are computed on the server and the page shows what it was sent; a test checks the loan panel has no arithmetic in it (build-1011, B-15).
12. **Errors are worded by cause.** The sign-in says "That PIN is not right. 3 tries left", "Too many wrong tries. You can try again in 0:41", "Could not reach the server" and "Enter your PIN", each from the server's actual answer (DEC-050).
13. **Fail closed.** No admin password set means the admin page answers 503 and says how to set one; the example placeholder counts as "not set" (DEC-034).
14. **Other people's text is shown as text.** Pages build the page from text nodes only; `innerHTML` and friends are banned by a test; a shop named `<img src=x onerror=...>` shows as those characters (build-1009).
15. **Nothing loads from outside.** No CDN, font or icon download; a strict content security policy; one self-contained response per page, which is also easier to test.
16. **A secret is shown once and never logged.** A generated PIN appears once, with the reason ("stored scrambled, cannot be read back"); no PIN or prompt reaches the activity log (build-1009).
17. **Writes are all-or-nothing and never destroy.** Build a new shop in a hidden folder and rename it into place; check a whole stock list before writing it; keep `config.yaml.bak`; no admin action deletes anything (DEC-042, B-71, B-76).
18. **An error cannot be "marked solved".** A warning can, with Undo; hiding a real failure is a lie the page tells (DEC-042).
19. **Focus never falls to the page body.** When Start call becomes End call, focus moves to the new button; a dismissed notice hands focus to the next panel.
20. **Make the next page one tap away.** The dashboard had no way to the call page until Surya noticed (2026-11-07); every page now links to the ones its user needs next (A5).
21. **Decoration that cannot be measured is the first thing to drop.** Glass and coloured glows read as "too much" and their contrast could not be computed; flat solid surfaces replaced them (DEC-049, build-1012).
22. **Look at the pixels, every change.** Several bugs passed every test and were visible in one glance: a hidden input stretched the page to 1,703 px wide (B7), a hard shadow the same green as its button looked like a rendering fault (DEC-049).
23. **A test that has never failed has not been shown to test anything.** Break the thing on purpose once: three security properties of the sign-in were broken by hand and each made tests fail (build-1015).
24. **Say what was not tried, in the same breath.** Build reports carry a "NOT done" line: a real phone, a real microphone (B-08), https, a screen reader.

## A2. From a reference to a spec

Surya works from references: a pasted palette, a mockup of a call screen, a screenshot of a dark developer dashboard, another project's guide. What worked, in order:

| Step | How | What it gave |
|---|---|---|
| Read the reference for **structure**, not branding | A text fetch of a public page returns layout and content, not colours (those come from a screenshot Surya provides) | The admin's search with Ctrl K, filter tabs with counts, a dismissable notice, "View all" panels, an activity view (build-1010) |
| Write a **taken / built / why** table | Two columns: what the reference has, what was built, why it earns a place; then a "seen but not taken" list with reasons | Kept in [frontendgnaniskills.md](frontendgnaniskills.md), last section; nothing copied |
| Check the reference against **this** product | A speaker button and a language picker in the call mockup were dropped: a browser tab has no speaker, and the speech service detects the language | The call page's "not taken from the mockup" list ([frontend.md](frontend.md)) |
| Read another project's guide as **rules**, then audit against them | Each rule checked against the real pages first; only gaps became work | The contrast tool, the browser audit, the snapshots folder, the sign-in's busy guard and cause-worded errors |

Rules: take patterns, never logos, names or code; say what was left out and why; a reference's palette is a starting point, and Surya's reaction ("not shiny bright", "too much") decides the end.

## A3. Process: the loop

```
reference → tokens + components → one honest page → look in a browser → audit → snapshots
    ↑                                                                              ↓
    └── write the rule + a failing check ← name the class of bug ← Surya's reaction ←┘
```

- **Registers, not memory.** `bugs.md` (what is wrong, by id), `bugfixed.md` (how each was fixed and checked), `decisions.md` (why, `DEC-nnn`), `tried_and_failed.md` / `tried_and_implemented.md`, `pain.md` (risks), `tasks.md`, and one report per build in `builds/`. Check the end of a register for the next free id before using one: two sessions once gave out the same number (DEC-048 was first numbered DEC-040).
- **Two kinds of change.** A **build** is something a caller or shopkeeper would notice (tag `build-N`, a report, a generated changelog entry); an **InBul** is everything else: docs, tests, tools, snapshots (tag `InBulNN`). Tags are the truth; titles never carry the number. The full flow: [version_control.md](version_control.md).
- **One UI branch.** All UI work goes on `ui-ux-upgrade` and is merged into `main` by pull request; the agent and evaluation work have their own branch. Before 2026-11-06 every piece of UI work had its own branch (`admin-dashboard`, `admin-dark-ui`, `call-loan-panel`, `frontend-audit`), which Surya called waste; merged branches are deleted unless Surya keeps one as a marker.
- **Two sessions, one folder is a trap.** While a UI session and a backend session shared one checkout, switching branch would have changed the other's files, and commits mixed their work. Give each its own folder (`git worktree add`), stage by file name, never `git add -A`.
- **Commit and push only when asked.** Commit by concern; the docs travel in the same commit; a commit says what was verified and what was not.
- **Every visible build gets a picture.** `snapshot_release.py` renders that release from git into `snapshots/history/`, a hand-written line goes in `changes.json`, and `history_index.py` rebuilds [snapshots/CHANGES.md](../snapshots/CHANGES.md). This was done backwards from build-1002 on 2026-11-06, so the record starts at the first page.
- **Not done here, and worth doing:** the Calley guide's adversarial audit (finders, then refuters who try to disprove each finding). The browser audit (B8) is automatic and narrow; it is not that.

## A4. Honest states (the part most worth copying)

| Situation | What the page does |
|---|---|
| Waiting for the first data | Placeholder blocks in the shape of what is coming; the container is marked busy (`aria-busy`) |
| Nothing there | A sentence that says what would fill it ("Items you order are listed here with a running total") |
| Not available yet | A disabled control marked **soon**, and only while it is a promise; build it or remove it |
| Live | "Live, updated 2 s ago", with a green dot |
| The server stops answering | After 10 s: "Connection lost. Showing data from N s ago"; the last data stays on screen, never a blank page |
| Signed out (a session ended mid-use) | A banner with a Sign in button; the browser's own password box never appears (DEC-050) |
| Demo data | "This shows made-up demo data." at the top of the page (B-11) |
| Too many wrong tries | The form shuts and counts down to the second the server gave; even the right PIN waits |
| A shop with no PIN | The sign-in page says so and disables the form instead of letting someone guess |
| Indicative figures | Tagged **indicative**, with a line saying where the figures come from and that they are not a bank's (DEC-047) |
| A call that ordered nothing | Still leaves a one-line record, so the dashboard shows that a call happened (B-88) |

Anti-patterns removed on the way: a tile repeating a panel; seven zero bars for a week with no sales (one empty message instead); a percentage worked out from yesterday's zero; a "Needs you" tile counting things the panel already listed.

## A5. Interaction design rules we applied (and where)

| Principle | What we did |
|---|---|
| **Fitts's law** (big, near targets) | 44 px targets on a touch screen (`@media (pointer: coarse)`), 24 px everywhere at least; the sign-in button is 52 px; the audit flags anything smaller (B8). Calley used 48 dp; we stayed at 44 and wrote that down |
| **Hick's law** (fewer choices) | One primary button per screen; the admin's tabs default to All with a count on each; "soon" items are disabled, not hidden, and removed once decided |
| **Recognition over recall** | Every keyboard shortcut is shown in its control's tooltip (T theme, B menu, M mute, Ctrl K search); the PIN field has a show button |
| **Feedback** | "Live, updated N s ago"; "Signing in..." on the button; tries left; a countdown; "Applies to the next call" beside each save |
| **Error prevention** | A shop's link name is checked as you type; a stock row that is wrong stops the save with the row named; the busy guard refuses a second submit (DEC-050) |
| **User control** | Undo on "Marked solved"; the notice comes back only when the numbers change; Sign out on both dashboards |
| **Consistency** | One component kit for both dashboards and the admin; the same colour means the same thing everywhere (green ready, blue money and thinking, violet credit, amber pending, red error) |
| **Task flow** | The primary button directly follows the fields it submits; detours ("Back to the call page", "Admin sign in") come after it |
| **Wayfinding** | Dashboard to call page (a menu item), call page to dashboard (a header link on a shop's own address), admin to both for every shop (2026-11-07) |
| **Minimal** | Flat solid surfaces, one radius, no gradients, one hard-edged accent per screen (the call button, the hero figure) (DEC-049) |

**The PIN pad rule.** Generated PINs are digits, so the field opens the number pad on a phone (`inputmode="numeric"`), but a PIN someone chose may use letters, so a **Use letters** switch changes the keyboard. Do not force a keyboard the data does not guarantee.

## A6. Security of a page that shows other people's text

1. Text nodes only, through one builder (`h()`), with a test banning `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `eval` and `new Function`.
2. A strict content security policy (`default-src 'none'`, inline script and style only, `connect-src 'self'`, `frame-ancestors 'none'`), plus `X-Frame-Options: DENY`, `nosniff`, `no-store`, no referrer.
3. **Sign in without a URL ever holding a secret.** The server here answers GET only, so the sign-in page sends the PIN once in an `Authorization` header and receives a session cookie that is `HttpOnly` (no script can read it) and `SameSite=Strict` (never sent from another site); `Secure` behind https. Sessions live in memory with a scope (`admin` or one shop), 12 hours or 30 days if kept (DEC-050).
4. **Who is asking decides the answer to "not signed in":** a browser opening a page gets the sign-in page (401, no `WWW-Authenticate`, so no native box); the page's own background request gets a bare 401; a script gets the Basic challenge as before, so old tools keep working.
5. Roles are separate: a shop's PIN never opens the admin page, whatever user name is sent; a shop's session never opens another shop.
6. Guesses are throttled per address and shop (5, then a minute); a valid session is not blocked by a lock, because the lock is about guessing.
7. A page that must write uses a WebSocket with a short-lived token fetched by a signed-in request, and the socket refuses an Origin that is not this server (build-1009).
8. Validate on the page to help the typist and on the server because the page is not trusted.
9. **Never weaken security to make a demo work.** When a password was needed to drive the sign-in in a test browser, the password stayed out of the transcript: the server-side sign-in ran in-process and only the session cookie went to the browser (2026-11-07).

## A7. When the look "feels AI generated": build two, choose per element, merge (DEC-051)
This happened once here, on 2026-11-08, and worked. The full record with the picture-by-picture choices is in [frontend.md](frontend.md), "How the two looks became one".

**The symptom.** The person cannot say what is wrong, only that it looks generic. Here it was the way things were *highlighted*. Four defaults gave it away:
- a status as a soft tinted pill;
- the open menu item as a tinted rounded row with a round count bubble;
- a notice as a tinted box with a border;
- a live state as a coloured dot.

Colours and layout were not the problem; those had been settled (DEC-049).

**The method, in order:**
1. **Name the pattern, not the colours.** Restate the complaint as the list of devices (pill, tinted row, bubble, dot, boxed banner) and confirm that the *difference* they show must stay. Only how it is shown changes.
2. **Offer three directions as text sketches before any code.** Take each from the product's own world, not from a style name. Here: the shop's account book (khata), a till receipt, a register's index tabs. Each sketch showed the same three things (a menu item, a card's status, a notice) so they could be compared.
3. **Build the ones the person likes as override stylesheets, in parallel.**
   - One file per look, injected over the real running pages only while pictures are taken (a `<style>` added through the browser's debugging protocol). The product is untouched, so nothing has to be undone.
   - The same capture script for every look: same pages, same states, both themes, phone and desktop. That way the pictures differ only by the look.
   - Two looks were built at once by two agents. Each looked at its own pictures and fixed what was off before handing back.
4. **Save both before choosing.** Keep the stylesheets, the pictures and a side-by-side table of what each element becomes and what each look costs (here [`snapshots/prototypes/`](../snapshots/prototypes/)). The rejected half is the record of what was tried.
5. **Let the person choose per element, and only listen while they do.** Here Surya sent 22 crops, each with a one-line verdict, and asked for nothing to be built until he said so. After every crop, read back the running list. The result was a mix: of 14 elements, 8 came from index tabs and 6 from khata (frontend.md has the table).
6. **When two picks disagree, find the rule behind them, say it, and let them correct it.** Two rules came out:
   - *By page:* the shop dashboard's live call is a solid tab, the admin's is an outlined box. The dashboard is read from across the counter.
   - *By width:* the menu's open item is a tab on a desktop and a double underline on a phone, where a tab cannot reach the page.

   A later, closer pick overrides an earlier whole-page one. A question left unanswered is decided toward the pictures they called best, and said so.
7. **Apply the person's adjustments literally.** "Straight and professional" became: no tilt, no ink texture, the page's own font, a 1 px line. "Without the line" became: the notice's top rule removed. Neither was reinterpreted.
8. **Merge into the components, not as a layer.**
   - Each rule goes into the stylesheet of the component it styles.
   - The new colours get tokens (here `--on-ink` for text on a solid tab, and `--paper` and `--paper-ink` for the slip).
   - Anything that was text in CSS `content` becomes markup, so assistive technology reads it. The prototype's "DEMO DATA" became a real `<span class="nlabel">`.
9. **Check it like any other change.**
   - Retake the same pictures from the real pages. Here the first retake caught a cascade bug: a later stylesheet reset the card gap, so the tabs touched the card above.
   - Add a contrast pair for every new ink (62 of 62 pass).
   - Update any test that banned a technique the new look uses on purpose. The "no glow" test now allows only the hard-edged `radial-gradient` shapes.

**A second pass, the next day (2026-11-09).** After the merge, Surya sent two more rejections: "I don't want this line design" (the thin rule down the left of the call card's notes) and a crop of a green vertical bar (the edge before "Live, updated", and the pen caret in the live-call box), with "we did research for replacing this kind of design; if we need colour, do the research again".
- **Lesson:** the rejected thing is a *kind* of mark. A dot, a bar and a caret are the same tell. After one is rejected, list every place that uses the kind (here: the notes' left rule, the freshness edge, the caret) and replace them together, not one at a time.
- **Research, done properly and with its limits said.** Two web searches (live-status indicators; status without colour alone). They found:
  - Component libraries mostly default to a pulsing dot, with the pulse optional. ServiceTitan's design system pulses only for states that need attention ([Anvil status light](https://v1.anvil.servicetitan.com/components/status-light)).
  - Alternatives in use: a static label beside a "last checked" time, swapping the icon or the date text for a green "Live" word ([CNOE spec](https://cnoe-io.github.io/ai-platform-engineering/specs/live-status-indicator/087-live-status-indicator-spec)), and explicit online / offline / reconnecting words ([PhiaUi StatusIndicator](https://hexdocs.pm/phia_ui/PhiaUi.Components.StatusIndicator.html)).
  - WCAG 1.4.1 (Use of Color) needs a second cue, such as text or a shape, next to colour ([W3C Understanding 1.4.1](https://www.w3.org/WAI/WCAG21/Understanding/use-of-color)). Oracle's guidance adds that status should not rely on blinking ([Oracle](https://docs.oracle.com/cd/F86650_01/pt859pbr5/eng/pt/tacs/ProvidingAlternativestoColorCodingtoConveyMeaning-ba7fc3.html)).
  - **Not found:** any comparison or usability study of these alternatives; the sources are examples of practice, not evidence of what works best. Nothing was found on "last updated" time patterns.
- **What it led to:** say the state in a word, in a tab shaped like the statuses: green LIVE or red OFFLINE, then the time as plain text. The live-call box keeps its outline and bold green words and loses the caret, which also removes the only blinking element.

**What to copy into another project:**
- The trigger words: "AI generated", "generic", "template".
- The four tell-tale devices.
- Directions taken from the product's own world.
- Override stylesheets with one shared capture script.
- Per-element choice, rules for conflicts, and merging into tokens and components.

**What not to copy:** this project's particular mix. It was right for a kirana shop's screens and for Surya's eye; another product should run the method, not reuse the result.

## A8. Onboarding: say what is empty, then a short tour that can always be left (DEC-052)
Done once here, on 2026-11-09, from a small pasted example (an empty state with an explanation and one button, and a coach mark on one button). The build is in [frontend.md](frontend.md), "Onboarding: empty states and a first-visit tour".

**Research, with its limits said.** Two web searches, read as examples of practice and not as evidence:
- *Empty states.* Nielsen Norman Group frames an empty state as doing three jobs at once: it says the system status (nothing here yet), teaches what belongs there, and gives a way into the key task ([NN/g video summary](https://www.nngroup.com/videos/empty-states-in-application-design-guidelines/); the search did not return the full article, so the rest comes from guides that cite it). The guides agree on a short title, one description, an optional picture and **one** action, with the headline starting with a verb ([Setproduct](https://setproduct.com/blog/empty-state-ui-design), [UX Planet](https://uxplanet.org/empty-state-design-a-practical-guide-94ad0adbda45)).
- *Tours.* Most sources say to keep a tour to 3 to 5 steps (one says up to 7), make it skippable at any point, and let it be replayed from a help menu. The step counts and the claim that skippable tours finish more often come from vendor blogs, with no independent study, so the build follows the direction (short, skippable, replayable) and not the numbers. For keyboards: move focus into the tip when a step opens, treat it as a non-modal dialog, let Tab stay in it, let Escape end it, and give focus back when it ends; where focus should go at the end differs between libraries, so it goes back to the button that replays the tour. One guide calls spotlight tours the hardest pattern to make accessible and warns they break first at 200% zoom ([EZUD](https://ezud.com/accessible-onboarding-tutorials/), [Adobe Spectrum coach mark](https://spectrum.adobe.com/page/coach-mark), [Elastic EUI tour guidelines](https://eui.elastic.co/pr_8515/new-docs/docs/display/tour/guidelines)).

**What to copy.**
1. An empty list gets a title, one sentence on what will appear and, if something on the page can start it, one action. If nothing can start it, leave the action out.
2. A tour is short (here 4 steps), points at things the person will use first, says "Step N of M" in words, and always has Skip. Ending it any way counts as seen.
3. It starts by itself only once, and never when the browser cannot remember that it did (a private window): it would come back every visit. A menu item replays it.
4. Test it with a fresh browser profile every time, or the "first visit" is never really first; and make the screenshot and audit tools mark it seen, or they photograph the tour on every page.
5. Re-place the ring after a resize, a scroll and the end of any transition, because the thing it points at may still be moving.
6. Leave out what the person has rejected: the example's row of progress dots stayed out, because dots had been rejected.

---

# Part B: This stack (plain web pages served by a Python app)

## B1. Stack and the reasons

| Choice | Why | What it cost / what was rejected |
|---|---|---|
| Plain HTML, CSS and JavaScript, no framework | Four small pages; nothing to install or upgrade; one response per page; the component *structure* carries over to any framework | A framework becomes worth it when a page has many interactive states sharing data, or a team needs it |
| A ~90-line composer (`dukaan_dost/webpage.py`) | `{{include:path}}` stitched in at request time, so each page is one self-contained response and the strict policy holds | Includes cannot leave the components folder, nesting is limited, a missing component is an error, never a gap |
| The HTTP hook of the `websockets` library (the same port as the call) | One port for the call, the pages and the admin socket | **GET only, no request bodies**: writes go over a WebSocket (DEC-042) and the sign-in uses a header (DEC-050) |
| Inline SVG icon sprite (`shared/icons.html`) | No icon font, no download, styled by `currentColor` | Each icon is hand-written paths |
| System fonts, Inter and IBM Plex Mono only if installed | Nothing fetched from outside | The look varies a little by machine |
| Node's built-in test runner for the pages | Tests the page's own code with no browser and no packages | Needs Node 20+ |
| Headless Chrome over the DevTools protocol, no packages | Screenshots, audits and real flows with only Node 20 and Chrome | A small hand-written client (`scripts/ui_check/*.mjs`) |
| pytest with a real server on a free port | Sign-in, sessions, the socket and every command end to end | About four minutes for the whole suite |

## B2. Architecture

```
dukaan_dost/
  webpage.py          the composer: {{include:path}} → one page
  dashboard.py        /s/<shop>/dashboard, /data, /session[/keep], /signout
  admin.py            /admin, /admin/data, /admin/token, /admin/ws, /admin/session, /admin/signout
  admin_actions.py    every admin change, each testable on a temporary folder
  login.py            the sign-in page and the session endpoints (DEC-050)
  auth.py             hashed PINs, the admin password, sessions, cookies, the throttle
  preview.py          every page with made-up data and no keys: python -m dukaan_dost.preview
  web/
    index.html  dashboard.html  admin.html  login.html     a page = the list of its components + its controller
    components/
      shared/   tokens, base, atoms, panel, theme button and script, side menu, top bar, tiles, pills, lists, forms,
                skeletons, notices, the DOM builder, formatters, key check, polling, view switcher, sign-in, sign-out
      call/  dashboard/  admin/     what only one page uses
```

- **A page file is a list.** `dashboard.html` is the `{{include:...}}` lines for its styles, markup and scripts, and nothing else of substance.
- **An organism is up to three files with one name:** `x.html`, `x.css`, `x.js`. A component never holds its own `<script>` or `<style>` tag; the page owns those (a test).
- **Pure helpers sit between two markers** (`/* ---- helpers` and `/* ---- end helpers ---- */`) in the page script, so Node pulls them out of the *composed* page and runs them with `new Function`: the tests run the code the browser runs.
- **Sections are views of one page,** switched by the address fragment (`#orders`, `#edit/<shop>`), so polling continues and Back works (`shared/views.js`).
- **Live data is polled** every 3 to 5 seconds (`shared/poll.js`); a 401 shows the signed-out banner, a network error keeps the last data.

## B3. Design system

### B3.1 How the look changed, and why (pictures in [snapshots/CHANGES.md](../snapshots/CHANGES.md))

| Build | Look | Why it changed |
|---|---|---|
| 1002 | One white card on a pale page | The first browser call page |
| 1005 | Warm cream, muted green; a call screen and a dashboard with a menu | A bare card showed a viewer nothing |
| 1006 | "Kirana Green": white cards on pale slate, one colour per meaning | Two pages should look like one product |
| 1007 | Bento grid, glass over coloured glows, hard-edged accents, a drawer menu, Auto / Light / Dark | Surya asked for bento, glass, brutalism and minimalism together; each was given one job (DEC-041) |
| 1010 | The admin alone: near-black and lime, from a reference dashboard | Surya asked for that reference's dark look |
| 1012 | **One neutral palette on every page**: charcoal and off-white, one calm green, no glass, no glows | "Too much"; and flat colours can be measured exactly (DEC-049) |
| 1018 | **Highlights from the product's own world**: statuses as index tabs on the cards' edges, the open menu item as a tab into the page, notes as paper slips, the live state said as a word in a tab (LIVE / OFFLINE) | The tinted pills, rows, bubbles and dots "felt AI generated"; two prototypes were built and Surya chose per element (DEC-051, section A7) |

The lesson: mixing named styles works only when each has one job; and the plainest version that keeps one strong accent is the one that survived. The second lesson (1018): when the plain version then looks generic, the fix was not more colour but marks taken from the product's own world.

### B3.2 Tokens (copy these as a starting point)

Defined once in `components/shared/tokens.css`: light on `:root`, dark under `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }` **and** `:root[data-theme="dark"]`, with the same names. Ratios are measured by `contrast.py` (WCAG 2; 4.5:1 text, 3:1 parts) and saved in `snapshots/latest/reports/contrast.md`.

| Token | Light | Dark | Job | Measured |
|---|---|---|---|---|
| `bg` | `#F3F3F1` | `#141415` | page | `ink` on it: 15.31 / 15.60 |
| `surface` / `surface2` | `#FFFFFF` / `#EBEBE8` | `#1D1D1F` / `#272729` | cards / chips, fields, bubbles | `muted` on `surface`: 7.41 / 6.95 |
| `ink` / `muted` | `#1C1C1E` / `#55555A` | `#ECECEE` / `#A6A6AC` | text / captions | all pairs ≥ 6.16 |
| `line` | `#DADAD6` | `#343437` | hairlines | (not text) |
| `green` / `green-ink` / `green-soft` | `#1F7A4D` / `#17613C` / `#E2EEE6` | `#5DBB8A` / `#86D4AB` / `#1F2E26` | brand, active, ready | `on-green` on `green`: 5.32 / 8.10 |
| `blue` / `blue-soft` | `#1D4ED8` / `#E4EAF6` | `#8FB4F0` / `#1F2633` | money, thinking, the hero figure | 5.55 / 7.20 |
| `credit` / `credit-soft` | `#6D3FD6` / `#EEE8F8` | `#BBA3F0` / `#2A2536` | credit (udhaar) | passes |
| `amber` / `amber-soft` | `#A64C08` / `#F3EAD0` | `#E6B24A` / `#322B1A` | pending, warning, focus ring | 4.78 / 7.24 (was 4.21, B3.1) |
| `warn` / `warn-soft` | `#B91C1C` / `#F6E1DE` | `#F28B82` / `#382221` | errors, broken | 5.16 / 6.20 |
| `end` / `on-end` | `#DC2626` / white | same | the hang-up button | passes |
| `brut` | `#1C1C1E` | `#ECECEE` | the hard edge and shadow of the one accent | must differ from what it sits under |

Shape: card radius 22 px, button radius 12 px, gaps 14 px between cells and 8 to 12 px inside, no shadows on ordinary cells. Type: Inter (if installed) then the system font; numbers in a monospace stack with tabular figures; small uppercase tracked labels for field and tile names.

### B3.3 Theme mechanics
- Three choices, **Auto, Light, Dark**, cycled by one button or **T**; the choice is saved (`localStorage` key `dd:theme`) **including Auto**, so Auto is a choice and different from never having chosen.
- A tiny script in `<head>`, **before the CSS**, sets `data-theme` from the saved choice, so there is no flash. A page can have its own default (the admin and its sign-in start dark: `window.DD_DEFAULT_THEME`).
- Every `localStorage` access is in try/catch (private windows, blocked storage).
- `color-scheme` is set with the theme so native controls match.

### B3.4 Rules that keep it consistent
1. A colour is a token; a test fails on any literal colour outside the token rules.
2. Status is a pill with a word. One colour per meaning on every page.
3. One primary action and one hero per screen; the hard-edged `brut` accent on at most those two.
4. A class means one thing everywhere (`.order-total` on the call page is not the dashboard's `.total`).
5. Change a token in one file; pages keep no copies.
6. Sentence case; plain words; say what saving does ("Applies to the next call").

## B4. The component kit (`web/components/shared/`)

| Component | Job | Notes |
|---|---|---|
| `tokens.css`, `base.css` | The palette; the reset, focus ring, 44 px touch rule | The only place a colour is written |
| `atoms.css` | `.mark`, `.chip`, `.dot`, `.tag`, `.soon`, `.empty`, `.brand` | One visual idea each |
| `icons.html` | The SVG sprite | `<svg class="i"><use href="#i-name"/></svg>` |
| `panel.css`, `tile.css`, `icon-tile.css` | A panel with its heading row; stat tiles with an icon square | The hero tile is wider, not taller |
| `status-pill.css` | Dot plus word | Never colour alone |
| `side-menu.*`, `menu-init.html`, `shell.css` | The drawer menu: hides with a button or **B**, remembered, applied before paint, leaves the tab order while hidden | On a phone it becomes a wrapped row |
| `topbar.css`, `theme-button.*`, `theme.js`, `theme-init.html` | The top bar; Auto / Light / Dark | Theme set before the CSS |
| `skeleton.css` | Placeholder blocks while loading | Not the empty state |
| `notices.css` | Banners: demo data, signed out, errors | Plain words |
| `forms.css` | Labelled fields, hints, `.btn`, `.btn.primary`, messages | Every field has a visible `<label for>` |
| `dom.js` | `h(tag, attrs, ...children)`, text only | The only way a page builds markup |
| `format.js`, `keys.js` | Rupees with Indian grouping, dates; the shortcut guard | Shortcuts ignore typing, held keys and Ctrl / Alt / Cmd |
| `poll.js`, `views.js` | Live data; sections as views of one page | "Connection lost" after 10 s |
| `login-*`, `signout-*` | The sign-in card and its helpers; the Sign out button | DEC-050 |
| `brutal.css` | The one hard-edged accent; presses in on click | Respects reduced motion |

The full pattern catalogue (stat tile, needs-attention list, filter tabs with counts, search with Ctrl K, dismissable notice, mark solved, add and edit forms, table editor, copy a link, activity log, read-only panel fed by the server, call screen) is in [frontendgnaniskills.md](frontendgnaniskills.md), section 7.

## B5. Pages and how they connect

| Page | Address | For | Built |
|---|---|---|---|
| Call page | `/s/<shop>/` (and `/` for the default shop) | A caller | build-1002, call screen build-1005, loan quote build-1011 |
| Shopkeeper dashboard | `/s/<shop>/dashboard` | The shop's owner, with the shop's PIN | build-1003, redesigned build-1005 and 1007 |
| Admin | `/admin` | The operator, with the admin password | build-1009, dark look and search build-1010 |
| Sign-in | the dashboard's or admin's own address when signed out | Both | build-1015 |

Links between them: the dashboard's menu has **Call page**; the call page's header has **Shopkeeper dashboard** on a shop's own address; every admin row has **Shop dashboard** and **Call page**; the sign-in page has **Back to the call page** and **Admin sign in**; both dashboards have **Sign out**.

**The call screen's states** are worked out by the page from what it is doing: idle, connecting, listening (the waveform follows the caller's microphone), thinking (until the first reply; given up after 12 s because not every turn gets a spoken reply), speaking, muted, ended. The order panel is read-only: the caller changes the order by voice. A stop resets the playback counter, or "speaking" could stick for the rest of the call (B-25).

## B6. Forms and the sign-in
- One `submit` handler for the button and the Enter key, starting with a busy guard; the button says "Signing in..." and refuses a second press.
- The field is marked invalid (`aria-invalid`) and the message is in a live region (`role="alert"`), worded by cause, with the tries left.
- A hidden, labelled, read-only username field lets a password manager save the PIN. Hide it with a rule that beats `input[type=text]{width:100%}`, or it stretches the page (B7).
- After the right PIN the page reloads the same address, which now answers with the dashboard; if the browser did not keep the cookie, it says so after 4 s instead of spinning.
- Validate before the network; the server checks again; the server's answer (`wrong`, `remaining`, `locked`, `retry_after`, `empty`) is data, and the words are made on the page from it (`loginOutcome`, tested in Node).

## B7. Accessibility and layout: the traps we actually fell into

| Trap | Symptom | Fix |
|---|---|---|
| A visually hidden input styled by `.sr`, beaten by `input[type=text]{width:100%}` | The sign-in page scrolled sideways to 1,703 px at 1280 | A more specific rule (`.login .sr`); the audit names the element that pokes out |
| `aria-hidden="true"` on a focusable helper field | A control with no name in the audit | Give it `aria-label` and `tabindex="-1"`; never hide a focusable thing from assistive tech |
| A checkbox measured alone | 20 x 20 px, under the 24 px floor | The label is part of the same control: measure the label (the audit now does) |
| A switch row 20 px tall | Too small to tap on a laptop | `min-height` on the row; put it before the touch rule, or it overrides the 44 px rule (build-1012) |
| No `<main>` on the call page | No landmark to jump to | The grid became `<main>` (build-1012) |
| Search box, hide-menu and notice-close buttons under 44 px on touch | Audit warnings | Raised on a coarse pointer only (build-1012) |
| The admin page ignores the device theme (it starts dark) | An audit run "in light" was really dark | Set the theme the way a person does, through the saved choice, before the page loads |
| A brutalist shadow the same colour as its button | The button looked notched | A near-white edge in dark, near-black in light (DEC-049) |
| Pixel font sizes | A browser's text-size setting does not scale the pages | **Open**: not fixed; known gap (B11) |
| Zoom: 130%, 150% and 200% on a phone are windows 300, 260 and 195 px wide | A search box, a panel's tag, quick-action buttons, a notice's dismiss button each pushed the page sideways; Recent orders passed the sideways test but broke every word one letter to a line | Test at those widths (the audit does now); let heading rows and buttons wrap; stack a table row into one column; keep a figure whole. **"No sideways scroll" is not "readable": look at the pictures** (frontend.md, "Zoom") |

Also done: every field has a visible label; every button a name (tested); state is exposed (`aria-pressed`, `aria-expanded`, `aria-current`, `aria-busy`); reduced motion stops pulses and slides; colour is never the only signal; zoom is never blocked.

## B8. Testing: how the pages were made reviewable without a phone

**The ladder, cheapest first:**
1. **Pure helpers in Node** (`tests/web/*.test.mjs`): formatting, labels, the needs-attention rule, filters, the sign-in's words, the call link. 120 page tests at the last run.
2. **Rule tests on the composed page source:** no banned DOM calls, no outside addresses, no literal colours, every field labelled, every button named, the theme script before the CSS, no inline event handlers, the placeholders the server fills.
3. **Server tests with a real server** (pytest, 1,200 at the last run): sign-in cases (none, wrong, another role, no password set, throttled, forged and expired cookies, a PIN in a URL), sessions and scopes, the socket (right token, wrong token, no token, another origin), every admin command end to end.
4. **Mutation checks:** put the bug back and see the test fail (a stray colour in each kind of component; the scope check, the HttpOnly flag and the lock check removed one at a time).
5. **The browser audit** (`audit.mjs`, all pages via `audit_all.py`): sideways scroll and what causes it, controls with no name, duplicate ids, targets under 24 px (error) and 44 px on touch (warning), the contrast of every visible text node from the real computed colours, `<title>`, `lang`, `<main>`. Last run: 0 errors, 0 warnings in 72 runs (9 page states, 2 themes, 360 / 390 / 768 / 1280 px).
6. **Real flows in a real browser** (`drive.mjs` with a steps file, such as `flows/login.mjs`): type, click, wait, compare what the page shows. The admin's 20 flows found a bug every unit test had missed.
7. **Snapshots, kept:** `snapshots.mjs` takes every page in every state into `snapshots/latest/` (138 images, light and dark, phone, tablet, desktop); `snapshot_release.py` renders a past release from git into `snapshots/history/`; `CHANGES.md` puts each release beside the one before.
8. **Look at them.** Every time. The overflow, the notched button and the empty two-row hero were all seen, not tested.

**Traps in the tooling, each of which cost time:**

| Trap | Fix |
|---|---|
| A shell heredoc turned `\b` in a regex into a backspace byte; the colour test could never fail | Write files with a file tool; mutation-check every rule test |
| An unquoted heredoc ran backticked words as commands | Quote heredocs, or write the file with a file tool |
| The contrast tool read the dark colours twice and never measured light, so "all pass" meant nothing | Test the tool itself: known answers, each theme reads its own values, a pale colour fails |
| A test took the first `<script>` in the page; adding a head script broke it | Select the main script, not the first |
| A flow re-run against a server that already held what it created | A fresh server per flow run |
| Every step failed with null elements | Wait until the server answers before starting the browser |
| The preview never registered the admin socket; every command failed in the browser while unit tests passed | Drive the real page against the preview; keep every entry point's wiring in step |
| A sign-in step reloaded the page and the browser dropped the step's evaluation | Split "send" and "check" steps; the driver retries a step cut off by a navigation |
| A browser click waited forever for "stable" in a background window | The element was fine (checked with `elementFromPoint`); click without the animation-frame wait |
| A capture of an old release failed once when Chrome did not start | Re-run that one release; the tool deletes and retakes its folder |
| The docs checker crashed on a tracked file that had been moved but not committed | Skip listed files that no longer exist |

## B9. Bug classes, with the fix each time

| Class | Instance | Fix |
|---|---|---|
| Two homes for one fact | A tile repeating a panel | Keep one; the count became a badge |
| A comparison that is not like with like | Today so far against all of yesterday | Yesterday up to the same time, and say so |
| An id checked for shape, not existence | Marking a problem solved for a shop that does not exist succeeded | Check what the id points at |
| Demo data that fails real validation | A save failed on valid input because the demo held an invalid item | Demo data passes the same checks as real data |
| A cached copy outlives an edit | A saved prompt did not reach calls | The agent drops its cached shop on save; a call in progress keeps what it has |
| A list that hides what is broken | A new shop with a broken `config.yaml` vanished from the admin | The admin lists shop-like folders; the agent keeps the strict list |
| An unbounded number from a file | `"total": 1e999` broke both dashboards (B-78) | Catch overflow where numbers are read |
| A text format split on characters JSON allows | Activity-log entries with U+2028 vanished (B-77) | Split on `\n` only |
| A test that fails by chance | A 6-digit PIN appeared inside a hex hash (B-40) | Compare values, not text search |
| `a && b && c` returning `undefined` | A search helper | `Boolean(...)`, strict equality in tests |
| An interruption that leaves a counter up | "Speaking" stuck for the rest of the call (B-25) | Reset on stop; count only the current generation |

## B10. Tried and dropped
Glass, the coloured glows and the navy dark theme (DEC-049); the admin's separate near-black and lime look; a hero tile two rows tall; a "Needs you" tile; the browser's own Basic-auth box (DEC-050); a sign-in by POST (the server cannot read bodies) and a token in the address (logged, kept in history); "soon" buttons nobody needed; a router, a state library and lazy-loaded screens (they solve problems four small pages do not have); one branch per piece of UI work.

## B11. Known gaps (be honest in the README)
Not tried with a real microphone in a real browser (B-08) or on a real phone; Chrome only (no Firefox or Safari); no screen-reader pass and no automated accessibility suite beyond the audit; https not seen (the Secure cookie flag is tested); a browser text-size setting does not scale the pages (pixel sizes); touch targets are 44 px where the Calley guide uses 48; no adversarial audit; the build number is not shown in the pages; older releases in `snapshots/history/` show landing pages only, not states inside a call.

---

# Part C: Build order, checklist, file map

## C1. If you were starting again: the build order

**Day 1: the things expensive to retrofit**
1. A reference and a "taken / left out" table (A2).
2. Tokens for light and dark with the same names; the Auto / Light / Dark switch before the first paint; a test that fails on a literal colour; the contrast tool, run once.
3. The composer (or your framework's equivalent) and the folders: `shared/`, one folder per page, pure helpers between markers.
4. The shell: menu, top bar, view switcher, theme button, polling, the text-only builder with its banned-calls test, the security headers.
5. The browser tools (screenshot, audit, drive) and **one page rendered in both themes at four widths**, before the second page.

**Day 2: the pages**
6. One honest page end to end: loading, empty, live, connection lost, signed out, demo data.
7. The other pages from the shared kit; each looked at in both themes before the next.
8. Sign-in done properly (a page, a session, causes, a lock), not the browser's box.

**Day 3: writes and the user's loop**
9. Writes once reads are solid: all-or-nothing functions with their own tests, a backup before every rewrite, nothing deleted.
10. Links between the pages each user moves between.

**Day 4: evidence and release**
11. The audit over every page state; fix to zero.
12. Snapshots into `latest/`; a picture per release into `history/`; `CHANGES.md`.
13. Mutation-check the rule tests; write what was not tried; a build report.

## C2. Pre-release checklist
- [ ] Every page looked at in light **and** dark at 360, 390, 768 and 1280 px; no sideways scroll
- [ ] The audit: 0 errors; every warning read and either fixed or written down
- [ ] Contrast measured and saved; every text pair ≥ 4.5:1, parts ≥ 3:1
- [ ] Every page has loading, empty, error, signed-out and demo-data states that say something true
- [ ] No literal colour outside the tokens; no `innerHTML` and friends; nothing loaded from outside
- [ ] Every field labelled, every button named, focus never on the body, shortcuts in tooltips
- [ ] Touch targets ≥ 44 px (or your project's rule) with a gap between neighbours
- [ ] Secrets shown once, never logged, never in a URL; fail closed; guesses throttled
- [ ] Each rule test seen to fail once
- [ ] `snapshots/latest/` retaken; this release in `snapshots/history/` with its line in `changes.json`
- [ ] The build report says what was not tried

## C3. File map (this repository)
```
dukaan_dost/web/                  the pages and components (B2)
dukaan_dost/{webpage,dashboard,admin,admin_actions,login,auth,preview}.py
tests/web/                        page tests (Node); composed.mjs builds a page the way the server does
tests/test_{webpage,dashboard,admin,admin_socket,login,ui_contrast}.py
scripts/ui_check/                 shot.mjs, drive.mjs (+ flows/), audit.mjs, audit_all.py, contrast.py,
                                  snapshots.mjs, snapshot_release.py, history_index.py
snapshots/                        latest/ (every page and state now), history/ (each release), CHANGES.md
MD/                               frontend.md (how the pages work now), frontendgnani.md (this file),
                                  frontendgnaniskills.md (the pattern catalogue), decisions.md, bugs.md,
                                  bugfixed.md, tried_and_failed.md, version_control.md, builds/
```

Commands:
```
python -m dukaan_dost.preview --port 8861 --no-browser       # every page with made-up data, no keys
node --test tests/web/  &&  python -m pytest                 # page tests, then everything
python scripts/ui_check/contrast.py                          # contrast of every token pair
SNAP_PIN=<pin> SNAP_ADMIN_PASSWORD=<pw> python scripts/ui_check/audit_all.py http://127.0.0.1:8861 snapshots/latest/reports/audit.txt
SNAP_PIN=<pin> SNAP_ADMIN_PASSWORD=<pw> node --experimental-websocket scripts/ui_check/snapshots.mjs http://127.0.0.1:8861
python scripts/ui_check/snapshot_release.py build-N NN-build-N  &&  python scripts/ui_check/history_index.py
```

## C4. Vocabulary
**Build** a user-visible numbered release (`build-N`). **InBul** an internal change (`InBulNN`). **Token** a named colour or size, the only place a value is written. **Organism** a whole panel: its markup, styles and script side by side. **Composer** the server step that stitches components into one page. **Helpers** the pure functions between the markers, tested in Node. **Hero** the one figure or action a screen is about. **Brut** the one hard-edged accent. **Preview** every page with made-up data and no keys. **Audit** the automatic browser check (B8). **Latest / history** the current full set of pictures / one set per release.
