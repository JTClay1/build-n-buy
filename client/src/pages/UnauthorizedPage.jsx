import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function UnauthorizedPage() {
  const { user } = useAuth();

  return (
    <main className="page unauthorized-page">
      <section className="form-card unauthorized-card">
        <p className="eyebrow">401 Unauthorized</p>
        <h1>You&apos;re already signed in.</h1>

        <p>
          {user?.username
            ? `You are currently logged in as ${user.username}.`
            : "You are currently logged in."}{" "}
          Log out first if you want to use a different account.
        </p>

        <div className="button-row">
          <Link className="primary-link-button" to="/dashboard">
            Go to Dashboard
          </Link>

          <Link to="/">Back Home</Link>
        </div>
      </section>
    </main>
  );
}

export default UnauthorizedPage;