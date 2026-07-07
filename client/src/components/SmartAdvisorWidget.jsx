import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

import {
  createAdvisorResponse,
  getAdvisorHistory,
} from "../services/api";
import { useAuth } from "../context/AuthContext";

function getPageContext(pathname) {
  const goalMatch = pathname.match(/^\/goals\/(\d+)/);

  if (goalMatch) {
    return {
      context_type: "goal",
      goal_id: Number(goalMatch[1]),
      label: "Goal context",
      placeholder: "Ask about this goal...",
      quickPrompts: [
        "Is this timeline realistic?",
        "How can I lower the monthly target?",
        "Should I wait for a sale before buying?",
      ],
    };
  }

  if (pathname === "/dashboard") {
    return {
      context_type: "dashboard",
      goal_id: null,
      label: "Dashboard context",
      placeholder: "Ask about your goals...",
      quickPrompts: [
        "Which goal should I prioritize?",
        "Am I taking on too many goals?",
        "How can I lower my total monthly target?",
      ],
    };
  }

  return {
    context_type: "general",
    goal_id: null,
    label: "General context",
    placeholder: "Ask Smart Buy Advisor...",
    quickPrompts: [
      "How should I plan a purchase?",
      "What makes a goal realistic?",
      "How should I compare cheaper alternatives?",
    ],
  };
}

function SmartAdvisorWidget() {
  const { isAuthenticated, authLoading } = useAuth();
  const location = useLocation();

  const pageContext = useMemo(
    () => getPageContext(location.pathname),
    [location.pathname]
  );

  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [advisorHistory, setAdvisorHistory] = useState([]);
  const [currentResponse, setCurrentResponse] = useState(null);
  const [error, setError] = useState("");
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    async function loadHistory() {
      if (!isOpen || !isAuthenticated) return;

      setIsLoadingHistory(true);
      setError("");

      try {
        const data = await getAdvisorHistory(pageContext.goal_id);
        setAdvisorHistory(data.advisor_responses || []);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoadingHistory(false);
      }
    }

    loadHistory();
  }, [isOpen, isAuthenticated, pageContext.goal_id]);

  if (authLoading || !isAuthenticated) {
    return null;
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedMessage = message.trim();

    if (!trimmedMessage) {
      setError("Ask the advisor a question first.");
      return;
    }

    setError("");
    setIsSubmitting(true);

    try {
      const payload = {
        message: trimmedMessage,
        context_type: pageContext.context_type,
      };

      if (pageContext.goal_id) {
        payload.goal_id = pageContext.goal_id;
      }

      const data = await createAdvisorResponse(payload);
      const savedResponse = data.advisor_response;

      setCurrentResponse(savedResponse);
      setAdvisorHistory((currentHistory) => [
        savedResponse,
        ...currentHistory,
      ]);
      setMessage("");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleQuickPrompt(prompt) {
    setMessage(prompt);
  }

  const responseToShow = currentResponse || advisorHistory[0] || null;
  const response = responseToShow?.response;

  return (
    <div className="advisor-widget">
      {isOpen && (
        <section className="advisor-panel">
          <div className="advisor-header">
            <div>
              <p className="eyebrow">Smart Buy Advisor</p>
              <h2>Ask before you buy</h2>
              <span>{pageContext.label}</span>
            </div>

            <button
              type="button"
              className="advisor-close-button"
              onClick={() => setIsOpen(false)}
              aria-label="Close Smart Buy Advisor"
            >
              ×
            </button>
          </div>

          <div className="advisor-quick-prompts">
            {pageContext.quickPrompts.map((prompt) => (
              <button
                type="button"
                key={prompt}
                onClick={() => handleQuickPrompt(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>

          <form className="advisor-form" onSubmit={handleSubmit}>
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              placeholder={pageContext.placeholder}
              rows="3"
            />

            <button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Thinking..." : "Ask Advisor"}
            </button>
          </form>

          {error && <p className="error-message">{error}</p>}

          {isLoadingHistory ? (
            <p className="advisor-muted">Loading advisor history...</p>
          ) : response ? (
            <article className="advisor-response-card">
              <h3>{response.summary}</h3>

              {response.recommendations?.length > 0 && (
                <div>
                  <h4>Recommendations</h4>
                  <ul>
                    {response.recommendations.map((recommendation) => (
                      <li key={recommendation}>{recommendation}</li>
                    ))}
                  </ul>
                </div>
              )}

              {response.action_items?.length > 0 && (
                <div>
                  <h4>Action Items</h4>
                  <ul>
                    {response.action_items.map((actionItem) => (
                      <li key={actionItem}>{actionItem}</li>
                    ))}
                  </ul>
                </div>
              )}

              {response.advisor_note && (
                <p className="advisor-note">{response.advisor_note}</p>
              )}
            </article>
          ) : (
            <div className="advisor-empty-state">
              <h3>No advisor responses yet</h3>
              <p>
                Ask a question from this page and the advisor will use the
                current context when possible.
              </p>
            </div>
          )}
        </section>
      )}

      <button
        type="button"
        className="advisor-floating-button"
        onClick={() => setIsOpen((currentValue) => !currentValue)}
      >
        <span className="advisor-notification-dot"></span>
        {isOpen ? "Close Advisor" : "Ask Advisor"}
      </button>
    </div>
  );
}

export default SmartAdvisorWidget;