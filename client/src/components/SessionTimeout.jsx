import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";

const SESSION_TIMEOUT_MS = 15 * 60 * 1000;
const LAST_ACTIVITY_KEY = "build_n_buy_last_activity_at";

function SessionTimeout() {
  const { isAuthenticated, authLoading, logout } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (authLoading || !isAuthenticated) {
      return undefined;
    }

    function getLastActivityTime() {
      return Number(localStorage.getItem(LAST_ACTIVITY_KEY) || Date.now());
    }

    function markActivity() {
      localStorage.setItem(LAST_ACTIVITY_KEY, String(Date.now()));
    }

    function isSessionExpired() {
      const lastActivityTime = getLastActivityTime();
      return Date.now() - lastActivityTime > SESSION_TIMEOUT_MS;
    }

    function handleExpiredSession() {
      localStorage.removeItem(LAST_ACTIVITY_KEY);
      logout();
      navigate("/login");
    }

    function checkSession() {
      if (isSessionExpired()) {
        handleExpiredSession();
      }
    }

    function handleUserActivity() {
      if (isSessionExpired()) {
        handleExpiredSession();
        return;
      }

      markActivity();
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        checkSession();

        if (!isSessionExpired()) {
          markActivity();
        }
      }
    }

    markActivity();
    checkSession();

    const activityEvents = [
      "click",
      "keydown",
      "mousedown",
      "mousemove",
      "scroll",
      "touchstart",
    ];

    activityEvents.forEach((eventName) => {
      window.addEventListener(eventName, handleUserActivity, { passive: true });
    });

    window.addEventListener("focus", checkSession);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    const intervalId = window.setInterval(checkSession, 30 * 1000);

    return () => {
      activityEvents.forEach((eventName) => {
        window.removeEventListener(eventName, handleUserActivity);
      });

      window.removeEventListener("focus", checkSession);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
      window.clearInterval(intervalId);
    };
  }, [authLoading, isAuthenticated, logout, navigate]);

  return null;
}

export default SessionTimeout;