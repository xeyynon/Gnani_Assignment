# Loop UI killer: how to stop going round in circles on how a screen looks

**Written for:** Surya, to reuse in another project, and any AI coding agent working for Surya. Everything below happened in this project between 2026-11-08 and 2026-11-09; nothing here is invented. The long record is in [frontend.md](frontend.md) ("Two candidate looks for highlights" and "How the two looks became one"), the reusable method in [frontendgnani.md](frontendgnani.md) (section A7), and the decision in [decisions.md](decisions.md) (DEC-051).

## The loop this breaks
A person says "this looks AI generated" or "I don't like it". The agent changes it. The person still does not like it. Another change, another round. Nobody can say what is wrong, and every round costs a build, a test run and a set of pictures.

## The idea in one paragraph
Do not ask the person to describe what they want. Show them **two complete versions side by side**, let them **pick per element** from the pictures, and **merge the picks** into one. Looking at pictures is easy for a person; describing a design is hard. One round of this replaced what would have been many rounds of guessing.

## The steps, as they were done here

1. **Name the pattern, not the colours.** The complaint was about the way things were *highlighted*: a status as a soft tinted pill, the open menu item as a tinted rounded row with a round count bubble, a notice as a tinted box, a live state as a coloured dot. Colours and layout were not the problem. Say that back to the person in a list. They confirmed the difference (the highlight) must stay; only how it is shown had to change.
2. **Offer three directions as text sketches, before any code.** Take each from the product's own world, not from a style name. Here: the shop's account book (khata ledger), a till receipt, a register's index tabs. Each sketch showed the same three things (a menu item, a card's status, a notice), so they could be compared. This was one question with three options.
3. **Build the ones they like, as prototypes, without touching the product.**
   - Surya liked two of the three and asked to see both before deciding.
   - Each look was one stylesheet, added over the real running pages only while pictures were taken (the pages' policy allows inline styles, so a `<style>` could be added through the browser's debugging protocol). Nothing in the product had to be undone.
   - Both were built **at the same time by two agents**, each with the **same capture script**: 8 pictures per look (dashboard overview, Calls, Orders, call page, admin; light and dark; desktop and phone). Same pages and same states, so the pictures differ only by the look.
   - Each agent looked at its own pictures and fixed what was off before handing back.
4. **Save both before choosing.** The stylesheets, the pictures and a table of what each element becomes and what each look costs went into the repo ([snapshots/prototypes/](../snapshots/prototypes/)). The look that is not chosen is the record of what was tried.
5. **Let the person choose per element, and only listen while they do.**
   - Surya said not to do anything until he said "start". He then sent 22 crops of the pictures, each with a one-line verdict ("this is better", "this is better but without the line", "is this becomes straight and professional this would look good").
   - After every crop the running list of choices was read back to him. Nothing was built during this.
6. **When two picks disagree, find the rule behind them, say it, and let them correct it.** Two rules came out:
   - *By page:* the shop dashboard's live call is a solid tab, the admin's is an outlined box. The dashboard is read from across the counter.
   - *By width:* the menu's open item is a tab on a desktop and a double underline on a phone, where a tab cannot reach the page.

   A later, closer pick overrides an earlier whole-page one. A question left unanswered was decided toward the pictures they had called best, and said so.
7. **Apply their adjustments literally.** "Straight and professional" became: no tilt, no ink texture, the page's own font, a 1 px line. "Without the line" became: the notice's top rule removed. Neither was reinterpreted.
8. **Merge into the real components, not as a layer.** Each rule went into the stylesheet of the component it styles. New colours became tokens (`--on-ink`, `--tab-fold`, `--tab-r`, `--paper`, `--paper-ink`). Anything that had been text in CSS `content` became a real element, so a screen reader reads it (the prototype's "DEMO DATA" became a `<span class="nlabel">`).
9. **Check it like any other change.** The same pictures retaken from the real pages, a contrast pair for every new colour, the browser audit, and the tests.

**The result:** 14 elements, 8 taken from index tabs and 6 from khata, in the table in [frontend.md](frontend.md).

## The second pass, the next day
Two more rejections came after it was built: "I don't want this line design" (a thin rule down the left of the notes on a call card), and a crop of a green vertical bar (the edge before "Live, updated" and the blinking pen caret in the live-call box), with "we did research for replacing this kind of design; if we need colour, do the research again".
- **The lesson:** what gets rejected is a *kind* of mark. A dot, a bar and a caret are the same tell. When one is rejected, list every place that uses the kind and replace them together.
- **What replaced them:** the state said in a word, in a tab shaped like the statuses: green **LIVE** or red **OFFLINE**, then the time in plain text. Nothing blinks.
- **The research** (two web searches) is in [frontendgnani.md](frontendgnani.md) A7 with its sources, and with what it did not show: no source compared these designs, and WCAG 1.4.1 says colour must not be the only signal.

## Traps hit while doing it
- **A later stylesheet undid the spacing.** The first picture of the merged look showed every status tab touching the card above, because the lists stylesheet loads after the status stylesheet and set the gap back to 10 px. Only looking at the pictures showed it.
- **A test banned a technique the new look uses on purpose.** The admin's "no glow" test banned every `radial-gradient`; the open menu tab's corners and the paper note's punched holes use it. The test now allows exactly those two and still bans blur.
- **A look that is only a prototype is not tested.** Contrast was not measured for either prototype (the script reads the real tokens). It was measured after the merge: 62 of 62 pairs pass.
- **"No sideways scroll" is not "readable".** The merged pages passed the audit at 200% zoom while one table broke every word one letter to a line. Look at the pictures at the narrowest widths.
- **A shell quoting error ran nothing.** Several edit scripts broke on quotes in a heredoc; writing the script to a file and running it was reliable.

## How to know the loop is dead
- The person has chosen per element, in their own words, and the choices are written down.
- The pictures from the real pages match the choices, in both themes and on a phone.
- The rejected look is saved, so nobody asks "what about the other one" later.
- Every new colour has a measured contrast pair, and the checks pass.
- The same kind of mark is not left anywhere else on the pages (dots, bars, lines).

## Start prompt for the next project
> This screen looks generic ("AI generated") to me. Do not change it yet. First, say back the devices you think give it that look (as a list). Then give me three directions, taken from what this product is about, as short text sketches that each show the same three things (a menu item, one status, one notice). I will pick two. Build those two as stylesheets laid over the real pages, take the same pictures of each, keep both, and put a table beside the pictures of what each element becomes and what each costs. Do nothing else until I say "start". Then I will send you my choices element by element; read the running list back after each one, name the rule when two disagree, and ask me about anything I have not answered. Build the merge into the real components, with new colours as tokens, and check it with pictures and a contrast measure.

## What this does not cover
It was tried once, by one person, on one product. It took a day, two parallel agents and 22 pictures from the person. It does not tell you what the right look is; it only gets the person's own eye into the decision quickly. Another product should run the steps, not copy the result.
