import { useEffect, useState } from "react";

import { updatePassword, updateProfile } from "../services/api";
import { useAuth } from "../context/AuthContext";

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

  const [profileMessage, setProfileMessage] = useState("");
  const [passwordMessage, setPasswordMessage] = useState("");
  const [error, setError] = useState("");
  const [isSavingProfile, setIsSavingProfile] = useState(false);
  const [isSavingPassword, setIsSavingPassword] = useState(false);

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

      setProfileMessage("Profile updated successfully. Refresh if navbar name does not update immediately.");
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

  return (
    <main className="page form-page">
      <section className="profile-page-header">
        <p className="eyebrow">Account settings</p>
        <h1>Profile</h1>
        <p>
          Update your account details, monthly planning budget, and password.
        </p>
      </section>

      {error && <p className="error-message">{error}</p>}

      <section className="profile-grid">
        <article className="form-card profile-card">
          <h2>Personal Details</h2>
          <p>
            These details help personalize your Build n&apos; Buy experience.
          </p>

          {profileMessage && (
            <p className="success-message">{profileMessage}</p>
          )}

          <form className="goal-form" onSubmit={handleProfileSubmit}>
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
        </article>

        <article className="form-card profile-card">
          <h2>Change Password</h2>
          <p>
            Update your password while keeping your existing account and goals.
          </p>

          {passwordMessage && (
            <p className="success-message">{passwordMessage}</p>
          )}

          <form className="goal-form" onSubmit={handlePasswordSubmit}>
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
        </article>
      </section>
    </main>
  );
}

export default ProfilePage;