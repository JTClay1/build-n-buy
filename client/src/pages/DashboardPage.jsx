import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getDashboard } from "../services/api";
import SummaryCard from "../components/SummaryCard";
import GoalCard from "../components/GoalCard";

function DashboardPage() {
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadDashboard() {
      try {
        const data = await getDashboard();
        setDashboardData(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }

    loadDashboard();
  }, []);

  if (isLoading) {
    return (
      <main className="page">
        <p>Loading dashboard...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="page">
        <p className="error-message">{error}</p>
      </main>
    );
  }

  const { summary, goals } = dashboardData;

  return (
    <main className="page dashboard-page">
      <section className="page-intro-text">
         <p className="eyebrow">Your savings command center</p>
         <h1>Dashboard</h1>
         <p>
          Track your purchase goals, monthly savings targets, and progress toward
          smarter buys.
         </p>
      </section>

      <section className="summary-grid">
        <SummaryCard label="Total Goals" value={summary.total_goals} />
        <SummaryCard label="Active Goals" value={summary.active_goals} />
        <SummaryCard label="Completed" value={summary.completed_goals} />

        <SummaryCard
          label="Total Saved"
          value={`$${summary.total_saved_amount.toFixed(2)}`}
        />

        <SummaryCard
          label="Overall Progress"
          value={`${summary.overall_progress}%`}
        />

        <SummaryCard
          label="Monthly Target"
          value={`$${summary.total_monthly_target.toFixed(2)}`}
        />
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <h2>Your Goals</h2>
          <p>
            {goals.length} saved purchase goal
            {goals.length === 1 ? "" : "s"}
          </p>
        </div>

        {goals.length > 0 ? (
          <div className="goal-grid">
            {goals.map((goal) => (
              <GoalCard key={goal.id} goal={goal} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <h3>No goals yet</h3>
            <p>Create your first purchase goal to start building toward it.</p>

            <Link className="primary-link-button" to="/goals/new">
              Create Goal
            </Link>
          </div>
        )}
      </section>
    </main>
  );
}

export default DashboardPage;