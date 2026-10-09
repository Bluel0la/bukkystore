"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { AdminLogout } from "@/components/admin-logout";
import type { AdminUser } from "@/lib/admin-types";

const navigation = [
  { href: "/admin", label: "Overview", mark: "⌂" },
  { href: "/admin/orders", label: "Orders", mark: "□" },
  { href: "/admin/products", label: "Products", mark: "◇" },
  { href: "/admin/categories", label: "Categories", mark: "⌘" },
  { href: "/admin/delivery", label: "Delivery", mark: "↗" },
  { href: "/admin/settings", label: "Store settings", mark: "⚙" },
] as const;

function isCurrent(pathname: string, href: string) {
  return href === "/admin" ? pathname === href : pathname.startsWith(href);
}

export function AdminShell({ children, storeName, user }: {
  children: ReactNode;
  storeName: string;
  user: AdminUser;
}) {
  const pathname = usePathname();

  return <div className="admin-shell">
    <aside className="admin-sidebar">
      <div className="admin-sidebar-brand">
        <Image alt="" height={38} src="/atiten-logo-icon.png" width={38} />
        <div><strong>{storeName}</strong><span>Store manager</span></div>
      </div>
      <nav aria-label="Admin navigation" className="admin-navigation">
        {navigation.map((item) => <Link
          aria-current={isCurrent(pathname, item.href) ? "page" : undefined}
          href={item.href}
          key={item.href}
        ><span aria-hidden="true">{item.mark}</span>{item.label}</Link>)}
      </nav>
      <div className="admin-sidebar-foot">
        <div className="admin-user"><span>{user.display_name.slice(0, 1).toUpperCase()}</span><div><strong>{user.display_name}</strong><small>{user.role === "OWNER" ? "Store owner" : "Administrator"}</small></div></div>
        <AdminLogout />
      </div>
    </aside>
    <div className="admin-stage">
      <header className="admin-topbar">
        <div><span className="admin-live-dot" />Store workspace</div>
        <div className="admin-topbar-actions"><Link href="/" target="_blank">View storefront ↗</Link><Link className="admin-quick-add" href="/admin/products/new">＋ Add product</Link></div>
      </header>
      <div className="admin-workspace">{children}</div>
    </div>
  </div>;
}
