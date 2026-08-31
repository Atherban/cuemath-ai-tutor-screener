import { type ButtonHTMLAttributes, forwardRef } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger-ghost";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const VARIANT_CLASS: Record<Variant, string> = {
  primary: "btn--primary",
  secondary: "btn--secondary",
  ghost: "btn--ghost",
  "danger-ghost": "btn--danger-ghost",
};

const SIZE_CLASS: Record<Size, string> = {
  sm: "btn--sm",
  md: "",
  lg: "btn--lg",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", size = "md", className = "", type = "button", ...rest },
  ref,
) {
  const classes = ["btn", VARIANT_CLASS[variant], SIZE_CLASS[size], className]
    .filter(Boolean)
    .join(" ");
  return <button ref={ref} type={type} className={classes} {...rest} />;
});
