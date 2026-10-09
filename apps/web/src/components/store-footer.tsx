import Link from "next/link";
import { whatsappLink, type PublicStoreSettings } from "@/lib/store-settings";

export function StoreFooter({ settings }: { settings: PublicStoreSettings }) {
  return <footer className="store-footer" id="visit">
    <div className="store-container footer-grid">
      <div><p className="footer-wordmark">Little things.<br />Lots of love.</p><p>Clothing, shoes & accessories for their everyday adventures.</p></div>
      <div><h2>Come say hello</h2><p>{settings.address}<br />{settings.city}</p><a href={whatsappLink(settings.whatsapp_number, "Hi! I'd like to ask about Atiten Kids Store.")}>Chat on WhatsApp ↗</a></div>
      <div><h2>Make yourself at home</h2><Link href="/#shop">Shop the collection</Link><Link href="/cart">Your shopping bag</Link><Link href="/#help">Shopping & delivery help</Link>{settings.instagram_url && <a href={settings.instagram_url}>Instagram ↗</a>}{settings.tiktok_url && <a href={settings.tiktok_url}>TikTok ↗</a>}</div>
    </div>
    <div className="store-container footer-bottom"><span>© {new Date().getFullYear()} {settings.store_name}</span><span>Made for little everyday moments.</span><Link href="/admin">Store team</Link></div>
  </footer>;
}
