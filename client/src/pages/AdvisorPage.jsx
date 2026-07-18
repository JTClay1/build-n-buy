import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import {
  createAdvisorResponse,
  deleteAdvisorResponse,
  getAdvisorHistory,
  getAdvisorSnapshot,
  getGoals,
  saveAdvisorResponse,
} from "../services/api";

const SAVED_RESPONSES_PER_PAGE = 5;

function formatCurrency(amount) {
  return Number(amount || 0).toFixed(2);
}

function AdvisorResponseCard({ advisorResponse, onDelete, isDeleting }) {
  const response = advisorResponse.response;

  return (
    <article className="advisor-response-card saved-advisor-card">
      <div className="advisor-response-meta">
        <div>
          <span>{advisorResponse.context_type}</span>
          {advisorResponse.created_at && (
            <span>{new Date(advisorResponse.created_at).toLocaleString()}</span>
          )}
        </div>

        <button
          type="button"
          className="advisor-delete-response-button"
          disabled={isDeleting}
          onClick={() => onDelete(advisorResponse.id)}
        >
          {isDeleting ? "Deleting..." : "Delete"}
        </button>
      </div>

      <p className="advisor-question">“{advisorResponse.user_message}”</p>

      <h3>{response?.summary}</h3>

      {response?.recommendations?.length > 0 && (
        <div>
          <h4>Recommendations</h4>
          <ul>
            {response.recommendations.map((recommendation) => (
              <li key={recommendation}>{recommendation}</li>
            ))}
          </ul>
        </div>
      )}

      {response?.action_items?.length > 0 && (
        <div>
          <h4>Action Items</h4>
          <ul>
            {response.action_items.map((actionItem) => (
              <li key={actionItem}>{actionItem}</li>
            ))}
          </ul>
        </div>
      )}

      {response?.advisor_note && (
        <p className="advisor-note">{response.advisor_note}</p>
      )}
    </article>
  );
}

function AdvisorPage() {
  const [snapshot, setSnapshot] = useState(null);
  const [goals, setGoals] = useState([]);
  const [savedResponses, setSavedResponses] = useState([]);
  const [savedResponsesPage, setSavedResponsesPage] = useState(1);
  const [currentResponse, setCurrentResponse] = useState(null);
  const [message, setMessage] = useState("");
  const [contextType, setContextType] = useState("dashboard");
  const [goalId, setGoalId] = useState("");
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isLoadingPage, setIsLoadingPage] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSavingResponse, setIsSavingResponse] = useState(false);
  const [deletingResponseId, setDeletingResponseId] = useState(null);

  // Scrapped/completed goals remain in history but are excluded from new
  // goal-specific planning prompts.
  const activeGoals = useMemo(
    () => goals.filter((goal) => goal.status === "active"),
    [goals]
  );

  const totalSavedResponsePages = useMemo(
    () =>
      Math.max(
        1,
        Math.ceil(savedResponses.length / SAVED_RESPONSES_PER_PAGE)
      ),
    [savedResponses.length]
  );

  // Pagination is client-side because the bounded history endpoint returns a small
  // recent set and deletion must update the visible page immediately.
  const paginatedSavedResponses = useMemo(() => {
    const startIndex = (savedResponsesPage - 1) * SAVED_RESPONSES_PER_PAGE;

    return savedResponses.slice(
      startIndex,
      startIndex + SAVED_RESPONSES_PER_PAGE
    );
  }, [savedResponses, savedResponsesPage]);

  async function loadAdvisorPageData() {
    setIsLoadingPage(true);
    setError("");

    try {
      // These resources are independent and can load concurrently; rendering waits
      // for one coherent advisor workspace rather than three partial states.
      const [snapshotData, goalsData, historyData] = await Promise.all([
        getAdvisorSnapshot(),
        getGoals(),
        getAdvisorHistory(),
      ]);

      setSnapshot(snapshotData.snapshot);
      setGoals(goalsData.goals || []);
      setSavedResponses(historyData.advisor_responses || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingPage(false);
    }
  }

  useEffect(() => {
    loadAdvisorPageData();
  }, []);

  useEffect(() => {
    // Deleting the last item on a page can reduce the page count; clamp the cursor
    // instead of leaving the user on an empty, out-of-range page.
    if (savedResponsesPage > totalSavedResponsePages) {
      setSavedResponsesPage(totalSavedResponsePages);
    }
  }, [savedResponsesPage, totalSavedResponsePages]);

  function handleContextChange(event) {
    const selectedContext = event.target.value;

    setContextType(selectedContext);
    setCurrentResponse(null);
    setSuccessMessage("");

    if (selectedContext !== "goal") {
      setGoalId("");
    } else if (!goalId && activeGoals[0]) {
      // Select a valid default so switching into goal context is immediately usable.
      setGoalId(String(activeGoals[0].id));
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedMessage = message.trim();

    if (!trimmedMessage) {
      setError("Ask the advisor a question first.");
      return;
    }

    if (contextType === "goal" && !goalId) {
      setError("Choose a goal for goal-specific advice.");
      return;
    }

    setError("");
    setSuccessMessage("");
    setIsSubmitting(true);

    try {
      const payload = {
        message: trimmedMessage,
        context_type: contextType,
      };

      if (contextType === "goal") {
        payload.goal_id = Number(goalId);
      }

      const data = await createAdvisorResponse(payload);

      setCurrentResponse(data.advisor_response);
      setMessage("");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSaveCurrentResponse() {
    if (!currentResponse || currentResponse.is_saved) return;

    setError("");
    setSuccessMessage("");
    setIsSavingResponse(true);

    try {
      const data = await saveAdvisorResponse({
        user_message: currentResponse.user_message,
        context_type: currentResponse.context_type,
        goal_id: currentResponse.goal_id,
        response: currentResponse.response,
      });

      setCurrentResponse({
        ...data.advisor_response,
        is_saved: true,
      });

      // Prepend the server representation to match newest-first history ordering.
      setSavedResponses((currentResponses) => [
        data.advisor_response,
        ...currentResponses,
      ]);

      setSavedResponsesPage(1);
      setSuccessMessage("Advisor response saved.");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSavingResponse(false);
    }
  }

  async function handleDeleteSavedResponse(responseId) {
    const confirmed = window.confirm(
      "Delete this saved advisor response? This cannot be undone."
    );

    if (!confirmed) return;

    setError("");
    setSuccessMessage("");
    setDeletingResponseId(responseId);

    try {
      await deleteAdvisorResponse(responseId);

      setSavedResponses((currentResponses) =>
        currentResponses.filter(
          (advisorResponse) => advisorResponse.id !== responseId
        )
      );

      if (currentResponse?.id === responseId) {
        // Keep the generated content visible after unsaving, but return it to a
        // transient state so it can be saved again if desired.
        setCurrentResponse({
          ...currentResponse,
          id: null,
          is_saved: false,
          created_at: null,
        });
      }

      setSuccessMessage("Advisor response deleted.");
    } catch (err) {
      setError(err.message);
    } finally {
      setDeletingResponseId(null);
    }
  }

  function usePrompt(prompt, promptContext = contextType) {
    setMessage(prompt);
    setContextType(promptContext);

    if (promptContext !== "goal") {
      setGoalId("");
    }
  }

  if (isLoadingPage) {
    return (
      <main className="page-shell advisor-page">
        <p className="advisor-muted">Loading Advisor page...</p>
      </main>
    );
  }

  const goalSnapshot = snapshot?.goals || {};
  const budgetSnapshot = snapshot?.budget || {};

  return (
    <main className="page-shell advisor-page">
      <section className="advisor-page-hero">
        <div>
          <p className="eyebrow">Smart Buy Advisor</p>
          <h1>Financial planning workspace</h1>
          <p>
            Ask deeper questions, save useful responses, and review your goals
            and budget from one dedicated page.
          </p>
        </div>

        <Link to="/dashboard">Back to dashboard</Link>
      </section>

      {error && <p className="error-message">{error}</p>}
      {successMessage && <p className="success-message">{successMessage}</p>}

      <section className="advisor-snapshot-grid">
        <article>
          <span>Active Goals</span>
          <strong>{goalSnapshot.active_goals || 0}</strong>
          <p>{goalSnapshot.completed_goals || 0} completed</p>
        </article>

        <article>
          <span>Total Saved</span>
          <strong>${formatCurrency(goalSnapshot.total_saved)}</strong>
          <p>${formatCurrency(goalSnapshot.total_remaining)} remaining</p>
        </article>

        <article>
          <span>Income vs Expenses</span>
          <strong>
            ${formatCurrency(budgetSnapshot.monthly_income)} / $
            {formatCurrency(budgetSnapshot.monthly_expenses)}
          </strong>
          <p>Monthly income and expenses</p>
        </article>

        <article>
          <span>After Goals</span>
          <strong>${formatCurrency(budgetSnapshot.available_after_goals)}</strong>
          <p>
            After ${formatCurrency(goalSnapshot.total_monthly_targets)} in goal
            targets
          </p>
        </article>
      </section>

      <section className="advisor-workspace-grid">
        <article className="goal-detail-card advisor-page-card">
          <div className="section-header">
            <div>
              <p className="eyebrow">Ask Advisor</p>
              <h2>Full-page advisor</h2>
            </div>
          </div>

          <div className="advisor-context-controls">
            <label>
              Context
              <select value={contextType} onChange={handleContextChange}>
                <option value="dashboard">Overall dashboard</option>
                <option value="general">General planning</option>
                <option value="goal">Specific goal</option>
              </select>
            </label>

            {contextType === "goal" && (
              <label>
                Goal
                <select
                  value={goalId}
                  onChange={(event) => setGoalId(event.target.value)}
                >
                  <option value="">Choose a goal</option>
                  {activeGoals.map((goal) => (
                    <option key={goal.id} value={goal.id}>
                      {goal.item_name}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>

          <div className="advisor-quick-prompts">
            <button
              type="button"
              onClick={() =>
                usePrompt("Which goal should I prioritize?", "dashboard")
              }
            >
              Which goal should I prioritize?
            </button>

            <button
              type="button"
              onClick={() =>
                usePrompt("Can I afford my current active goals?", "dashboard")
              }
            >
              Can I afford my active goals?
            </button>

            <button
              type="button"
              onClick={() =>
                usePrompt(
                  "How should I think about buying now versus waiting?",
                  "general"
                )
              }
            >
              Buy now or wait?
            </button>
          </div>

          <form className="advisor-form advisor-page-form" onSubmit={handleSubmit}>
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder="Ask about your goals, cash flow, priorities, or whether a purchase makes sense..."
              rows="6"
            />

            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Thinking..." : "Ask Advisor"}
            </button>
          </form>

          {currentResponse?.response && (
            <article className="advisor-response-card advisor-current-response">
              <div className="advisor-response-topline">
                <h3>{currentResponse.response.summary}</h3>

                <button
                  type="button"
                  onClick={handleSaveCurrentResponse}
                  disabled={isSavingResponse || currentResponse.is_saved}
                >
                  {currentResponse.is_saved
                    ? "Saved"
                    : isSavingResponse
                      ? "Saving..."
                      : "Save Response"}
                </button>
              </div>

              {currentResponse.response.recommendations?.length > 0 && (
                <div>
                  <h4>Recommendations</h4>
                  <ul>
                    {currentResponse.response.recommendations.map(
                      (recommendation) => (
                        <li key={recommendation}>{recommendation}</li>
                      )
                    )}
                  </ul>
                </div>
              )}

              {currentResponse.response.action_items?.length > 0 && (
                <div>
                  <h4>Action Items</h4>
                  <ul>
                    {currentResponse.response.action_items.map((actionItem) => (
                      <li key={actionItem}>{actionItem}</li>
                    ))}
                  </ul>
                </div>
              )}

              {currentResponse.response.advisor_note && (
                <p className="advisor-note">
                  {currentResponse.response.advisor_note}
                </p>
              )}
            </article>
          )}
        </article>

        <section className="goal-detail-card advisor-page-card advisor-saved-section">
          <div className="section-header">
            <div>
              <p className="eyebrow">Saved responses</p>
              <h2>Advisor notes</h2>
            </div>

            <span>{savedResponses.length}</span>
          </div>

          {savedResponses.length > 0 ? (
            <>
              <div className="saved-advisor-list">
                {paginatedSavedResponses.map((advisorResponse) => (
                  <AdvisorResponseCard
                    key={advisorResponse.id}
                    advisorResponse={advisorResponse}
                    onDelete={handleDeleteSavedResponse}
                    isDeleting={deletingResponseId === advisorResponse.id}
                  />
                ))}
              </div>

              {savedResponses.length > SAVED_RESPONSES_PER_PAGE && (
                <div className="saved-advisor-pagination">
                  <button
                    type="button"
                    onClick={() =>
                      setSavedResponsesPage((currentPage) =>
                        Math.max(currentPage - 1, 1)
                      )
                    }
                    disabled={savedResponsesPage === 1}
                  >
                    Previous
                  </button>

                  <span>
                    Page {savedResponsesPage} of {totalSavedResponsePages}
                  </span>

                  <button
                    type="button"
                    onClick={() =>
                      setSavedResponsesPage((currentPage) =>
                        Math.min(currentPage + 1, totalSavedResponsePages)
                      )
                    }
                    disabled={savedResponsesPage === totalSavedResponsePages}
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="advisor-empty-state">
              <h3>No saved responses yet</h3>
              <p>
                Ask the advisor a question, then save the responses worth
                keeping here.
              </p>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

export default AdvisorPage;
