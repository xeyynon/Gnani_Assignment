# Shops

One folder per shop. The agent runs the folder named by `SHOP_NAME` (default
`dukaan_dost`), so this project's own shop goes in `shops/dukaan_dost/`.

```
shops/<name>/
  config.yaml              system_prompt (a string) and fallback_messages (language code -> text)
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
