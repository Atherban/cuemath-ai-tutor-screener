import { Logo } from "./Logo";

export function SiteHeader() {
  return (
    <header className="site-header">
      <div className="container site-header__inner">
        <Logo to="/" />
        <nav className="site-header__nav" aria-label="Primary">
          <span className="site-header__chip">
            <span className="site-header__chip-dot" aria-hidden="true" />
            Tutor Careers
          </span>
        </nav>
      </div>
    </header>
  );
}
