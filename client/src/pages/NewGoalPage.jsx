import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { createGoal } from "../services/api";

function getTomorrowDateString() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);

  const year = tomorrow.getFullYear();
  const month = String(tomorrow.getMonth() + 1).padStart(2, "0");
  const day = String(tomorrow.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function calculateMonthsRemaining(targetDateValue) {
  if (!targetDateValue) {
    return 0;
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const targetDate = new Date(`${targetDateValue}T00:00:00`);
  const millisecondsRemaining = targetDate - today;
  const daysRemaining = millisecondsRemaining / (1000 * 60 * 60 * 24);

  if (daysRemaining <= 0) {
    return 0;
  }

  return Math.ceil(daysRemaining / 30);
}

function NewGoalPage() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    item_name: "",
    retailer: "",
    target_amount: "",
    target_date: "",
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
    const monthsRemaining = calculateMonthsRemaining(formData.target_date);

    if (!formData.item_name.trim()) {
      setError("Please enter an item name.");
      return;
    }

    if (targetAmount <= 0) {
      setError("Target amount must be greater than zero.");
      return;
    }

    if (!formData.target_date) {
      setError("Please choose a target date.");
      return;
    }

    if (monthsRemaining <= 0) {
      setError("Target date must be in the future.");
      return;
    }

    setIsSubmitting(true);

    try {
      const data = await createGoal({
        item_name: formData.item_name.trim(),
        retailer: formData.retailer.trim(),
        target_amount: targetAmount,
        target_date: formData.target_date,
      });

      navigate(`/goals/${data.goal.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  const monthsRemaining = calculateMonthsRemaining(formData.target_date);

  const previewMonthlyTarget =
    Number(formData.target_amount) > 0 && monthsRemaining > 0
      ? Number(formData.target_amount) / monthsRemaining
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
          you need to save each month based on your target date.
        </p>

        {error && <p className="error-message">{error}</p>}

        <form className="goal-form" onSubmit={handleSubmit}>
          <label htmlFor="item_name">What are you saving for?</label>
          <input
            id="item_name"
            name="item_name"
            type="text"
            placeholder="Example: Nintendo Switch 2"
            value={formData.item_name}
            onChange={handleChange}
            required
          />

          <label htmlFor="retailer">Preferred Retailer</label>
          <input
            id="retailer"
            name="retailer"
            type="text"
            placeholder="Example: Best Buy"
            value={formData.retailer}
            onChange={handleChange}
          />

          <label htmlFor="target_amount">Target Amount</label>
          <input
            id="target_amount"
            name="target_amount"
            type="number"
            min="1"
            step="0.01"
            placeholder="500"
            value={formData.target_amount}
            onChange={handleChange}
            required
          />

          <label htmlFor="target_date">Target Date</label>
          <input
            id="target_date"
            name="target_date"
            type="date"
            min={getTomorrowDateString()}
            value={formData.target_date}
            onChange={handleChange}
            required
          />

          <div className="goal-preview">
            <span>Months remaining</span>
            <strong>{monthsRemaining || "--"}</strong>
          </div>

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