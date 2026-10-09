# Storefront refresh

The store now has a warm olive and cream visual direction, an original SVG hero,
responsive category navigation, server-backed product search, size and price
filters, an in-stock filter, and cursor pagination. Filter URLs can be shared;
changing categories resets pagination while preserving the other filters.

Product cards display actual compare-at pricing when present. Product details
include breadcrumbs, delivery guidance and a horizontally scrollable related
collection. The homepage adds contact information, shopping FAQs and a footer
using the store settings. Loading skeletons respect reduced-motion preferences.
Catalogue failures are distinguished from empty search results, with a reload
action and WhatsApp contact. Catalogue and settings requests time out after eight
seconds. Fractional purchase quantities are rejected in the purchase controls.

The external decorative runtime and its watermark-hiding styles were removed.
The existing checkout and admin work was preserved. Motion powers the category selector, adapted from the MIT-licensed Kokonut Smooth Tab. The Kokonut carousel, tabs and search references
and Motion loading/footer references informed the interaction direction; this
implementation now includes an adapted Kokonut Smooth Tab with URL-backed category links and reduced-motion support. Other referenced packaged components and paid source code are not included.

## Launch work still needed

- Upload real merchandise photos through the existing admin photo workflow.
- Confirm delivery areas, fees, exchange terms and store contact details.
- Complete OPay merchant onboarding, enter the issued sandbox credentials, and
  run OPay's end-to-end approval tests before switching the adapter to production.
- Schedule abandoned-reservation expiry as described in the README.
- Run a full order/payment/fulfilment check with the configured live database and
  payment sandbox. Browser review of a storefront does not verify settlement.

Do not add fabricated sales counters, ratings, testimonials, delivery guarantees
or blanket exchange promises as visual filler.

