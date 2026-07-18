import { useEffect, useState } from "react";

const THEME_STORAGE_KEY = "build_n_buy_theme";

function getInitialTheme() {
  const savedTheme = localStorage.getItem(THEME_STORAGE_KEY);

  if (savedTheme === "dark" || savedTheme === "light") {
    return savedTheme;
  }

  return "light";
}

function applyTheme(theme) {
  // Set both roots because the stylesheet contains selectors for each convention;
  // removing the legacy class prevents stale styles from overriding data-theme.
  document.documentElement.setAttribute("data-theme", theme);
  document.body.setAttribute("data-theme", theme);

  document.documentElement.classList.remove("dark-theme");
  document.body.classList.remove("dark-theme");

  localStorage.setItem(THEME_STORAGE_KEY, theme);
}

function ThemeToggle() {
  const [theme, setTheme] = useState(getInitialTheme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  function handleToggleTheme() {
    setTheme((currentTheme) => (currentTheme === "dark" ? "light" : "dark"));
  }

  return (
    <button
      type="button"
      className="theme-toggle-button"
      onClick={handleToggleTheme}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
    >
      {theme === "dark" ? "Light" : "Dark"}
    </button>
  );
}

export default ThemeToggle;
