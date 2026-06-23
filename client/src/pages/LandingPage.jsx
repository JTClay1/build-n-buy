import { Link } from "react-router-dom";

function LandingPage() {
  return (
    <main className="page">
      <h1>Build n&apos; Buy</h1>
      <p>
        Plan smarter purchases, track savings goals, and use AI to make better
        buying decisions.
      </p>

      <div className="button-row">
        <Link to="/signup">Get Started</Link>
        <Link to="/login">Log In</Link>
      </div>
    </main>
  );
}

export default LandingPage;