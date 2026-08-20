import type { ReactNode, SVGProps } from "react";

export type InterfaceIconName =
  | "arrow-down"
  | "arrow-left"
  | "arrow-right"
  | "arrow-up"
  | "chevron-down"
  | "chevron-right"
  | "close"
  | "document"
  | "drag"
  | "external-link"
  | "grid"
  | "health"
  | "paperwork"
  | "search";

interface InterfaceIconProps extends Omit<SVGProps<SVGSVGElement>, "children"> {
  name: InterfaceIconName;
  title?: string;
}

const paths: Record<InterfaceIconName, ReactNode> = {
  "arrow-down": <><path d="M12 4v16"/><path d="m6 14 6 6 6-6"/></>,
  "arrow-left": <><path d="M20 12H4"/><path d="m10 18-6-6 6-6"/></>,
  "arrow-right": <><path d="M4 12h16"/><path d="m14 6 6 6-6 6"/></>,
  "arrow-up": <><path d="M12 20V4"/><path d="m6 10 6-6 6 6"/></>,
  "chevron-down": <path d="m6 9 6 6 6-6"/>,
  "chevron-right": <path d="m9 6 6 6-6 6"/>,
  close: <><path d="M6 6l12 12"/><path d="M18 6 6 18"/></>,
  document: <><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v5h5"/><path d="M9 12h6M9 16h6"/></>,
  drag: <><path d="m8 7 4-4 4 4"/><path d="M12 3v18"/><path d="m8 17 4 4 4-4"/></>,
  "external-link": <><path d="M14 5h5v5"/><path d="m19 5-9 9"/><path d="M18 13v6H5V6h6"/></>,
  grid: <><rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/></>,
  health: <><path d="M4 12h4l2-5 4 10 2-5h4"/><path d="M12 21C6 17.5 3 14 3 9.5A4.5 4.5 0 0 1 12 8a4.5 4.5 0 0 1 9 1.5c0 4.5-3 8-9 11.5Z"/></>,
  paperwork: <><path d="M7 3h10v4H7z"/><path d="M5 5h14v16H5z"/><path d="M8 11h8M8 15h8M8 19h5"/></>,
  search: <><circle cx="11" cy="11" r="6"/><path d="m16 16 4 4"/></>,
};

export function InterfaceIcon({ name, title, ...props }: InterfaceIconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      width="1em"
      height="1em"
      aria-hidden={title ? undefined : true}
      role={title ? "img" : undefined}
      focusable="false"
      {...props}
    >
      {title ? <title>{title}</title> : null}
      {paths[name]}
    </svg>
  );
}
