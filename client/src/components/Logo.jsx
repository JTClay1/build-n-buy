function Logo({ size = "nav" }) {
  return (
    <div className={`brand-logo ${size === "large" ? "large" : ""}`}>
      <span className="brand-big-b">B</span>

      <span className="brand-stack">
        <span className="brand-word brand-top">uild</span>
        <span className="brand-middle">n&apos;</span>
        <span className="brand-word brand-bottom">uy</span>
      </span>
    </div>
  );
}

export default Logo;