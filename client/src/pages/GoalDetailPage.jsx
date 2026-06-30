import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  createContribution,
  deleteContribution,
  getGoal,
} from "../services/api";

function GoalDetailPage() {
  const { goalId } = useParams();

  const [goal, setGoal] = useState(null);
  const [formData, setFormData] = useState({
    amount: "",
    note: "",
  });
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    async function loadGoal() {
      try {
        const data = await getGoal(goalId);
        setGoal(data.goal);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }

    loadGoal();
  }, [goalId]);

  function handleChange(event) {
    const { name, value } = event.target;

    setFormData((currentData) => ({
      ...currentData,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    const amount = Number(formData.amount);

    if (amount <= 0) {
      setError("Contribution amount must be greater than zero.");
      return;
    }

    setIsSubmitting(true);

    try {
      const data = await createContribution(goalId, {
        amount,
        note: formData.note.trim(),
      });

      setGoal(data.goal);
      setFormData({
        amount: "",
        note: "",
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDeleteContribution(contributionId) {
    setError("");

    try {
      const data = await deleteContribution(contributionId);
      setGoal(data.goal);
    } catch (err) {
      setError(err.message);
    }
  }

  if (isLoading) {
    return (
      <main className="page">
        <p>Loading goal...</p>
      </main>
    );
  }

  if (error && !goal) {
    return (
      <main className="page">
        <p className="error-message">{error}</p>
        <Link to="/dashboard">Back to dashboard</Link>
      </main>
    );
  }

  const progress =
    goal.target_amount > 0
      ? Math.min((goal.saved_amount / goal.target_amount) * 100, 100)
      : 0;

  const remainingAmount = Math.max(goal.target_amount - goal.saved_amount, 0);

  return (
    <main className="page goal-detail-page">
      <Link to="/dashboard" className="back-link">
        ← Back to dashboard
      </Link>

      <section className="goal-detail-hero">
        <div>
          <p className="eyebrow">Goal details</p>
          <h1>{goal.item_name}</h1>
          <p>
            Track savings progress, add contributions, and keep this purchase
            plan moving.
          </p>
        </div>

        <Link className="primary-link-button" to={`/goals/${goal.id}/edit`}>
          Edit Goal
        </Link>
      </section>

      {error && <p className="error-message">{error}</p>}

      <section className="goal-detail-grid">
        <article className="goal-progress-card">
          <div className="goal-status-row">
            <span className={`status-pill ${goal.status}`}>{goal.status}</span>
            <strong>{progress.toFixed(1)}%</strong>
          </div>

          <div className="progress-bar large">
            <div
              className="progress-fill"
              style={{ width: `${progress}%` }}
            ></div>
          </div>

          <div className="goal-money-grid">
            <div>
              <span>Saved</span>
              <strong>${goal.saved_amount.toFixed(2)}</strong>
            </div>
            <div>
              <span>Target</span>
              <strong>${goal.target_amount.toFixed(2)}</strong>
            </div>
            <div>
              <span>Remaining</span>
              <strong>${remainingAmount.toFixed(2)}</strong>
            </div>
            <div>
              <span>Monthly Target</span>
              <strong>${goal.monthly_target.toFixed(2)}</strong>
            </div>
          </div>
        </article>

        <article className="contribution-card">
          <h2>Add Contribution</h2>
          <p>Log money saved toward this goal.</p>

          <form className="goal-form" onSubmit={handleSubmit}>
            <label htmlFor="amount">Amount</label>
            <input
              id="amount"
              name="amount"
              type="number"
              min="1"
              step="0.01"
              placeholder="50"
              value={formData.amount}
              onChange={handleChange}
              required
            />

            <label htmlFor="note">Note</label>
            <input
              id="note"
              name="note"
              type="text"
              placeholder="Example: Extra savings deposit"
              value={formData.note}
              onChange={handleChange}
            />

            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Adding..." : "Add Contribution"}
            </button>
          </form>
        </article>
      </section>

      <section className="dashboard-section">
        <div className="section-header">
          <h2>Contribution History</h2>
          <p>
            {goal.contributions.length} contribution
            {goal.contributions.length === 1 ? "" : "s"}
          </p>
        </div>

        {goal.contributions.length > 0 ? (
          <div className="contribution-list">
            {goal.contributions.map((contribution) => (
              <article className="contribution-item" key={contribution.id}>
                <div>
                  <strong>${contribution.amount.toFixed(2)}</strong>
                  <p>{contribution.note || "No note added"}</p>
                  <span>
                    {new Date(
                      contribution.contribution_date
                    ).toLocaleDateString()}
                  </span>
                </div>

                <button
                  type="button"
                  onClick={() => handleDeleteContribution(contribution.id)}
                >
                  Delete
                </button>
              </article>
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <h3>No contributions yet</h3>
            <p>Add your first contribution to start building momentum.</p>
          </div>
        )}
      </section>
    </main>
  );
}

export default GoalDetailPage;