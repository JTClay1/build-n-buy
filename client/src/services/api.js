const API_BASE_URL = "http://localhost:5555/api";

export async function apiRequest(endpoint, options = {}) {
  const token = localStorage.getItem("token");

  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || data.msg || "Something went wrong");
  }

  return data;
}

export function signupUser(userData) {
  return apiRequest("/auth/signup", {
    method: "POST",
    body: JSON.stringify(userData),
  });
}

export function loginUser(credentials) {
  return apiRequest("/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export async function updateProfile(profileData) {
  return apiRequest("/auth/profile", {
    method: "PATCH",
    body: JSON.stringify(profileData),
  });
}

export async function updatePassword(passwordData) {
  return apiRequest("/auth/password", {
    method: "PATCH",
    body: JSON.stringify(passwordData),
  });
}

export function getCurrentUser() {
  return apiRequest("/auth/me");
}

export function getDashboard() {
  return apiRequest("/dashboard");
}

export function getGoals() {
  return apiRequest("/goals");
}

export function createGoal(goalData) {
  return apiRequest("/goals", {
    method: "POST",
    body: JSON.stringify(goalData),
  });
}

export function getGoal(goalId) {
  return apiRequest(`/goals/${goalId}`);
}

export function updateGoal(goalId, goalData) {
  return apiRequest(`/goals/${goalId}`, {
    method: "PATCH",
    body: JSON.stringify(goalData),
  });
}

export function deleteGoal(goalId) {
  return apiRequest(`/goals/${goalId}`, {
    method: "DELETE",
  });
}

export function createContribution(goalId, contributionData) {
  return apiRequest(`/goals/${goalId}/contributions`, {
    method: "POST",
    body: JSON.stringify(contributionData),
  });
}

export function deleteContribution(contributionId) {
  return apiRequest(`/contributions/${contributionId}`, {
    method: "DELETE",
  });
}

export async function createAdvisorResponse(advisorData) {
  return apiRequest("/advisor", {
    method: "POST",
    body: JSON.stringify(advisorData),
  });
}

export async function saveAdvisorResponse(advisorData) {
  return apiRequest("/advisor/save", {
    method: "POST",
    body: JSON.stringify(advisorData),
  });
}

export async function getAdvisorSnapshot() {
  return apiRequest("/advisor/snapshot");
}

export async function getAdvisorHistory(goalId = null) {
  const queryString = goalId ? `?goal_id=${goalId}` : "";

  return apiRequest(`/advisor/history${queryString}`);
}

export async function getNotifications() {
  return apiRequest("/notifications");
}

export async function createDemoNotification(goalId = null) {
  return apiRequest("/notifications/demo", {
    method: "POST",
    body: JSON.stringify(goalId ? { goal_id: goalId } : {}),
  });
}

export async function markNotificationRead(notificationId) {
  return apiRequest(`/notifications/${notificationId}/read`, {
    method: "PATCH",
  });
}

export async function markAllNotificationsRead() {
  return apiRequest("/notifications/read-all", {
    method: "PATCH",
  });
}

export async function getBudgetItems() {
  return apiRequest("/budget-items");
}

export async function createBudgetItem(budgetItemData) {
  return apiRequest("/budget-items", {
    method: "POST",
    body: JSON.stringify(budgetItemData),
  });
}

export async function updateBudgetItem(itemId, budgetItemData) {
  return apiRequest(`/budget-items/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify(budgetItemData),
  });
}

export async function deleteBudgetItem(itemId) {
  return apiRequest(`/budget-items/${itemId}`, {
    method: "DELETE",
  });
}
export async function getGoalPrices(goalId) {
  return apiRequest(`/goals/${goalId}/prices`);
}

export async function createGoalPrice(goalId, priceData) {
  return apiRequest(`/goals/${goalId}/prices`, {
    method: "POST",
    body: JSON.stringify(priceData),
  });
}

export async function updateGoalPrice(priceId, priceData) {
  return apiRequest(`/prices/${priceId}`, {
    method: "PATCH",
    body: JSON.stringify(priceData),
  });
}

export async function deleteGoalPrice(priceId) {
  return apiRequest(`/prices/${priceId}`, {
    method: "DELETE",
  });
}

export async function refreshRetailerPrice(priceId, options = {}) {
  return apiRequest(`/prices/${priceId}/refresh`, {
    method: "PATCH",
    body: JSON.stringify(options),
  });
}

export async function refreshGoalPrices(goalId, options = {}) {
  return apiRequest(`/goals/${goalId}/prices/refresh`, {
    method: "POST",
    body: JSON.stringify(options),
  });
}