import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { deleteGoal, getGoal, updateGoal } from "../services/api";

function EditGoalPage() {
  const { goalId } = useParams();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    item_name: "",
    target_amount: "",
    months_to_goal: "",
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
          target_amount: loadedGoal.target_amount,
          months_to_goal: loadedGoal.months_to_goal,
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
      const data = await updateGoal(goalId, {
        item_name: formData.item_name.trim(),
        target_amount: targetAmount,
        months_to_goal: monthsToGoal,
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

  const previewMonthlyTarget =
    Number(formData.target_amount) > 0 && Number(formData.months_to_goal) > 0
      ? Number(formData.target_amount) / Number(formData.months_to_goal)
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
          Update the purchase details, timeline, or status for this savings
          goal.
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

          <label htmlFor="months_to_goal">Months to Goal</label>
          <input
            id="months_to_goal"
            name="months_to_goal"
            type="number"
            min="1"
            step="1"
            value={formData.months_to_goal}
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
            No worries — you can delete this goal if it no longer fits your plans.
            This will also remove its contribution history.
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