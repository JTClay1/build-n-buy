import { useEffect } from "react";

import { useAuth } from "../context/AuthContext";
import { runDailyPriceCheck } from "../services/api";

const LAST_AUTO_CHECK_DATE_KEY = "build_n_buy_last_price_auto_check_date";

function getLocalDateKey(date = new Date()) {
  return date.toISOString().slice(0, 10);
}

function getMillisecondsUntilNextMidnight() {
  const now = new Date();
  const nextMidnight = new Date(now);

  nextMidnight.setHours(24, 0, 0, 0);

  return nextMidnight.getTime() - now.getTime();
}

function DailyPriceCheck() {
  const { isAuthenticated, authLoading } = useAuth();

  useEffect(() => {
    if (authLoading || !isAuthenticated) {
      return undefined;
    }

    let timeoutId = null;
    // Focus, visibility, and midnight events can arrive together; this guard
    // prevents overlapping network runs within the mounted component.
    let isRunning = false;

    async function runCheckIfNeeded() {
      if (isRunning) return;

      const todayKey = getLocalDateKey();
      // The browser marker avoids redundant requests, while the server applies a
      // second per-price daily guard for multiple tabs or devices.
      const lastCheckDate = localStorage.getItem(LAST_AUTO_CHECK_DATE_KEY);

      if (lastCheckDate === todayKey) {
        return;
      }

      isRunning = true;

      try {
        const data = await runDailyPriceCheck();

        localStorage.setItem(LAST_AUTO_CHECK_DATE_KEY, todayKey);

        console.log("Daily price auto-check complete:", data);
      } catch (error) {
        console.error("Daily price auto-check failed:", error);
      } finally {
        isRunning = false;
      }
    }

    function scheduleNextMidnightCheck() {
      // Recompute the delay after each run so DST and clock changes do not turn a
      // one-day timeout into a permanently drifting interval.
      const delay = getMillisecondsUntilNextMidnight();

      timeoutId = window.setTimeout(async () => {
        await runCheckIfNeeded();
        scheduleNextMidnightCheck();
      }, delay);
    }

    runCheckIfNeeded();
    scheduleNextMidnightCheck();

    function handleVisibilityChange() {
      // Timers may be throttled in background tabs; recheck when the user returns.
      if (document.visibilityState === "visible") {
        runCheckIfNeeded();
      }
    }

    window.addEventListener("focus", runCheckIfNeeded);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }

      window.removeEventListener("focus", runCheckIfNeeded);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [authLoading, isAuthenticated]);

  return null;
}

export default DailyPriceCheck;
