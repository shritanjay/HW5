// Line-art SVG images for the dashboard (no image files; they inherit text color).
import type { AgentName } from "./api";

type P = { size?: number; className?: string };
const svg = (size: number, className: string | undefined, children: React.ReactNode, vb = "0 0 24 24") => (
  <svg width={size} height={size} viewBox={vb} fill="none" stroke="currentColor" strokeWidth={1.6}
       strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
    {children}
  </svg>
);

/* ---------- agents ---------- */
export const BossIcon = ({ size = 20, className }: P) => svg(size, className, <>
  <path d="M3 8l4.5 3.5L12 5l4.5 6.5L21 8l-2 10H5L3 8z" />
  <path d="M5 21h14" />
</>);
export const InventoryIcon = ({ size = 20, className }: P) => svg(size, className, <>
  <path d="M21 8l-9-5-9 5 9 5 9-5z" />
  <path d="M3 8v8l9 5 9-5V8" />
  <path d="M12 13v8" />
  <path d="M7.5 5.5l9 5" />
</>);
export const AccountingIcon = ({ size = 20, className }: P) => svg(size, className, <>
  <rect x="5" y="2.5" width="14" height="19" rx="2" />
  <rect x="8" y="5.5" width="8" height="3.5" rx="0.6" />
  <path d="M8.5 13h.01M12 13h.01M15.5 13h.01M8.5 16.5h.01M12 16.5h.01M15.5 16.5h.01" strokeWidth={2.4} />
</>);
export const FacilitiesIcon = ({ size = 20, className }: P) => svg(size, className, <>
  <circle cx="8" cy="15" r="4.5" />
  <path d="M11.2 11.8L20 3M16.5 6.5l2.5 2.5M14 9l2 2" />
</>);
export const ServiceIcon = ({ size = 20, className }: P) => svg(size, className, <>
  <path d="M20 12.5a7.5 7.5 0 0 1-11.2 6.5L4 20l1.2-4.3A7.5 7.5 0 1 1 20 12.5z" />
  <path d="M9 11h6M9 14h4" />
</>);

export const AGENT_ICON: Record<AgentName, (p: P) => React.ReactElement> = {
  boss: BossIcon,
  inventory: InventoryIcon,
  accounting: AccountingIcon,
  facilities: FacilitiesIcon,
  customer_service: ServiceIcon,
};

/* ---------- ticket illustrations ---------- */
export const TeeArt = ({ size = 96, className }: P) => svg(size, className, <>
  <path d="M22 14l-12 6 4 12 6-2v26h24V30l6 2 4-12-12-6c-1.5 4-4.5 6-10 6s-8.5-2-10-6z" strokeWidth={1.4} />
  <path d="M27 14c1.5 3 3.5 4.5 5 4.5s3.5-1.5 5-4.5" strokeWidth={1.2} />
  <text x="32" y="44" textAnchor="middle" fontSize="7" fill="currentColor" stroke="none" fontWeight="700" letterSpacing="0.5">S</text>
</>, "0 0 64 64");

export const StorefrontArt = ({ size = 96, className }: P) => svg(size, className, <>
  <path d="M10 26h44v28H10z" strokeWidth={1.4} />
  <path d="M8 26l5-12h38l5 12" strokeWidth={1.4} />
  <path d="M8 26c0 3 2.5 5 5.5 5s5.5-2 5.5-5c0 3 2.5 5 5.5 5s5.5-2 5.5-5c0 3 2.5 5 5.5 5s5.5-2 5.5-5c0 3 2.5 5 5.5 5S56 29 56 26" strokeWidth={1.2} />
  <path d="M16 54V38h10v16M32 38h16v10H32z" strokeWidth={1.3} />
  <path d="M24 20h16" strokeWidth={1.2} />
</>, "0 0 64 64");

export const HoodieArt = ({ size = 96, className }: P) => svg(size, className, <>
  <path d="M24 12c0-4 3.5-6 8-6s8 2 8 6l12 6 4 18-6 2-2-8v28H18V30l-2 8-6-2 4-18 10-6z" strokeWidth={1.4} />
  <path d="M24 12c1 6 4 9 8 9s7-3 8-9" strokeWidth={1.2} />
  <path d="M30 21v7M34 21v7" strokeWidth={1.1} />
  <path d="M24 46h16v8H24z" strokeWidth={1.1} />
  <g transform="translate(43 40) rotate(18)">
    <path d="M0 0h12l4 5-4 5H0z" strokeWidth={1.2} fill="var(--bg)" />
    <text x="6" y="7.2" textAnchor="middle" fontSize="6" fill="currentColor" stroke="none" fontWeight="700">%</text>
  </g>
</>, "0 0 64 64");

export const TICKET_ART: Record<string, (p: P) => React.ReactElement> = {
  customer_order: TeeArt,
  rent_notice: StorefrontArt,
  price_override: HoodieArt,
};

/* ---------- misc ---------- */
export const ShopMark = ({ size = 20, className }: P) => svg(size, className, <>
  <path d="M4 10v10h16V10" />
  <path d="M3 10l2-6h14l2 6" />
  <path d="M3 10c0 1.4 1.2 2.5 3 2.5S9 11.4 9 10c0 1.4 1.2 2.5 3 2.5s3-1.1 3-2.5c0 1.4 1.2 2.5 3 2.5s3-1.1 3-2.5" />
  <path d="M10 20v-5h4v5" />
</>);
export const WalletIcon = ({ size = 18, className }: P) => svg(size, className, <>
  <path d="M19 7V5a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H5a2 2 0 0 1-2-2V6" />
  <circle cx="16.5" cy="13.5" r="1" fill="currentColor" />
</>);
export const PulseArt = ({ size = 56, className }: P) => svg(size, className, <>
  <circle cx="32" cy="32" r="24" strokeWidth={1.2} strokeDasharray="3 5" />
  <path d="M14 32h10l4-10 8 20 4-10h10" strokeWidth={1.6} />
</>, "0 0 64 64");
export const CheckSeal = ({ size = 18, className }: P) => svg(size, className, <>
  <path d="M12 2l2.4 1.8 3-.2.9 2.9 2.5 1.7-1 2.8 1 2.8-2.5 1.7-.9 2.9-3-.2L12 22l-2.4-1.8-3 .2-.9-2.9-2.5-1.7 1-2.8-1-2.8 2.5-1.7.9-2.9 3 .2z" />
  <path d="M8.5 12l2.5 2.5 4.5-5" />
</>);
