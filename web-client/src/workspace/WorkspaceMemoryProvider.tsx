import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useAuth } from "../auth/AuthProvider";
import type { PolicyCitation, ReportSummary } from "../types";

export interface SavedCitation extends PolicyCitation {
  savedAt: string;
}

interface WorkspaceMemoryValue {
  savedCitations: SavedCitation[];
  savedReports: ReportSummary[];
  saveCitation(citation: PolicyCitation): void;
  removeCitation(source: string, n: number): void;
  toggleReport(report: ReportSummary): void;
  isReportSaved(reportId: string): boolean;
  clear(): void;
}

const WorkspaceMemoryContext = createContext<WorkspaceMemoryValue | null>(null);

export function WorkspaceMemoryProvider({ children }: PropsWithChildren) {
  const { status } = useAuth();
  const [savedCitations, setSavedCitations] = useState<SavedCitation[]>([]);
  const [savedReports, setSavedReports] = useState<ReportSummary[]>([]);

  const clear = useCallback(() => {
    setSavedCitations([]);
    setSavedReports([]);
  }, []);

  useEffect(() => {
    if (status === "signed-out") clear();
  }, [status, clear]);

  const saveCitation = useCallback((citation: PolicyCitation) => {
    setSavedCitations((current) => {
      if (current.some((item) => item.source === citation.source && item.n === citation.n)) {
        return current;
      }
      return [...current, { ...citation, savedAt: new Date().toISOString() }];
    });
  }, []);

  const removeCitation = useCallback((source: string, n: number) => {
    setSavedCitations((current) => current.filter((item) => item.source !== source || item.n !== n));
  }, []);

  const toggleReport = useCallback((report: ReportSummary) => {
    setSavedReports((current) =>
      current.some((item) => item.reportId === report.reportId)
        ? current.filter((item) => item.reportId !== report.reportId)
        : [...current, report],
    );
  }, []);

  const isReportSaved = useCallback(
    (reportId: string) => savedReports.some((item) => item.reportId === reportId),
    [savedReports],
  );

  const value = useMemo<WorkspaceMemoryValue>(
    () => ({
      savedCitations,
      savedReports,
      saveCitation,
      removeCitation,
      toggleReport,
      isReportSaved,
      clear,
    }),
    [savedCitations, savedReports, saveCitation, removeCitation, toggleReport, isReportSaved, clear],
  );

  return <WorkspaceMemoryContext.Provider value={value}>{children}</WorkspaceMemoryContext.Provider>;
}

export function useWorkspaceMemory(): WorkspaceMemoryValue {
  const value = useContext(WorkspaceMemoryContext);
  if (!value) throw new Error("useWorkspaceMemory must be used inside WorkspaceMemoryProvider");
  return value;
}
