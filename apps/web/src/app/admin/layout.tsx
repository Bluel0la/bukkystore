import type { ReactNode } from "react";

import { AdminShell } from "@/components/admin-shell";
import { getAdminStoreSettings, getAdminUser } from "@/lib/admin";

export default async function AdminLayout({ children }: { children: ReactNode }) {
  const user = await getAdminUser();
  if (!user) return children;
  const settings = await getAdminStoreSettings();
  return <AdminShell storeName={settings?.store_name ?? "Atiten Kids Store"} user={user}>{children}</AdminShell>;
}
