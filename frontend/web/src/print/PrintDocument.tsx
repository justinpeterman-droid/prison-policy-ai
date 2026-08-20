import type { ReactNode } from "react";
import "./print.css";

interface PrintDocumentProps {
  title: string;
  children: ReactNode;
}

export function PrintDocument({ title, children }: PrintDocumentProps) {
  return <article className="print-document" aria-label={title}>{children}</article>;
}
