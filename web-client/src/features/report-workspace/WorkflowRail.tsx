import { Check, ShieldCheck } from "lucide-react";
import { reportSteps, type ReportStepId } from "./useReportWorkspace";

export function WorkflowRail({
  step,
  currentStepIndex,
  onStep,
}: {
  step: ReportStepId;
  currentStepIndex: number;
  onStep(step: ReportStepId): void;
}) {
  return (
    <aside className="workflow-rail" aria-label="Report workflow steps">
      <p className="workflow-rail__label">Report workflow</p>
      <ol>
        {reportSteps.map((item, index) => (
          <li key={item.id} className={item.id === step ? "active" : index < currentStepIndex ? "complete" : ""}>
            <button onClick={() => onStep(item.id)}>
              <span className="workflow-step-number">
                {index < currentStepIndex ? <Check aria-hidden="true" /> : index + 1}
              </span>
              <span><strong>{item.label}</strong><small>{item.description}</small></span>
            </button>
          </li>
        ))}
      </ol>
      <div className="workflow-trust">
        <ShieldCheck aria-hidden="true" />
        <span><strong>You remain in control.</strong> Nothing is filed or finalized automatically.</span>
      </div>
    </aside>
  );
}
