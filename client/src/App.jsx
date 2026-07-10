import { Route, Routes } from "react-router-dom";

import NavBar from "./components/NavBar";
import ProtectedRoute from "./components/ProtectedRoute";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import DashboardPage from "./pages/DashboardPage";
import NewGoalPage from "./pages/NewGoalPage";
import GoalDetailPage from "./pages/GoalDetailPage";
import EditGoalPage from "./pages/EditGoalPage";
import PublicOnlyRoute from "./components/PublicOnlyRoute";
import UnauthorizedPage from "./pages/UnauthorizedPage";
import SmartAdvisorWidget from "./components/SmartAdvisorWidget";
import ProfilePage from "./pages/ProfilePage";

function App() {
  return (
    <>
      <NavBar />

      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route
          path="/login"
          element={
            <PublicOnlyRoute>
              <LoginPage />
            </PublicOnlyRoute>
          }
        />

        <Route
          path="/signup"
          element={
            <PublicOnlyRoute>
              <SignupPage />
            </PublicOnlyRoute>
          }
        />

        <Route path="/unauthorized" element={<UnauthorizedPage />} />

        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/goals/new"
          element={
            <ProtectedRoute>
              <NewGoalPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/goals/:goalId"
          element={
            <ProtectedRoute>
              <GoalDetailPage />
            </ProtectedRoute>
          }
        />

        <Route
          path="/goals/:goalId/edit"
          element={
            <ProtectedRoute>
              <EditGoalPage />
            </ProtectedRoute>
          }
        />

        <Route
           path="/profile"
           element={
             <ProtectedRoute>
               <ProfilePage />
             </ProtectedRoute>
           }
        />
      </Routes>

      <SmartAdvisorWidget />
    </>
  );
}

export default App;