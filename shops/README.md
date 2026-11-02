# Shops

One folder per shop. The agent runs the folder named by `SHOP_NAME` (default
`dukaan_dost`), so this project's own shop goes in `shops/dukaan_dost/`.

```
shops/<name>/
  stock.json               what the shop sells (the source of truth; see below)
  config.yaml              system_prompt (a string), fallback_messages (language code -> text),
                           and optionally display_name (what the greeting and pages call the shop)
  knowledge/
    core/always_on.md      sent on every turn
    products_pricing.md    ┐
    ordering_payment.md    │
    delivery_shipping.md   │  only these file names are read
    packaging.md           │  (KNOWLEDGE_FILES in dukaan_dost/knowledge_retriever.py)
    refund_policy.md       │
    payment_issues.md      │
    faq.md                 │
    recommendations.md     ┘
```

Each topic file is split on `##` headings, and the sections are scored by keyword
overlap with what the caller said. Put each product (or small group) under its
own `##` heading, with its English, Hindi and Telugu names in the same section.

**All data here is synthetic**: made-up products, prices, shop details and
customers. No real phone numbers, IDs or addresses.

**Adding a shop:** copy a shop folder, rename it (lower case letters, digits, `_` and `-`, 2 to 40 characters), edit `config.yaml` and the knowledge files, and set its dashboard PIN with
`python -m dukaan_dost.auth set-pin <name>`. Its call link is `/s/<name>/` and its dashboard `/s/<name>/dashboard`.

**The stock list.** `stock.json` holds every item (SKU, English, Hindi and Telugu names, Latin-script
aliases, unit, pack, price, in stock). `knowledge/products_pricing.md` is generated from it, so edit
`stock.json` and run `python scripts/build_shop_knowledge.py shops/<name>`; the tests fail if the
generated file is stale. The same file gives the speech recogniser its product-name boost list.
`--keyterms` prints that list. Hindi and Telugu names should be checked by a native speaker.
