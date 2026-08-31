export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="container">
        <p>© {new Date().getFullYear()} Cuemath · Tutor Screening</p>
        <p style={{ marginTop: 6, fontSize: "0.85em" }}>
          Your responses are used solely to assess your tutoring suitability.
        </p>
      </div>
    </footer>
  );
}
