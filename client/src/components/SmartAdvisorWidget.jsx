import { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

import {
  createAdvisorResponse,
  createDemoNotification,
  getAdvisorHistory,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
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
  const [advisorHistory, setAdvisorHistory] = useState([]);
  const [currentResponse, setCurrentResponse] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [error, setError] = useState("");
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isLoadingNotifications, setIsLoadingNotifications] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

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

  useEffect(() => {
    loadNotifications();
  }, [isAuthenticated]);

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
          notification.id === notificationId
            ? data.notification
            : notification
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
        {unreadCount > 0 && (
          <span className="advisor-floating-count">{unreadCount}</span>
        )}
        {isOpen ? "Close Advisor" : "Ask Advisor"}
      </button>
    </div>
  );
}

export default SmartAdvisorWidget;