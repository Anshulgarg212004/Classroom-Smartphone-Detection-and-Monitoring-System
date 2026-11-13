
import { useState } from "react";
import {
  BrowserRouter,
  Route,
  Routes,
  Navigate,
} from "react-router-dom";

import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import AddClassroom from "./pages/AddClassroom.jsx";
import ClassroomMonitoring from "./components/classrooms/ClassroomMonitoring.jsx";

export default function App() {
  const [session, setSession] = useState(() => {
    const token = localStorage.getItem("classroom_access_token");
    const user = localStorage.getItem("classroom_user");

    if (!token) return null;

    return {
      token,
      user: user ? JSON.parse(user) : {},
    };
  });

  function handleLogin(token, user) {
    localStorage.setItem("classroom_access_token", token);
    localStorage.setItem("classroom_user", JSON.stringify(user));

    setSession({ token, user });
  }

  function handleLogout() {
    localStorage.removeItem("classroom_access_token");
    localStorage.removeItem("classroom_user");
    setSession(null);
  }

  return (
    <BrowserRouter>
      {!session ? (
        <Routes>
          <Route
            path="*"
            element={<Login onLogin={handleLogin} />}
          />
        </Routes>
      ) : (
        <Routes>
          <Route
            path="/"
            element={
              <Dashboard
                token={session.token}
                user={session.user}
                onLogout={handleLogout}
              />
            }
          />

          <Route
            path="/add-classroom"
            element={<AddClassroom />}
          />

          <Route
            path="/classroom-monitoring"
            element={<ClassroomMonitoring />}
          />

          <Route
            path="*"
            element={<Navigate to="/" replace />}
          />
        </Routes>
      )}
    </BrowserRouter>
  );
}
