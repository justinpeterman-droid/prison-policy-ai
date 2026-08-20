import type { ComponentType } from "react";
import { ChemicalAgentsPrint } from "../features/administration/paperwork/monthly/ChemicalAgentsPrint";
import { ContrabandSearchPrint } from "../features/administration/paperwork/monthly/ContrabandSearchPrint";
import { WindowsBarsDoorsPrint } from "../features/administration/paperwork/monthly/WindowsBarsDoorsPrint";

export type PrintTemplateCode =
  | "monthly_windows_bars_doors"
  | "monthly_chemical_agents"
  | "monthly_contraband_standard"
  | "monthly_contraband_expanded";

export interface MonthlyPrintPrefill { month: string; shift: string; shiftSupervisor?: string; }
export interface MonthlyTemplateDefinition {
  code: PrintTemplateCode;
  title: string;
  description: string;
  pageSize: "letter";
  orientation: "landscape";
  definition: { columns: readonly string[]; schedule?: readonly string[]; footerNote?: string };
}

export interface PrintComponentProps { definition: MonthlyTemplateDefinition; prefill: MonthlyPrintPrefill; }

export const printRegistry: Record<PrintTemplateCode, ComponentType<PrintComponentProps>> = {
  monthly_windows_bars_doors: WindowsBarsDoorsPrint,
  monthly_chemical_agents: ChemicalAgentsPrint,
  monthly_contraband_standard: ContrabandSearchPrint,
  monthly_contraband_expanded: ContrabandSearchPrint,
};
