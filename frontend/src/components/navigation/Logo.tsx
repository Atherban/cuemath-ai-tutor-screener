import { Link } from "react-router-dom";

interface LogoProps {
  /** Link target for the logo; null renders a plain span. */
  to?: string | null;
  light?: boolean;
}

/** Cuemath-style wordmark: a rounded "C" mark + wordmark. */
export function Logo({ to = "/", light = false }: LogoProps) {
  const inner = (
    <>
      <span className="logo__mark" aria-hidden="true">
        C
      </span>
      <span style={light ? { color: "#fff" } : undefined}>Cuemath</span>
    </>
  );

  if (to === null) {
    return (
      <span className="logo" aria-label="Cuemath">
        {inner}
      </span>
    );
  }
  return (
    <Link to={to} className="logo" aria-label="Cuemath">
      {inner}
    </Link>
  );
}
