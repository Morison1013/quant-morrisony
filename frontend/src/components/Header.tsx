"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/emotion", label: "情绪监控" },
  { href: "/stock-query", label: "股票查询" },
  { href: "/scanner", label: "全市场扫描" },
  { href: "/dashboard", label: "数据看板" },
];

export default function Header() {
  const pathname = usePathname();

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/" className="text-lg font-black bg-gradient-to-r from-blue-400 to-emerald-400 bg-clip-text text-transparent">
            Quant_Morrisony
          </Link>
          <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-400">
            v0.2.0
          </span>
          <nav className="flex items-center gap-1 ml-4">
            {NAV_ITEMS.map((item) => {
              const isActive = item.href === "/"
                ? pathname === "/"
                : pathname?.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`px-3 py-1.5 text-sm rounded-lg transition-colors font-medium ${
                    isActive
                      ? "bg-blue-600/20 text-blue-400"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </header>
  );
}
