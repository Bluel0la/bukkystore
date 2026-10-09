import Image from "next/image";
import Link from "next/link";
import { CartLink } from "@/components/cart-link";
import SmoothTab from "@/components/kokonutui/smooth-tab";
import { ProductCard } from "@/components/product-card";
import { StoreBrand } from "@/components/store-brand";
import { StoreFooter } from "@/components/store-footer";
import { getCategories, getProducts } from "@/lib/catalogue";
import { shopHref, shopQuery, type ShopParams } from "@/lib/shop-query";
import { getPublicStoreSettings, whatsappLink } from "@/lib/store-settings";

export default async function Home({ searchParams }: { searchParams: Promise<ShopParams> }) {
  const query = shopQuery(await searchParams);
  const [categories, catalogue, settings] = await Promise.all([
    getCategories().catch(() => []),
    getProducts(query.toString()).catch(() => null),
    getPublicStoreSettings(),
  ]);
  const selected = query.get("category");
  const search = query.get("search") ?? "";
  const filtered = [...query.keys()].some((key) => key !== "limit" && key !== "cursor");
  const chat = whatsappLink(settings.whatsapp_number, "Hi! I'd love some help choosing an outfit.");

  return <>
    <a className="skip-link" href="#shop">Skip to the collection</a>
    <div className="announcement">Little wardrobes. Big adventures. <span>Delivery across Lagos ↗</span></div>
    <header className="store-header store-container">
      <StoreBrand name={settings.store_name} />
      <nav aria-label="Primary navigation"><Link href="/#shop">The collection</Link><Link href="#help">Good to know</Link><Link href="#visit">Visit us</Link></nav>
      <div className="header-bag"><CartLink /></div>
    </header>
    <main>
      <section className="store-container hero" aria-labelledby="hero-title">
        <div className="hero-copy"><p className="eyebrow">For the wonderfully little</p><h1 id="hero-title">Small outfits.<br />Big <em>personality.</em></h1><p className="hero-description">For playground days, party days, and all the little moments in between. Find their next favourite here.</p><Link className="store-button" href="#shop">Find their next favourite <span aria-hidden="true">↗</span></Link><p className="hero-note"><span aria-hidden="true">✳</span> Picked with care. Ready for play.</p></div>
        <div className="hero-art"><Image src="/little-adventures.svg" alt="Illustration of a little outfit, a knitted hat and a tiny shoe" width={640} height={580} priority /><span className="hero-sticker">A little<br /><em>everyday magic</em><span aria-hidden="true">✧</span></span><span className="art-caption">THE LITTLE ADVENTURES EDIT · ATITEN</span></div>
      </section>
      <div className="store-container service-strip"><p><span aria-hidden="true">↗</span><strong>Lagos delivery</strong><span>Area-based fees at checkout</span></p><p><span aria-hidden="true">♡</span><strong>A little help choosing?</strong><a href={chat}>Talk to us on WhatsApp</a></p><p><span aria-hidden="true">✓</span><strong>Less fuss, more play</strong><span>Shop without creating an account</span></p></div>
      <section className="store-container collection" id="shop" aria-labelledby="shop-title">
        <div className="section-heading"><div><p className="eyebrow">Their wardrobe, a little happier</p><h2 id="shop-title">{search ? `Results for “${search}”` : categories.find((c) => c.slug === selected)?.name ?? "Meet their new favourites."}</h2></div><span className="collection-note">Little finds. Lots to love.</span></div>
        <SmoothTab selected={selected ?? "all"} items={[{ id: "all", title: "All little things", href: shopHref(query, { category: null, cursor: null }) }, ...categories.map((category) => ({ id: category.slug, title: category.name, href: shopHref(query, { category: category.slug, cursor: null }) }))]} />
        <form action="/#shop" method="get" className="shop-filters" key={`filters:${query}`} role="search" aria-label="Find products">
          {selected && <input name="category" type="hidden" value={selected} />}
          <label className="search-field"><span className="sr-only">Search products</span><svg aria-hidden="true" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg><input name="search" placeholder="Find a little something…" maxLength={80} defaultValue={search} type="search" /></label>
          <label className="filter-field"><span>Size</span><input name="size" placeholder="e.g. 3–4Y" maxLength={40} defaultValue={query.get("size") ?? ""} /></label>
          <label className="filter-field"><span>Max. price (₦)</span><input name="budget" type="number" min="1" max="999999999" step="1" placeholder="Any budget" defaultValue={query.has("max_price_minor") ? Number(query.get("max_price_minor")) / 100 : ""} /></label>
          <label className="stock-filter"><input name="available" type="checkbox" value="true" defaultChecked={query.has("available")} /> In stock</label><button className="filter-submit" type="submit">Find pieces <span aria-hidden="true">↗</span></button>
        </form>
        <div className="results-meta"><span>{catalogue ? `${catalogue.items.length} pieces on this page` : "Our collection"}</span>{filtered && <Link href="/#shop">Clear filters ×</Link>}<span>Store picks first</span></div>
        {catalogue?.items.length ? <div className="product-grid shop-grid-enter" key={`products:${query}`}>{catalogue.items.map((product) => <ProductCard key={product.id} product={product} />)}</div> : <div className="shop-empty"><span aria-hidden="true">✳</span><h3>{catalogue ? "No little finds just yet." : "Our collection is taking a little break."}</h3><p>{catalogue ? "Try another search or clear your filters to discover something lovely." : "We couldn’t load the products. Please try again, or let us help you on WhatsApp."}</p><a className="store-button" href={catalogue ? "/#shop" : shopHref(query)}>{catalogue ? "Explore all pieces" : "Try again"} ↗</a>{!catalogue && <a href={chat}>Ask us on WhatsApp ↗</a>}</div>}
        <div className="shop-pagination">{query.has("cursor") && <Link href={shopHref(query, { cursor: null })}>← Back to first page</Link>}{catalogue?.next_cursor && <Link className="store-button" href={shopHref(query, { cursor: catalogue.next_cursor })}>More little finds →</Link>}</div>
      </section>
      <section className="store-container help-banner"><div><p className="eyebrow">A real store. A friendly face.</p><h2>Not sure what fits?<br />Let’s find it together.</h2><p>Tell us what you’re looking for. We’ll help with sizes, colours, and those “will they love it?” decisions.</p><a href={chat} className="store-button">Say hello on WhatsApp ↗</a></div><div className="help-flower" aria-hidden="true">✳<span>Chosen with<br /><em>little ones</em><br />in mind.</span></div></section>
      <section className="store-container shop-help" id="help" aria-labelledby="help-title"><div><p className="eyebrow">Before you pop it in your bag</p><h2 id="help-title">Good to know.</h2><p>A few answers for a smoother shop.</p></div><div className="faq-list"><details><summary>Where do you deliver?</summary><p>We deliver to supported areas in Lagos. Choose your area at checkout to see the delivery fee before placing your order. For other locations, <a href={chat}>contact us first</a>.</p></details><details><summary>How do I choose the right size?</summary><p>Available sizes and colours are listed on each product. Sizes can vary between styles, so <a href={chat}>ask us for measurements</a> if you’re unsure.</p></details><details><summary>Do I need an account to shop?</summary><p>No. Add your favourites to your bag and check out as a guest. Keep the private order link you receive at checkout to check your order’s progress.</p></details><details><summary>Can I ask about an exchange?</summary><p>Please <a href={chat}>contact the store</a> to confirm exchange options for your item before ordering, or for help with an order you’ve received.</p></details></div></section>
    </main>
    <StoreFooter settings={settings} />
  </>;
}
