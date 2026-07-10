import { useEffect, useState } from "react";

import {
  createBudgetItem,
  deleteBudgetItem,
  getBudgetItems,
  updateBudgetItem,
  updatePassword,
  updateProfile,
} from "../services/api";
import { useAuth } from "../context/AuthContext";

function formatCurrency(amount) {
  return Number(amount || 0).toFixed(2);
}

function ProfilePage() {
  const { user } = useAuth();

  const [profileData, setProfileData] = useState({
    username: "",
    email: "",
    display_name: "",
    monthly_budget: "",
  });

  const [passwordData, setPasswordData] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const [budgetFormData, setBudgetFormData] = useState({
    title: "",
    amount: "",
    item_type: "expense",
    category: "",
    note: "",
  });

  const [budgetItems, setBudgetItems] = useState([]);
  const [budgetSummary, setBudgetSummary] = useState(null);

  const [profileMessage, setProfileMessage] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");
  const [budgetMessage, setBudgetMessage] = useState("");
  const [error, setError] = useState("");

  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingPassword, setIsSavingPassword] = useState(false);
  const [isSavingBudgetItem, setIsSavingBudgetItem] = useState(false);

  useEffect(() => {
    if (user) {
      setProfileData({
        username: user.username || "",
        email: user.email || "",
        display_name: user.display_name || "",
        monthly_budget: user.monthly_budget ?? "",
      });
    }
  }, [user]);

  useEffect(() => {
    async function loadBudgetItems() {
      try {
        const data = await getBudgetItems();

        setBudgetItems(data.budget_items || []);
        setBudgetSummary(data.summary || null);
      } catch (err) {
        setError(err.message);
      }
    }

    loadBudgetItems();
  }, []);

  function handleProfileChange(event) {
    const { name, value } = event.target;

    setProfileData((currentData) => ({
      ...currentData,
      [name]: value,
    }));
  }

  function handlePasswordChange(event) {
    const { name, value } = event.target;

    setPasswordData((currentData) => ({
      ...currentData,
      [name]: value,
    }));
  }

  function handleBudgetFormChange(event) {
    const { name, value } = event.target;

    setBudgetFormData((currentData) => ({
      ...currentData,
      [name]: value,
    }));
  }

  async function handleProfileSubmit(event) {
    event.preventDefault();

    setError("");
    setProfileMessage("");

    if (!profileData.username.trim()) {
      setError("Username cannot be empty.");
      return;
    }

    if (!profileData.email.trim()) {
      setError("Email cannot be empty.");
      return;
    }

    const monthlyBudget =
      profileData.monthly_budget === ""
        ? null
        : Number(profileData.monthly_budget);

    if (monthlyBudget !== null && monthlyBudget < 0) {
      setError("Monthly budget cannot be negative.");
      return;
    }

    setIsSavingProfile(true);

    try {
      await updateProfile({
        username: profileData.username.trim(),
        email: profileData.email.trim(),
        display_name: profileData.display_name.trim(),
        monthly_budget: monthlyBudget,
      });

      setProfileMessage("Profile updated successfully.");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSavingProfile(false);
    }
  }

  async function handlePasswordSubmit(event) {
    event.preventDefault();

    setError("");
    setPasswordMessage("");

    if (!passwordData.current_password || !passwordData.new_password) {
      setError("Current password and new password are required.");
      return;
    }

    if (passwordData.new_password.length < 6) {
      setError("New password must be at least 6 characters.");
      return;
    }

    if (passwordData.new_password !== passwordData.confirm_password) {
      setError("New passwords do not match.");
      return;
    }

    setIsSavingPassword(true);

    try {
      await updatePassword({
        current_password: passwordData.current_password,
        new_password: passwordData.new_password,
      });

      setPasswordMessage("Password updated successfully.");
      setPasswordData({
        current_password: "",
        new_password: "",
        confirm_password: "",
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSavingPassword(false);
    }
  }

  async function handleBudgetSubmit(event) {
    event.preventDefault();

    setError("");
    setBudgetMessage("");

    const amount = Number(budgetFormData.amount);

    if (!budgetFormData.title.trim()) {
      setError("Budget item title is required.");
      return;
    }

    if (amount < 0 || Number.isNaN(amount)) {
      setError("Budget amount must be a valid positive number.");
      return;
    }

    setIsSavingBudgetItem(true);

    try {
      const data = await createBudgetItem({
        title: budgetFormData.title.trim(),
        amount,
        item_type: budgetFormData.item_type,
        category: budgetFormData.category.trim(),
        note: budgetFormData.note.trim(),
      });

      setBudgetItems((currentItems) => [data.budget_item, ...currentItems]);
      setBudgetSummary(data.summary);
      setBudgetMessage("Budget item added successfully.");

      setBudgetFormData({
        title: "",
        amount: "",
        item_type: "expense",
        category: "",
        note: "",
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSavingBudgetItem(false);
    }
  }

  async function handleToggleBudgetItem(item) {
    setError("");
    setBudgetMessage("");

    try {
      const data = await updateBudgetItem(item.id, {
        is_active: !item.is_active,
      });

      setBudgetItems((currentItems) =>
        currentItems.map((budgetItem) =>
          budgetItem.id === item.id ? data.budget_item : budgetItem
        )
      );

      setBudgetSummary(data.summary);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleDeleteBudgetItem(itemId) {
    setError("");
    setBudgetMessage("");

    try {
      const data = await deleteBudgetItem(itemId);

      setBudgetItems((currentItems) =>
        currentItems.filter((budgetItem) => budgetItem.id !== itemId)
      );

      setBudgetSummary(data.summary);
      setBudgetMessage("Budget item deleted.");
    } catch (err) {
      setError(err.message);
    }
  }

  const incomeItems = budgetItems.filter(
    (item) => item.item_type === "income"
  );

  const expenseItems = budgetItems.filter(
    (item) => item.item_type === "expense"
  );

  return (
    <main className="page profile-hub-page">
      <section className="profile-page-header">
        <p className="eyebrow">Account settings</p>
        <h1>Profile & Budget Context</h1>
        <p>
          Manage your account, monthly cash flow, and password from one place.
          This budget context will eventually help Smart Advisor give better
          purchase advice.
        </p>
      </section>

      {error && <p className="error-message">{error}</p>}

      <article className="form-card profile-hub-card">
        <header className="profile-hub-hero">
          <div>
            <p className="eyebrow">Your account hub</p>
            <h2>{profileData.display_name || profileData.username || "Profile"}</h2>
            <p>
              Keep your personal details and monthly budget context current so
              Build n&apos; Buy can make smarter recommendations.
            </p>
          </div>

          {budgetSummary && (
            <div className="profile-hub-highlight">
              <span>Available After Goals</span>
              <strong>
                ${formatCurrency(budgetSummary.available_after_goals)}
              </strong>
            </div>
          )}
        </header>

        {budgetSummary && (
          <section className="profile-hub-summary-strip">
            <div>
              <span>Income</span>
              <strong>${formatCurrency(budgetSummary.monthly_income)}</strong>
            </div>

            <div>
              <span>Expenses</span>
              <strong>${formatCurrency(budgetSummary.monthly_expenses)}</strong>
            </div>

            <div>
              <span>Before Goals</span>
              <strong>
                ${formatCurrency(budgetSummary.available_before_goals)}
              </strong>
            </div>

            <div>
              <span>Goal Targets</span>
              <strong>
                ${formatCurrency(budgetSummary.total_goal_monthly_targets)}
              </strong>
            </div>

            <div>
              <span>After Goals</span>
              <strong>
                ${formatCurrency(budgetSummary.available_after_goals)}
              </strong>
            </div>
          </section>
        )}

        <section className="profile-hub-section">
          <div className="profile-hub-section-copy">
            <p className="eyebrow">Personal details</p>
            <h3>Account Info</h3>
            <p>
              Update your identity and monthly planning budget. This is the
              simple budget number attached directly to your profile.
            </p>
          </div>

          <div className="profile-hub-section-content">
            {profileMessage && (
              <p className="success-message">{profileMessage}</p>
            )}

            <form className="goal-form profile-hub-form" onSubmit={handleProfileSubmit}>
              <label htmlFor="display_name">Display Name</label>
              <input
                id="display_name"
                name="display_name"
                type="text"
                placeholder="Example: Josh"
                value={profileData.display_name}
                onChange={handleProfileChange}
              />

              <label htmlFor="username">Username</label>
              <input
                id="username"
                name="username"
                type="text"
                value={profileData.username}
                onChange={handleProfileChange}
                required
              />

              <label htmlFor="email">Email</label>
              <input
                id="email"
                name="email"
                type="email"
                value={profileData.email}
                onChange={handleProfileChange}
                required
              />

              <label htmlFor="monthly_budget">Monthly Planning Budget</label>
              <input
                id="monthly_budget"
                name="monthly_budget"
                type="number"
                min="0"
                step="0.01"
                placeholder="400"
                value={profileData.monthly_budget}
                onChange={handleProfileChange}
              />

              <button type="submit" disabled={isSavingProfile}>
                {isSavingProfile ? "Saving profile..." : "Save Profile"}
              </button>
            </form>
          </div>
        </section>

        <section className="profile-hub-section budget-section">
          <div className="profile-hub-section-copy">
            <p className="eyebrow">Budget context</p>
            <h3>Monthly Income & Expenses</h3>
            <p>
              Add personalized income and expense lines. These are flexible, so
              users can name categories however they want.
            </p>
          </div>

          <div className="profile-hub-section-content">
            {budgetMessage && (
              <p className="success-message">{budgetMessage}</p>
            )}

            <form className="goal-form budget-item-form" onSubmit={handleBudgetSubmit}>
                <div className="budget-field">
                    <label htmlFor="item_type">Type</label>
                    <select
                        id="item_type"
                        name="item_type"
                        value={budgetFormData.item_type}
                        onChange={handleBudgetFormChange}
                    >
                    <option value="income">Income</option>
                    <option value="expense">Expense</option>
                    </select>
                </div>

                 <div className="budget-field">
                    <label htmlFor="title">Title</label>
                    <input
                        id="title"
                        name="title"
                        type="text"
                        placeholder="Example: Rent, job income, groceries"
                        value={budgetFormData.title}
                        onChange={handleBudgetFormChange}
                        required
                    />
                </div>

                <div className="budget-field">
                    <label htmlFor="amount">Monthly Amount</label>
                    <input
                        id="amount"
                        name="amount"
                        type="number"
                        min="0"
                        step="0.01"
                        placeholder="500"
                        value={budgetFormData.amount}
                        onChange={handleBudgetFormChange}
                        required
                    />
                </div>

                <div className="budget-field">
                    <label htmlFor="category">Category</label>
                    <input
                        id="category"
                        name="category"
                        type="text"
                        placeholder="Example: Housing, Work, Food"
                        value={budgetFormData.category}
                        onChange={handleBudgetFormChange}
                    />
                </div>

                <div className="budget-field budget-field-wide">
                    <label htmlFor="note">Note</label>
                    <input
                        id="note"
                        name="note"
                        type="text"
                        placeholder="Optional note"
                        value={budgetFormData.note}
                        onChange={handleBudgetFormChange}
                    />
                </div>

                <button type="submit" disabled={isSavingBudgetItem}>
                    {isSavingBudgetItem ? "Adding..." : "Add Budget Item"}
                </button>
            </form>

            <div className="budget-item-columns unified">
              <BudgetItemList
                title="Income"
                items={incomeItems}
                onToggle={handleToggleBudgetItem}
                onDelete={handleDeleteBudgetItem}
              />

              <BudgetItemList
                title="Expenses"
                items={expenseItems}
                onToggle={handleToggleBudgetItem}
                onDelete={handleDeleteBudgetItem}
              />
            </div>
          </div>
        </section>

        <section className="profile-hub-section">
          <div className="profile-hub-section-copy">
            <p className="eyebrow">Security</p>
            <h3>Change Password</h3>
            <p>
              Update your password without affecting your goals, savings
              history, or budget context.
            </p>
          </div>

          <div className="profile-hub-section-content">
            {passwordMessage && (
              <p className="success-message">{passwordMessage}</p>
            )}

            <form className="goal-form profile-hub-form" onSubmit={handlePasswordSubmit}>
              <label htmlFor="current_password">Current Password</label>
              <input
                id="current_password"
                name="current_password"
                type="password"
                value={passwordData.current_password}
                onChange={handlePasswordChange}
                required
              />

              <label htmlFor="new_password">New Password</label>
              <input
                id="new_password"
                name="new_password"
                type="password"
                value={passwordData.new_password}
                onChange={handlePasswordChange}
                required
              />

              <label htmlFor="confirm_password">Confirm New Password</label>
              <input
                id="confirm_password"
                name="confirm_password"
                type="password"
                value={passwordData.confirm_password}
                onChange={handlePasswordChange}
                required
              />

              <button type="submit" disabled={isSavingPassword}>
                {isSavingPassword ? "Updating password..." : "Update Password"}
              </button>
            </form>
          </div>
        </section>
      </article>
    </main>
  );
}

function BudgetItemList({ title, items, onToggle, onDelete }) {
  return (
    <div className="budget-item-list-wrap">
      <h3>{title}</h3>

      {items.length > 0 ? (
        <div className="budget-item-list">
          {items.map((item) => (
            <article
              className={`budget-item ${item.is_active ? "" : "inactive"}`}
              key={item.id}
            >
              <div>
                <strong>{item.title}</strong>
                <p>
                  ${formatCurrency(item.amount)}
                  {item.category ? ` · ${item.category}` : ""}
                </p>
                {item.note && <span>{item.note}</span>}
              </div>

              <div className="budget-item-actions">
                <button type="button" onClick={() => onToggle(item)}>
                  {item.is_active ? "Pause" : "Activate"}
                </button>

                <button type="button" onClick={() => onDelete(item.id)}>
                  Delete
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state compact">
          <p>No {title.toLowerCase()} added yet.</p>
        </div>
      )}
    </div>
  );
}

export default ProfilePage;