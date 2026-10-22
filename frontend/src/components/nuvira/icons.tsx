import type { ReactNode, SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };
const icon = (children: ReactNode) => function Icon({ size = 20, ...props }: IconProps) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{children}</svg>;
};

export const Home = icon(<><path d="m3 11 9-8 9 8"/><path d="M5 10v10h14V10M9 20v-6h6v6"/></>);
export const BookOpen = icon(<><path d="M3 5.5A4.5 4.5 0 0 1 7.5 4H11v16H7.5A4.5 4.5 0 0 0 3 21Z"/><path d="M21 5.5A4.5 4.5 0 0 0 16.5 4H13v16h3.5A4.5 4.5 0 0 1 21 21Z"/></>);
export const Upload = icon(<><path d="M12 16V3m0 0L7 8m5-5 5 5"/><path d="M4 15v5h16v-5"/></>);
export const Settings = icon(<><circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1A7 7 0 0 0 15 6.2L14.7 3h-4L10 6.2a7 7 0 0 0-1.6.9L6 6.1 4 9.5 6.1 11a7 7 0 0 0 0 2L4 14.5l2 3.4 2.4-1a7 7 0 0 0 1.6.9l.7 3.2h4l.3-3.2a7 7 0 0 0 1.6-.9l2.4 1 2-3.4-2.1-1.5a7 7 0 0 0 .1-1Z"/></>);
export const MessageCircle = icon(<path d="M21 12a8 8 0 0 1-9 8 9 9 0 0 1-4-1l-5 2 2-5a9 9 0 1 1 16-4Z"/>);
export const CheckCircle2 = icon(<><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></>);
export const ChevronRight = icon(<path d="m9 18 6-6-6-6"/>);
export const ChevronLeft = icon(<path d="m15 18-6-6 6-6"/>);
export const CircleAlert = icon(<><circle cx="12" cy="12" r="9"/><path d="M12 7v6m0 4h.01"/></>);
export const LoaderCircle = icon(<><path d="M21 12a9 9 0 1 1-6.2-8.6"/><path d="M21 3v6h-6"/></>);
export const LogOut = icon(<><path d="M10 5H5v14h5"/><path d="M14 8l4 4-4 4m4-4H9"/></>);
export const Moon = icon(<path d="M20 15a8 8 0 1 1-11-11 7 7 0 0 0 11 11Z"/>);
export const Sun = icon(<><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M2 12h2m16 0h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></>);
export const Send = icon(<><path d="m3 3 18 9-18 9 4-9Z"/><path d="M7 12h14"/></>);
export const Sparkles = icon(<><path d="m12 3 1.4 4.6L18 9l-4.6 1.4L12 15l-1.4-4.6L6 9l4.6-1.4Z"/><path d="m19 15 .7 2.3L22 18l-2.3.7L19 21l-.7-2.3L16 18l2.3-.7Z"/></>);
export const X = icon(<path d="M5 5l14 14M19 5 5 19"/>);
