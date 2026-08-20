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

interface FieldControlProps {
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
  className?: string;
  id?: string;
}

export interface FieldProps {
  children: ReactElement<FieldControlProps>;
  className?: string;
  error?: ReactNode;
  hint?: ReactNode;
  label: ReactNode;
  required?: boolean;
}

export function Field({ children, className, error, hint, label, required = false }: FieldProps) {
  const generatedId = useId();
  const controlId = children.props.id ?? `${generatedId}-control`;
  const hintId = hint ? `${generatedId}-hint` : undefined;
  const errorId = error ? `${generatedId}-error` : undefined;
  const describedBy = [children.props["aria-describedby"], hintId, errorId].filter(Boolean).join(" ") || undefined;

  if (!isValidElement(children)) throw new Error("Field requires one form control child.");

  return (
    <label className={classes("gow-field", Boolean(error) && "gow-field--invalid", className)} htmlFor={controlId}>
      <span className="gow-field__label">
        {label}
        {required ? <span className="gow-visually-hidden"> (required)</span> : null}
      </span>
      {cloneElement(children, {
        id: controlId,
        className: classes("gow-control", children.props.className),
        "aria-describedby": describedBy,
        "aria-invalid": Boolean(error) || undefined,
      })}
      {hint ? <span className="gow-field__hint" id={hintId}>{hint}</span> : null}
      {error ? <span className="gow-field__error" id={errorId}>{error}</span> : null}
    </label>
  );
}
