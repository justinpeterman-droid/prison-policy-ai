import { useCallback, useEffect, useMemo, useState } from "react";
import { WebApiError } from "../../api/client";
import type { SessionProfile } from "../auth/api";
import {
  createCountSheet,
  fetchCountDefinition,
  lookupCountSheet,
  saveCountSheet,
} from "./api";
import { CountSheetGrid } from "./CountSheetGrid";
import type { CountSaveState } from "./CountSheetGrid";
import type { CountSheetDefinition, CountValues } from "./counts";

interface CountSheetPageProps {
  profile: SessionProfile;
  today?: string;
}

function localIsoDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function CountSheetPage({ profile, today = localIsoDate() }: CountSheetPageProps) {
  const shift = profile.shift?.trim() ?? "";
  const [definition, setDefinition] = useState<CountSheetDefinition | null>(null);
  const [definitionSha256, setDefinitionSha256] = useState("");
  const [recordId, setRecordId] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const [values, setValues] = useState<CountValues>({});
  const [expectedOperationalTotal, setExpectedOperationalTotal] = useState(0);
  const [saveState, setSaveState] = useState<CountSaveState>("saved");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [conflict, setConflict] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setLoadError(null);
    setSaveError(null);
    setConflict(false);
    if (!shift) {
      setLoading(false);
      setLoadError("A shift must be assigned to your account before a Count Sheet can be opened.");
      return () => {
        active = false;
      };
    }
    void fetchCountDefinition()
      .then(async (loaded) => {
        const record = await lookupCountSheet(
          today,
          shift,
          loaded.definition,
          loaded.sha256,
        );
        if (!active) return;
        setDefinition(loaded.definition);
        setDefinitionSha256(loaded.sha256);
        setRecordId(record?.recordId ?? null);
        setRevision(record?.revision ?? 0);
        setValues(record?.values ?? {});
        setExpectedOperationalTotal(record?.expectedOperationalTotal ?? 0);
        setSaveState("saved");
        setDirty(false);
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setDefinition(null);
        setLoadError(
          reason instanceof Error
            ? reason.message
            : "The Count Sheet could not be loaded.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [reloadToken, shift, today]);

  const persist = useCallback(async (reason: "autosave" | "manual_save") => {
    if (!definition || !definitionSha256 || !shift || saveState === "saving") return;
    setSaveState("saving");
    setSaveError(null);
    setConflict(false);
    try {
      const saved = recordId
        ? await saveCountSheet({
            recordId,
            revision,
            values,
            expectedOperationalTotal,
            reason,
            definition,
            definitionSha256,
          })
        : await createCountSheet({
            recordDate: today,
            shift,
            values,
            expectedOperationalTotal,
            definition,
            definitionSha256,
          });
      setRecordId(saved.recordId);
      setRevision(saved.revision);
      setValues(saved.values);
      setExpectedOperationalTotal(saved.expectedOperationalTotal);
      setDirty(false);
      setSaveState("saved");
    } catch (reasonValue: unknown) {
      const isConflict = reasonValue instanceof WebApiError
        && reasonValue.code === "revision_conflict";
      setConflict(isConflict);
      setSaveError(
        isConflict
          ? "This Count Sheet changed on the server. Your entries are still here; reload before saving again."
          : reasonValue instanceof Error
            ? reasonValue.message
            : "The Count Sheet could not be saved. Your entries are still here.",
      );
      setSaveState("failed");
      setDirty(true);
    }
  }, [
    definition,
    definitionSha256,
    expectedOperationalTotal,
    recordId,
    revision,
    saveState,
    shift,
    today,
    values,
  ]);

  useEffect(() => {
    if (!dirty || !definition || saveState === "saving" || conflict) return;
    const timer = window.setTimeout(() => {
      void persist("autosave");
    }, 60_000);
    return () => window.clearTimeout(timer);
  }, [conflict, definition, dirty, persist, saveState]);

  const pageTitle = useMemo(
    () => `${today} · ${shift || "Shift not assigned"}`,
    [shift, today],
  );

  if (loading) {
    return <main className="count-sheet" aria-busy="true">Loading Count Sheet…</main>;
  }
  if (loadError || !definition) {
    return (
      <main className="count-sheet">
        <div className="forms-library-state error" role="alert">
          <h1>Count Sheet unavailable</h1>
          <p>{loadError ?? "The approved Count Sheet definition is unavailable."}</p>
          <button type="button" onClick={() => setReloadToken((value) => value + 1)}>Try again</button>
        </div>
      </main>
    );
  }

  return (
    <main>
      <div className="count-sheet-context" aria-label="Count Sheet date and shift">
        <strong>{pageTitle}</strong>
        <span>{recordId ? `Revision ${revision}` : "New Count Sheet"}</span>
      </div>
      {saveError ? (
        <div className="count-sheet-save-error" role="alert">
          <strong>{conflict ? "Revision conflict" : "Save problem"}</strong>
          <span>{saveError}</span>
          {conflict ? (
            <button type="button" onClick={() => setReloadToken((value) => value + 1)}>
              Reload saved version
            </button>
          ) : null}
        </div>
      ) : null}
      <CountSheetGrid
        definition={definition}
        values={values}
        expectedOperationalTotal={expectedOperationalTotal}
        onValuesChange={(next) => {
          setValues(next);
          setDirty(true);
          setSaveError(null);
          setConflict(false);
          setSaveState("unsaved");
        }}
        onExpectedOperationalTotalChange={(next) => {
          setExpectedOperationalTotal(next);
          setDirty(true);
          setSaveError(null);
          setConflict(false);
          setSaveState("unsaved");
        }}
        onSave={() => void persist("manual_save")}
        onPrint={() => window.print()}
        saveState={saveState}
        reconciliationAlert={!conflict}
      />
    </main>
  );
}
