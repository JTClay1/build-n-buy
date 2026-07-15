import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";

import {
  createAdvisorResponse,
  createDemoNotification,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  saveAdvisorResponse,
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
  const [showNotifications, setShowNotifications] = useState(false);
  const [message, setMessage] = useState("");
  const [currentResponse, setCurrentResponse] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [isLoadingNotifications, setIsLoadingNotifications] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSavingResponse, setIsSavingResponse] = useState(false);

  async function loadNotifications() {
    if (!isAuthenticated) return;

    setIsLoadingNotifications(true);

    try {
      const data = await getNotifications();
      setNotifications(data.notifications || []);
      setUnreadCount(data.unread_count || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoadingNotifications(false);
    }
  }

  async function submitAdvisorRequest(
    trimmedMessage,
    requestContext = pageContext,
    advisorMode = "standard"
  ) {
    if (!trimmedMessage) {
      setError("Ask the advisor a question first.");
      return;
    }

    setError("");
    setSuccessMessage("");
    setIsSubmitting(true);

    try {
      const payload = {
        message: trimmedMessage,
        context_type: requestContext.context_type,
        advisor_mode: advisorMode,
      };

      if (requestContext.goal_id) {
        payload.goal_id = requestContext.goal_id;
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

  useEffect(() => {
    loadNotifications();
  }, [isAuthenticated]);

  useEffect(() => {
    setCurrentResponse(null);
    setMessage("");
    setError("");
    setSuccessMessage("");
  }, [location.pathname]);

  useEffect(() => {
    function handleAdvisorRequest(event) {
      if (!isAuthenticated || location.pathname === "/advisor") return;

      const detail = event.detail || {};
      const requestMessage = String(detail.message || "").trim();

      if (!requestMessage) return;

      const requestContext = {
        context_type: detail.context_type || pageContext.context_type,
        goal_id: detail.goal_id ?? pageContext.goal_id,
        label: pageContext.label,
        placeholder: pageContext.placeholder,
        quickPrompts: pageContext.quickPrompts,
      };

      setIsOpen(true);
      setShowNotifications(false);
      setMessage(requestMessage);
      setError("");
      setSuccessMessage("");

      if (detail.autoSubmit) {
        submitAdvisorRequest(
          requestMessage,
          requestContext,
          detail.advisor_mode || "standard"
        );
      }
    }

    window.addEventListener("buildnbuy:advisor-request", handleAdvisorRequest);

    return () => {
      window.removeEventListener(
        "buildnbuy:advisor-request",
        handleAdvisorRequest
      );
    };
  }, [isAuthenticated, location.pathname, pageContext]);

  async function handleSubmit(event) {
    event.preventDefault();

    const trimmedMessage = message.trim();

    await submitAdvisorRequest(trimmedMessage);
  }

  async function handleSaveResponse() {
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

      setSuccessMessage("Saved to Advisor page.");
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSavingResponse(false);
    }
  }

  function handleQuickPrompt(prompt) {
    setMessage(prompt);
  }

  async function handleCreateDemoNotification() {
    setError("");

    try {
      await createDemoNotification(pageContext.goal_id);
      await loadNotifications();
      setShowNotifications(true);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleReadNotification(notificationId) {
    setError("");

    try {
      const data = await markNotificationRead(notificationId);

      setNotifications((currentNotifications) =>
        currentNotifications.map((notification) =>
          notification.id === notificationId ? data.notification : notification
        )
      );

      setUnreadCount(data.unread_count || 0);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleReadAllNotifications() {
    setError("");

    try {
      await markAllNotificationsRead();

      setNotifications((currentNotifications) =>
        currentNotifications.map((notification) => ({
          ...notification,
          is_read: true,
        }))
      );

      setUnreadCount(0);
    } catch (err) {
      setError(err.message);
    }
  }

  if (authLoading || !isAuthenticated || location.pathname === "/advisor") {
    return null;
  }

  const response = currentResponse?.response;

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

            <div className="advisor-header-actions">
              <button
                type="button"
                className="advisor-bell-button"
                onClick={() =>
                  setShowNotifications((currentValue) => !currentValue)
                }
                aria-label="Open notifications"
              >
                🔔
                {unreadCount > 0 && (
                  <span className="advisor-bell-count">{unreadCount}</span>
                )}
              </button>

              <button
                type="button"
                className="advisor-close-button"
                onClick={() => setIsOpen(false)}
                aria-label="Close Smart Buy Advisor"
              >
                ×
              </button>
            </div>
          </div>

          {showNotifications && (
            <section className="advisor-notifications-panel">
              <div className="advisor-notifications-header">
                <h3>Notifications</h3>

                {unreadCount > 0 && (
                  <button type="button" onClick={handleReadAllNotifications}>
                    Mark all read
                  </button>
                )}
              </div>

              <button
                type="button"
                className="advisor-demo-alert-button"
                onClick={handleCreateDemoNotification}
              >
                Create demo price alert
              </button>

              {isLoadingNotifications ? (
                <p className="advisor-muted">Loading notifications...</p>
              ) : notifications.length > 0 ? (
                <div className="advisor-notification-list">
                  {notifications.map((notification) => (
                    <article
                      key={notification.id}
                      className={`advisor-notification-item ${
                        notification.is_read ? "read" : "unread"
                      }`}
                    >
                      <div>
                        <h4>{notification.title}</h4>
                        <p>{notification.message}</p>
                        <span>
                          {new Date(
                            notification.created_at
                          ).toLocaleDateString()}
                        </span>
                      </div>

                      {!notification.is_read && (
                        <button
                          type="button"
                          onClick={() =>
                            handleReadNotification(notification.id)
                          }
                        >
                          Mark read
                        </button>
                      )}
                    </article>
                  ))}
                </div>
              ) : (
                <div className="advisor-empty-state compact">
                  <h3>No notifications yet</h3>
                  <p>
                    Future price alerts, sale updates, and advisor reminders
                    will show up here.
                  </p>
                </div>
              )}
            </section>
          )}

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
          {successMessage && <p className="success-message">{successMessage}</p>}

          {response ? (
            <article className="advisor-response-card">
              <div className="advisor-response-topline">
                <h3>{response.summary}</h3>

                <button
                  type="button"
                  onClick={handleSaveResponse}
                  disabled={isSavingResponse || currentResponse.is_saved}
                >
                  {currentResponse.is_saved
                    ? "Saved"
                    : isSavingResponse
                    ? "Saving..."
                    : "Save Response"}
                </button>
              </div>

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
              <h3>No active advisor response</h3>
              <p>
                Ask a quick question here, or open the full Advisor page for
                saved responses and a bigger planning view.
              </p>

              <Link to="/advisor">Open Advisor page</Link>
            </div>
          )}
        </section>
      )}

      <button
        type="button"
        className="advisor-floating-button"
        onClick={() => setIsOpen((currentValue) => !currentValue)}
      >
        {unreadCount > 0 && (
          <span className="advisor-floating-count">{unreadCount}</span>
        )}
        {isOpen ? "Close Advisor" : "Ask Advisor"}
      </button>
    </div>
  );
}

export default SmartAdvisorWidget;