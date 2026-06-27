import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { createGoal } from "../services/api";

function NewGoalPage() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    item_name: "",
    target_amount: "",
    months_to_goal: "",
  });

  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

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

    const targetAmount = Number(formData.target_amount);
    const monthsToGoal = Number(formData.months_to_goal);

    if (!formData.item_name.trim()) {
      setError("Please enter an item name.");
      return;
    }

    if (targetAmount <= 0) {
      setError("Target amount must be greater than zero.");
      return;
    }

    if (monthsToGoal <= 0) {
      setError("Months to goal must be greater than zero.");
      return;
    }

    setIsSubmitting(true);

    try {
      const data = await createGoal({
        item_name: formData.item_name.trim(),
        target_amount: targetAmount,
        months_to_goal: monthsToGoal,
      });

      navigate(`/goals/${data.goal.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const previewMonthlyTarget =
    Number(formData.target_amount) > 0 && Number(formData.months_to_goal) > 0
      ? Number(formData.target_amount) / Number(formData.months_to_goal)
      : 0;

  return (
    <main className="page form-page">
      <section className="form-card">
        <Link to="/dashboard" className="back-link">
          ← Back to dashboard
        </Link>

        <p className="eyebrow">Build your next buy</p>
        <h1>New Goal</h1>
        <p>
          Create a purchase goal and Build n&apos; Buy will calculate how much
          you need to save each month.
        </p>

        {error && <p className="error-message">{error}</p>}

        <form className="goal-form" onSubmit={handleSubmit}>
          <label htmlFor="item_name">What are you saving for?</label>
          <input
            id="item_name"
            name="item_name"
            type="text"
            placeholder="Example: RTX 4070 Super"
            value={formData.item_name}
            onChange={handleChange}
            required
          />

          <label htmlFor="target_amount">Target Amount</label>
          <input
            id="target_amount"
            name="target_amount"
            type="number"
            min="1"
            step="0.01"
            placeholder="800"
            value={formData.target_amount}
            onChange={handleChange}
            required
          />

          <label htmlFor="months_to_goal">Months to Goal</label>
          <input
            id="months_to_goal"
            name="months_to_goal"
            type="number"
            min="1"
            step="1"
            placeholder="6"
            value={formData.months_to_goal}
            onChange={handleChange}
            required
          />

          <div className="goal-preview">
            <span>Estimated monthly target</span>
            <strong>${previewMonthlyTarget.toFixed(2)}</strong>
          </div>

          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating goal..." : "Create Goal"}
          </button>
        </form>
      </section>
    </main>
  );
}

export default NewGoalPage;