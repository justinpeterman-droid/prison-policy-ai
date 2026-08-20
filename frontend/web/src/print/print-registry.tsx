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
  definition: { columns: readonly string[]; schedule?: readonly string[]; footerNote?: string };
}

export interface PrintComponentProps { definition: MonthlyTemplateDefinition; prefill: MonthlyPrintPrefill; }

export const MONTHLY_PRINT_TEMPLATES: readonly MonthlyTemplateDefinition[] = [
  { code: "monthly_windows_bars_doors", title: "Windows, Bars & Doors Check Log", description: "Daily security checks for exterior and housing windows, doors, and bars.", definition: { columns: ["Date", "Exterior Bks. Windows", "All Inmate Housing Windows", "Housing Doors", "All Cell Bars", "Officer's Signature"], footerNote: "All bars will be checked with a rubber mallet." } },
  { code: "monthly_chemical_agents", title: "Use of Chemical Agents Log", description: "Monthly record of chemical-agent use and supervisory review.", definition: { columns: ["Date", "Staff", "Inmate Name / #", "Conforms To Policy", "Medical Attention", "Supervisor"] } },
  { code: "monthly_contraband_standard", title: "Contraband Search Log — Standard Area Rotation", description: "Standard-area contraband search schedule.", definition: { columns: ["Date/Time", "Area Searched", "Contraband Found", "Searching Officers", "Disposition of Contraband"], schedule: ["Gym", "School", "Front Office / Barber Shop", "Boiler Room", "Kitchen and ODR", "Laundry Press Area / Main Showers"] } },
  { code: "monthly_contraband_expanded", title: "Contraband Search Log — Expanded Area Rotation", description: "Expanded-area contraband search schedule.", definition: { columns: ["Date/Time", "Area Searched", "Contraband Found", "Searching Officers", "Disposition of Contraband"], schedule: ["Gym", "Chapel", "Entrance Building", "School", "Front Office / Barbershop", "Boiler Room", "Kitchen / ODR", "Laundry", "Inmate Barbershop", "Inside Maintenance"] } },
];

export const printRegistry: Record<PrintTemplateCode, ComponentType<PrintComponentProps>> = {
  monthly_windows_bars_doors: WindowsBarsDoorsPrint,
  monthly_chemical_agents: ChemicalAgentsPrint,
  monthly_contraband_standard: ContrabandSearchPrint,
  monthly_contraband_expanded: ContrabandSearchPrint,
};
