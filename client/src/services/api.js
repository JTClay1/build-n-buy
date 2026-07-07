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

export async function getAdvisorHistory(goalId = null) {
  const queryString = goalId ? `?goal_id=${goalId}` : "";

  return apiRequest(`/advisor/history${queryString}`);
}