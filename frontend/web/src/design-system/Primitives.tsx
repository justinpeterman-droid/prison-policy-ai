import {
  cloneElement,
  createElement,
  forwardRef,
  isValidElement,
  useId,
  type ButtonHTMLAttributes,
  type HTMLAttributes,
  type ReactElement,
  type ReactNode,
} from "react";

type ButtonVariant = "primary" | "secondary" | "destructive" | "quiet" | "icon" | "segment";
type SurfaceVariant = "action" | "information" | "list" | "inset" | "empty" | "warning" | "dialog";
type ListRowVariant = "navigation" | "action";
type MessageTone = "information" | "success" | "warning" | "destructive" | "dependency-unavailable";

function classes(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}

export function buttonClassName(variant: ButtonVariant, className?: string): string {
  return classes("gow-button", `gow-button--${variant}`, className);
}

interface ButtonBaseProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  selected?: boolean;
}

export type ButtonProps = ButtonBaseProps & (
  | { "aria-label": string; variant: "icon" }
  | { variant?: Exclude<ButtonVariant, "icon"> }
);

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { children, className, disabled, loading = false, selected, type = "button", variant = "secondary", ...props },
  ref,
) {
  return (
    <button
      {...props}
      ref={ref}
      type={type}
      className={buttonClassName(variant, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      aria-pressed={selected ?? props["aria-pressed"]}
      data-selected={selected || undefined}
    >
      {children}
    </button>
  );
});

export interface SurfaceProps extends HTMLAttributes<HTMLElement> {
  as?: "article" | "div" | "section";
  variant?: SurfaceVariant;
}

export function Surface({ as = "section", className, variant = "information", ...props }: SurfaceProps) {
  return createElement(as, {
    ...props,
    className: classes("gow-surface", `gow-surface--${variant}`, className),
  });
}

export interface PanelHeaderProps extends HTMLAttributes<HTMLElement> {
  action?: ReactNode;
  eyebrow?: ReactNode;
  headingId?: string;
  headingLevel?: 2 | 3;
  heading: ReactNode;
}

export function PanelHeader({ action, children, className, eyebrow, heading, headingId, headingLevel = 2, ...props }: PanelHeaderProps) {
  const Heading = `h${headingLevel}` as "h2" | "h3";
  return (
    <header {...props} className={classes("gow-panel-header", className)}>
      <div>
        {eyebrow ? <p className="gow-panel-header__eyebrow">{eyebrow}</p> : null}
        <Heading id={headingId}>{heading}</Heading>
        {children ? <div className="gow-panel-header__supporting">{children}</div> : null}
      </div>
      {action ? <div className="gow-panel-header__action">{action}</div> : null}
    </header>
  );
}

export function listRowClassName(variant: ListRowVariant, className?: string): string {
  return classes("gow-list-row", `gow-list-row--${variant}`, className);
}

export interface ListRowProps extends HTMLAttributes<HTMLElement> {
  as?: "div" | "li";
  variant: ListRowVariant;
}

export function ListRow({ as = "div", className, variant, ...props }: ListRowProps) {
  return createElement(as, { ...props, className: listRowClassName(variant, className) });
}

export interface StatusMessageProps extends HTMLAttributes<HTMLElement> {
  as?: "div" | "p" | "section";
  tone?: MessageTone;
}

export function StatusMessage({ as = "div", className, role, tone = "information", ...props }: StatusMessageProps) {
  const assertive = tone === "destructive" || tone === "dependency-unavailable";
  return createElement(as, {
    ...props,
    className: classes("gow-message", `gow-message--${tone}`, className),
    role: role ?? (assertive ? "alert" : "status"),
    "aria-live": props["aria-live"] ?? (assertive ? "assertive" : "polite"),
  });
}

interface FieldControlProps {
  "aria-describedby"?: string;
  "aria-errormessage"?: string;
  "aria-invalid"?: boolean;
  "aria-required"?: boolean;
  className?: string;
  id?: string;
  required?: boolean;
}

export interface FieldProps {
  children: ReactElement<FieldControlProps>;
  className?: string;
  error?: ReactNode;
  hint?: ReactNode;
  label: ReactNode;
  requirement?: "required" | "optional";
  required?: boolean;
}

export function Field({ children, className, error, hint, label, requirement, required = false }: FieldProps) {
  const generatedId = useId();
  const controlId = children.props.id ?? `${generatedId}-control`;
  const hintId = hint ? `${generatedId}-hint` : undefined;
  const errorId = error ? `${generatedId}-error` : undefined;
  const describedBy = [children.props["aria-describedby"], hintId, errorId].filter(Boolean).join(" ") || undefined;
  const isRequired = required || requirement === "required" || Boolean(children.props.required);

  if (!isValidElement(children)) throw new Error("Field requires one form control child.");

  return (
    <label className={classes("gow-field", Boolean(error) && "gow-field--invalid", className)} htmlFor={controlId}>
      <span className="gow-field__label">
        {label}
        {isRequired ? <span className="gow-visually-hidden"> (required)</span> : null}
        {requirement === "optional" && !isRequired ? <span className="gow-visually-hidden"> (optional)</span> : null}
      </span>
      {cloneElement(children, {
        id: controlId,
        className: classes("gow-control", children.props.className),
        "aria-describedby": describedBy,
        "aria-errormessage": errorId ?? children.props["aria-errormessage"],
        "aria-invalid": Boolean(error) || children.props["aria-invalid"] || undefined,
        "aria-required": isRequired || undefined,
        required: isRequired || undefined,
      })}
      {hint ? <span className="gow-field__hint" id={hintId}>{hint}</span> : null}
      {error ? <span className="gow-field__error" id={errorId}>{error}</span> : null}
    </label>
  );
}
