import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { deleteGoal, getGoal, updateGoal } from "../services/api";

function getTomorrowDateString() {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);

  const year = tomorrow.getFullYear();
  const month = String(tomorrow.getMonth() + 1).padStart(2, "0");
  const day = String(tomorrow.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function formatDateForInput(dateValue) {
  if (!dateValue) {
    return "";
  }

  return dateValue.split("T")[0];
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

function EditGoalPage() {
  const { goalId } = useParams();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    item_name: "",
    retailer: "",
    target_amount: "",
    target_date: "",
    status: "active",
  });

  const [goal, setGoal] = useState(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    async function loadGoal() {
      try {
        const data = await getGoal(goalId);
        const loadedGoal = data.goal;

        setGoal(loadedGoal);
        setFormData({
          item_name: loadedGoal.item_name,
          retailer: loadedGoal.retailer || "",
          target_amount: loadedGoal.target_amount,
          target_date: formatDateForInput(loadedGoal.target_date),
          status: loadedGoal.status,
        });
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

    if (monthsRemaining <= 0 && formData.status !== "completed") {
      setError("Target date must be in the future.");
      return;
    }

    setIsSubmitting(true);

    try {
      const data = await updateGoal(goalId, {
        item_name: formData.item_name.trim(),
        retailer: formData.retailer.trim(),
        target_amount: targetAmount,
        target_date: formData.target_date,
        status: formData.status,
      });

      navigate(`/goals/${data.goal.id}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleDelete() {
    const confirmed = window.confirm(
      "Are you sure you want to delete this goal? This will also delete its contributions."
    );

    if (!confirmed) return;

    setError("");
    setIsDeleting(true);

    try {
      await deleteGoal(goalId);
      navigate("/dashboard");
    } catch (err) {
      setError(err.message);
      setIsDeleting(false);
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

  const monthsRemaining = calculateMonthsRemaining(formData.target_date);

  const remainingAmount =
    Number(formData.target_amount) > Number(goal?.saved_amount || 0)
      ? Number(formData.target_amount) - Number(goal?.saved_amount || 0)
      : 0;

  const previewMonthlyTarget =
    remainingAmount > 0 && monthsRemaining > 0
      ? remainingAmount / monthsRemaining
      : 0;

  return (
    <main className="page form-page">
      <section className="form-card">
        <Link to={`/goals/${goalId}`} className="back-link">
          ← Back to goal
        </Link>

        <p className="eyebrow">Adjust your plan</p>
        <h1>Edit Goal</h1>
        <p>
          Update the purchase details, retailer, target date, or status for this
          savings goal.
        </p>

        {error && <p className="error-message">{error}</p>}

        <form className="goal-form" onSubmit={handleSubmit}>
          <label htmlFor="item_name">Item Name</label>
          <input
            id="item_name"
            name="item_name"
            type="text"
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

          <label htmlFor="status">Status</label>
          <select
            id="status"
            name="status"
            value={formData.status}
            onChange={handleChange}
          >
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="scrapped">Scrapped</option>
          </select>

          <div className="goal-preview">
            <span>Months remaining</span>
            <strong>{monthsRemaining || "--"}</strong>
          </div>

          <div className="goal-preview">
            <span>Estimated monthly target</span>
            <strong>${previewMonthlyTarget.toFixed(2)}</strong>
          </div>

          <button type="submit" disabled={isSubmitting || isDeleting}>
            {isSubmitting ? "Saving changes..." : "Save Changes"}
          </button>
        </form>

        <div className="danger-zone">
          <h2>Plans Changed?</h2>
          <p>
            No worries — you can delete this goal if it no longer fits your
            plans. This will also remove its contribution history.
          </p>

          <button
            type="button"
            className="danger-button"
            onClick={handleDelete}
            disabled={isDeleting || isSubmitting}
          >
            {isDeleting ? "Deleting..." : "Delete Goal"}
          </button>
        </div>
      </section>
    </main>
  );
}

export default EditGoalPage;