import { Link } from "react-router-dom";

function formatCurrency(amount) {
  return Number(amount || 0).toFixed(2);
}

function formatDate(dateValue) {
  if (!dateValue) {
    return "Not set";
  }

  return new Date(dateValue).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function calculateProgress(goal) {
  // Prefer the server's capped business calculation, with a fallback for older or
  // partially cached payloads that only contain raw amounts.
  if (goal.progress_percentage !== undefined) {
    return Number(goal.progress_percentage);
  }

  if (goal.target_amount > 0) {
    return Math.min((goal.saved_amount / goal.target_amount) * 100, 100);
  }

  return 0;
}

function GoalCard({ goal }) {
  const progress = calculateProgress(goal);
  const remainingAmount =
    // remaining_amount is derived by the API; retain a local fallback so the card
    // can render goal objects supplied by older endpoints.
    goal.remaining_amount !== undefined
      ? goal.remaining_amount
      : Math.max(goal.target_amount - goal.saved_amount, 0);

  return (
    <Link className="goal-card" to={`/goals/${goal.id}`}>
      <div className="goal-card-header">
        <div>
          <h3>{goal.item_name}</h3>
          <p>{goal.retailer || "No retailer selected"}</p>
        </div>

        <span className={`status-pill ${goal.status}`}>{goal.status}</span>
      </div>

      <div className="goal-card-progress-row">
        <span>{progress.toFixed(1)}% funded</span>
        <strong>${formatCurrency(goal.saved_amount)}</strong>
      </div>

      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${progress}%` }}
        ></div>
      </div>

      <div className="goal-card-stats">
        <div>
          <span>Target</span>
          <strong>${formatCurrency(goal.target_amount)}</strong>
        </div>

        <div>
          <span>Remaining</span>
          <strong>${formatCurrency(remainingAmount)}</strong>
        </div>

        <div>
          <span>Monthly</span>
          <strong>${formatCurrency(goal.monthly_target)}</strong>
        </div>

        <div>
          <span>Target Date</span>
          <strong>{formatDate(goal.target_date)}</strong>
        </div>

        <div>
          <span>Months Left</span>
          <strong>{goal.months_remaining ?? goal.months_to_goal}</strong>
        </div>
      </div>
    </Link>
  );
}

export default GoalCard;
