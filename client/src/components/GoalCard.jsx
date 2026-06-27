import { Link } from "react-router-dom";

function GoalCard({ goal }) {
  const progress =
    goal.target_amount > 0
      ? Math.min((goal.saved_amount / goal.target_amount) * 100, 100)
      : 0;

  return (
    <article className="goal-card">
      <div className="goal-card-header">
        <div>
          <h3>{goal.item_name}</h3>
          <p>{goal.status}</p>
        </div>

        <Link to={`/goals/${goal.id}`}>View</Link>
      </div>

      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${progress}%` }}
        ></div>
      </div>

      <div className="goal-card-details">
        <span>
          ${goal.saved_amount.toFixed(2)} saved
        </span>
        <span>
          ${goal.target_amount.toFixed(2)} goal
        </span>
      </div>

      <p className="goal-monthly">
        Monthly target: ${goal.monthly_target.toFixed(2)}
      </p>
    </article>
  );
}

export default GoalCard;