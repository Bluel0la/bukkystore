import Image from "next/image";
import Link from "next/link";

/** Store brand mark: logo badge plus name. Usable in server and client components. */
export function StoreBrand({ name }: { name: string }) {
  return (
    <Link className="flex items-center gap-2 text-xl font-semibold tracking-[-0.03em]" href="/">
      <Image
        alt={`${name} logo`}
        className="h-9 w-9 rounded-full object-cover"
        height={36}
        priority
        src="/atiten-logo-icon.png"
        width={36}
      />
      {name}
    </Link>
  );
}
