import type { ReactNode } from "react";

interface PrintPacketProps { children: ReactNode; }

export function PrintPacket({ children }: PrintPacketProps) {
  return <section className="print-packet" aria-label="Monthly paperwork packet">{children}</section>;
}
