import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import PriceComparisonCard from "../components/PriceComparisonCard";

import {
  createContribution,
  deleteContribution,
  getGoal,
} from "../services/api";

function formatCurrency(amount) {
  return Number(amount || 0).toFixed(2);
}

function formatDate(dateValue) {
  if (!dateValue) {
    return "Not set";
  }

  return new Date(dateValue).toLocaleDateString();
}

function formatShortDate(dateValue) {
  if (!dateValue) {
    return "";
  }

  return new Date(dateValue).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function calculateProgress(goal) {
  if (goal.progress_percentage !== undefined) {
    return Number(goal.progress_percentage);
  }

  if (goal.target_amount > 0) {
    return Math.min((goal.saved_amount / goal.target_amount) * 100, 100);
  }

  return 0;
}

function calculateTimelineProgress(goal) {
  if (!goal.created_at || !goal.target_date) {
    return 0;
  }

  const createdDate = new Date(goal.created_at);
  const targetDate = new Date(goal.target_date);
  const today = new Date();

  const totalTimeline = targetDate - createdDate;
  const elapsedTimeline = today - createdDate;

  if (totalTimeline <= 0) {
    return 100;
  }

  const progress = (elapsedTimeline / totalTimeline) * 100;

  return Math.min(Math.max(progress, 0), 100);
}

function buildProgressChartData(goal) {
  const width = 520;
  const height = 260;

  const padding = {
    top: 20,
    right: 20,
    bottom: 40,
    left: 44,
  };

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const createdDate = new Date(goal.created_at);
  const targetDate = new Date(goal.target_date);
  const today = new Date();

  const safeTargetDate =
    targetDate > createdDate
      ? targetDate
      : new Date(createdDate.getTime() + 24 * 60 * 60 * 1000);

  const totalDuration = safeTargetDate - createdDate || 1;

  const sortedContributions = [...(goal.contributions || [])].sort(
    (a, b) =>
      new Date(a.contribution_date).getTime() -
      new Date(b.contribution_date).getTime()
  );

  let runningSaved = 0;

  const rawPoints = [
    {
      date: createdDate,
      percent: 0,
    },
  ];

  sortedContributions.forEach((contribution) => {
    const entryType = contribution.entry_type || "deposit";
    const amount = Number(contribution.amount || 0);

    if (entryType === "withdrawal") {
      runningSaved -= amount;
    } else {
      runningSaved += amount;
    }

    runningSaved = Math.max(runningSaved, 0);

    const percent =
      goal.target_amount > 0
        ? clamp((runningSaved / goal.target_amount) * 100, 0, 100)
        : 0;

    rawPoints.push({
      date: new Date(contribution.contribution_date),
      percent,
    });
  });

  const currentDate = today < safeTargetDate ? today : safeTargetDate;

  rawPoints.push({
    date: currentDate,
    percent: calculateProgress(goal),
    isCurrent: true,
  });

  const points = rawPoints.map((point) => {
    const dateProgress = clamp(
      (point.date - createdDate) / totalDuration,
      0,
      1
    );

    const x = padding.left + dateProgress * chartWidth;
    const y =
      padding.top + (1 - clamp(point.percent / 100, 0, 1)) * chartHeight;

    return {
      ...point,
      x,
      y,
    };
  });

  const pathD = points
    .map((point, index) =>
      `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`
    )
    .join(" ");

  const gridLines = [0, 25, 50, 75, 100].map((value) => {
    const y = padding.top + (1 - value / 100) * chartHeight;

    return { value, y };
  });

  const todayProgress = clamp(
    (currentDate - createdDate) / totalDuration,
    0,
    1
  );

  const todayX = padding.left + todayProgress * chartWidth;

  return {
    width,
    height,
    padding,
    points,
    pathD,
    gridLines,
    todayX,
    startLabel: formatShortDate(createdDate),
    targetLabel: formatShortDate(safeTargetDate),
  };
}

function GoalDetailPage() {
  const { goalId } = useParams();

  const [goal, setGoal] = useState(null);
  const [formData, setFormData] = useState({
    amount: "",
    entry_type: "deposit",
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
      setError("Amount must be greater than zero.");
      return;
    }

    if (formData.entry_type === "withdrawal" && amount > goal.saved_amount) {
      setError("You cannot subtract more than the amount currently saved.");
      return;
    }

    setIsSubmitting(true);

    try {
      const data = await createContribution(goalId, {
        amount,
        entry_type: formData.entry_type,
        note: formData.note.trim(),
      });

      setGoal(data.goal);
      setFormData({
        amount: "",
        entry_type: "deposit",
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

  function handleAdvisorAlternativeRequest(alternativeType) {
  if (!goal) return;

  const isPremium = alternativeType === "premium";

  const advisorMode = isPremium
    ? "premium_alternatives"
    : "budget_alternatives";

  const message = isPremium
    ? `Find premium alternatives for my goal "${goal.item_name}". Strictly return product alternative ideas only. Focus on upgraded models, premium versions, better long-term value, stronger warranties, better bundles, and higher-quality competing products.`
    : `Find budget alternatives for my goal "${goal.item_name}". Strictly return product alternative ideas only. Focus on cheaper alternatives, previous-generation models, refurbished or open-box options, cheaper bundles, and similar lower-cost products.`;

  window.dispatchEvent(
    new CustomEvent("buildnbuy:advisor-request", {
      detail: {
        context_type: "goal",
        goal_id: Number(goalId),
        advisor_mode: advisorMode,
        message,
        autoSubmit: true,
      },
    })
  );
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

  const contributions = goal.contributions || [];
  const progress = calculateProgress(goal);
  const timelineProgress = calculateTimelineProgress(goal);
  const progressChart = buildProgressChartData(goal);

  const remainingAmount =
    goal.remaining_amount !== undefined
      ? goal.remaining_amount
      : Math.max(goal.target_amount - goal.saved_amount, 0);

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
            Track savings progress, target date, retailer details, and monthly
            savings pace for this purchase plan.
          </p>
        </div>

        <Link className="primary-link-button" to={`/goals/${goal.id}/edit`}>
          Edit Goal
        </Link>

        <div className="goal-advisor-actions">
          <button
            type="button"
            onClick={() => handleAdvisorAlternativeRequest("budget")}
          >
            Find Budget Alternatives
          </button>

          <button
            type="button"
            onClick={() => handleAdvisorAlternativeRequest("premium")}
          >
            Find Premium Alternatives
          </button>
        </div>
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
              <strong>${formatCurrency(goal.saved_amount)}</strong>
            </div>

            <div>
              <span>Target</span>
              <strong>${formatCurrency(goal.target_amount)}</strong>
            </div>

            <div>
              <span>Remaining</span>
              <strong>${formatCurrency(remainingAmount)}</strong>
            </div>

            <div>
              <span>Monthly Target</span>
              <strong>${formatCurrency(goal.monthly_target)}</strong>
            </div>

            <div>
              <span>Retailer</span>
              <strong>{goal.retailer || "Not selected"}</strong>
            </div>

            <div>
              <span>Months Remaining</span>
              <strong>{goal.months_remaining ?? goal.months_to_goal}</strong>
            </div>
          </div>
        </article>

        <article className="contribution-card">
          <h2>Savings Activity</h2>
          <p>Add money to this goal or subtract from savings when plans change.</p>

          <form className="goal-form" onSubmit={handleSubmit}>
            <label htmlFor="entry_type">Activity Type</label>
            <select
              id="entry_type"
              name="entry_type"
              value={formData.entry_type}
              onChange={handleChange}
            >
              <option value="deposit">Add to savings</option>
              <option value="withdrawal">Subtract from savings</option>
            </select>

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
              placeholder={
                formData.entry_type === "withdrawal"
                  ? "Example: Needed to pull from savings"
                  : "Example: Extra savings deposit"
              }
              value={formData.note}
              onChange={handleChange}
            />

            <button type="submit" disabled={isSubmitting}>
              {isSubmitting
                ? "Saving..."
                : formData.entry_type === "withdrawal"
                ? "Subtract from Savings"
                : "Add to Savings"}
            </button>
          </form>
        </article>
      </section>

      <section className="goal-insight-grid">
        <article className="goal-timeline-card">
          <div className="section-header">
            <h2>Monthly Timeline</h2>
            <p>
              {goal.months_remaining ?? goal.months_to_goal} month target pace
            </p>
          </div>

          <div className="timeline-track">
            <div
              className="timeline-fill"
              style={{ width: `${timelineProgress}%` }}
            ></div>
          </div>

          <div className="timeline-labels">
            <span>Created {formatDate(goal.created_at)}</span>
            <span>Target {formatDate(goal.target_date)}</span>
          </div>

          <div className="timeline-summary">
            <div>
              <span>Monthly savings needed</span>
              <strong>${formatCurrency(goal.monthly_target)}</strong>
            </div>

            <div>
              <span>Amount left to save</span>
              <strong>${formatCurrency(remainingAmount)}</strong>
            </div>
          </div>
        </article>

        <article className="goal-timeline-card">
          <div className="section-header">
            <h2>Progress Graph</h2>
            <p>{progress.toFixed(1)}% funded</p>
          </div>

          <div className="line-chart-wrap">
            <svg
              viewBox={`0 0 ${progressChart.width} ${progressChart.height}`}
              className="progress-line-chart"
              role="img"
              aria-label="Goal funding progress over time"
            >
              {progressChart.gridLines.map((line) => (
                <g key={line.value}>
                  <line
                    x1={progressChart.padding.left}
                    y1={line.y}
                    x2={progressChart.width - progressChart.padding.right}
                    y2={line.y}
                    className="chart-grid-line"
                  />

                  <text x={8} y={line.y + 4} className="chart-grid-label">
                    {line.value}%
                  </text>
                </g>
              ))}

              <line
                x1={progressChart.padding.left}
                y1={progressChart.height - progressChart.padding.bottom}
                x2={progressChart.width - progressChart.padding.right}
                y2={progressChart.height - progressChart.padding.bottom}
                className="chart-axis-line"
              />

              <line
                x1={progressChart.padding.left}
                y1={progressChart.padding.top}
                x2={progressChart.padding.left}
                y2={progressChart.height - progressChart.padding.bottom}
                className="chart-axis-line"
              />

              <line
                x1={progressChart.todayX}
                y1={progressChart.padding.top}
                x2={progressChart.todayX}
                y2={progressChart.height - progressChart.padding.bottom}
                className="chart-today-line"
              />

              <path d={progressChart.pathD} className="progress-line-path" />

              {progressChart.points.map((point, index) => (
                <circle
                  key={`${point.date.toISOString()}-${index}`}
                  cx={point.x}
                  cy={point.y}
                  r={index === progressChart.points.length - 1 ? 5 : 4}
                  className={
                    index === progressChart.points.length - 1
                      ? "progress-line-dot current"
                      : "progress-line-dot"
                  }
                />
              ))}

              <text
                x={progressChart.padding.left}
                y={progressChart.height - 8}
                className="chart-axis-label"
              >
                {progressChart.startLabel}
              </text>

              <text
                x={progressChart.todayX}
                y={progressChart.height - 8}
                textAnchor="middle"
                className="chart-axis-label"
              >
                Today
              </text>

              <text
                x={progressChart.width - progressChart.padding.right}
                y={progressChart.height - 8}
                textAnchor="end"
                className="chart-axis-label"
              >
                {progressChart.targetLabel}
              </text>
            </svg>
          </div>
        </article>
      </section>

       {goal && <PriceComparisonCard goalId={goal.id} />}

      <section className="dashboard-section">
        <div className="section-header">
          <h2>Savings Activity History</h2>
          <p>
            {contributions.length} activit
            {contributions.length === 1 ? "y" : "ies"}
          </p>
        </div>

        {contributions.length > 0 ? (
          <div className="contribution-list">
            {contributions.map((contribution) => {
              const entryType = contribution.entry_type || "deposit";
              const isWithdrawal = entryType === "withdrawal";

              return (
                <article
                  className={`contribution-item ${
                    isWithdrawal ? "withdrawal-item" : "deposit-item"
                  }`}
                  key={contribution.id}
                >
                  <div>
                    <strong>
                      {isWithdrawal ? "-" : "+"}$
                      {formatCurrency(contribution.amount)}
                    </strong>
                    <p>{contribution.note || "No note added"}</p>
                    <span>
                      {entryType === "withdrawal" ? "Withdrawal" : "Deposit"} ·{" "}
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
              );
            })}
          </div>
        ) : (
          <div className="empty-state">
            <h3>No savings activity yet</h3>
            <p>Add your first savings activity to start building momentum.</p>
          </div>
        )}
      </section>
    </main>
  );
}

export default GoalDetailPage;