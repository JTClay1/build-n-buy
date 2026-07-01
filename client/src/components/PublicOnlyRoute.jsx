import UnauthorizedPage from "../pages/UnauthorizedPage";
import { useAuth } from "../context/AuthContext";

function PublicOnlyRoute({ children }) {
  const { isAuthenticated, authLoading } = useAuth();

  if (authLoading) {
    return (
      <main className="page">
        <p>Loading...</p>
      </main>
    );
  }

  if (isAuthenticated) {
    return <UnauthorizedPage />;
  }

  return children;
}

export default PublicOnlyRoute;