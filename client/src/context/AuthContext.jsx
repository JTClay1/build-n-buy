import { createContext, useContext, useEffect, useState } from "react";
import { getCurrentUser, loginUser, signupUser } from "../services/api";

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    async function checkSession() {
      const token = localStorage.getItem("token");

      if (!token) {
        setAuthLoading(false);
        return;
      }

      try {
        const data = await getCurrentUser();
        setUser(data.user);
      } catch (error) {
        localStorage.removeItem("token");
        setUser(null);
      } finally {
        setAuthLoading(false);
      }
    }

    checkSession();
  }, []);

  async function login(credentials) {
    const data = await loginUser(credentials);
    localStorage.setItem("token", data.token);
    setUser(data.user);
    return data.user;
  }

  async function signup(userData) {
    const data = await signupUser(userData);
    localStorage.setItem("token", data.token);
    setUser(data.user);
    return data.user;
  }

  function logout() {
    localStorage.removeItem("token");
    setUser(null);
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        authLoading,
        login,
        signup,
        logout,
        isAuthenticated: Boolean(user),
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}