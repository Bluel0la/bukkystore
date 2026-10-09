export default function Loading() {
  return <main className="store-container py-12" aria-busy="true" aria-label="Loading store"><p role="status" className="mb-8 text-sm text-(--muted)">Finding lovely little things…</p><div className="loading-block mb-10 h-52" /><div className="product-grid" aria-hidden="true">{Array.from({ length: 4 }, (_, index) => <div key={index}><div className="loading-block aspect-[4/5]" /><div className="loading-block mt-4 h-5 w-3/4" /></div>)}</div></main>;
}
