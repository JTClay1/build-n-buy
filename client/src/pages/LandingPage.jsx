import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Logo from "../components/Logo";

function LandingPage() {
  const { user, isAuthenticated, authLoading } = useAuth();

  if (authLoading) {
    return (
      <main className="page">
        <p>Loading...</p>
      </main>
    );
  }

  if (isAuthenticated) {
    return (
      <main className="page home-page">
        <section className="home-hero">
          <div>
            <p className="eyebrow">Welcome back</p>

            <div className="hero-logo-wrap hero-logo-feature">
              <Logo size="large" />
            </div>

            <h1>Keep building, {user?.username}.</h1>

            <p>
              Jump back into your purchase goals, review your savings progress,
              or create a new plan for your next big buy.
            </p>
          </div>

          <Link className="primary-link-button" to="/dashboard">
            Open Dashboard
          </Link>
        </section>

        <section className="home-action-grid">
          <Link className="home-action-card" to="/dashboard">
            <h2>View Dashboard</h2>
            <p>
              See your total saved amount, active goals, monthly targets, and
              overall progress.
            </p>
          </Link>

          <Link className="home-action-card" to="/goals/new">
            <h2>Create New Goal</h2>
            <p>
              Add a new purchase goal and calculate how much you need to save
              each month.
            </p>
          </Link>

          <div className="home-action-card muted-card">
            <h2>Smart Buy Advisor</h2>
            <p>
              Coming soon: compare cheaper alternatives, premium upgrades,
              timeline changes, and ways to free up money.
            </p>
          </div>
        </section>

        <section className="home-info-card">
          <h2>How Build n&apos; Buy helps</h2>
          <p>
            Build n&apos; Buy is designed around a save-first mindset. Instead
            of rushing into a purchase, you can plan the goal, track your
            contributions, and make smarter tradeoffs before spending.
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className="page home-page">
      <section className="home-hero">
        <div>
          <p className="eyebrow">Save first. Buy smarter.</p>

          <div className="hero-logo-wrap hero-logo-feature">
            <Logo size="large" />
          </div>

          <h1 className="sr-only">Build n&apos; Buy</h1>

          <p>
            Plan smarter purchases, track savings goals, and use AI to make
            better buying decisions before you spend.
          </p>
        </div>

        <div className="button-row">
          <Link className="primary-link-button" to="/signup">
            Get Started
          </Link>
          <Link to="/login">Log In</Link>
        </div>
      </section>

      <section className="home-action-grid">
        <div className="home-action-card">
          <h2>Create goals</h2>
          <p>
            Set a target amount and timeline for the things you actually want to
            buy.
          </p>
        </div>

        <div className="home-action-card">
          <h2>Track progress</h2>
          <p>
            Add contributions over time and watch your monthly target adjust as
            you save.
          </p>
        </div>

        <div className="home-action-card">
          <h2>Buy with context</h2>
          <p>
            Soon, Smart Buy Advisor will help compare alternatives and decide
            whether the purchase fits your plan.
          </p>
        </div>
      </section>
    </main>
  );
}

export default LandingPage;