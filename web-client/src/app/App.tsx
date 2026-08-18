import type { PropsWithChildren } from "react";
import { BrowserRouter, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { LoadingState } from "../components/ui";
import { AccountPage } from "../pages/AccountPage";
import { ChangePinPage } from "../pages/ChangePinPage";
import { HomePage } from "../pages/HomePage";
import { PolicyLibraryPage } from "../pages/PolicyLibraryPage";
import { PolicyPage } from "../pages/PolicyPage";
import { ReportWorkspacePage } from "../pages/ReportWorkspacePage";
import { ReportsPage } from "../pages/ReportsPage";
import { SavedPage } from "../pages/SavedPage";
import { SignInPage } from "../pages/SignInPage";
import {
  AdminAuditPage,
  AdminOverviewPage,
  AdminReportsPage,
  AdminStaffPage,
  SystemHealthPage,
} from "../admin/AdminPages";
import { AppShell } from "./AppShell";

function ProtectedRoute({ children }: PropsWithChildren) {
  const { status, profile } = useAuth();
  const location = useLocation();
  if (status === "loading") {
    return (
      <div className="route-loading">
        <LoadingState label="Opening secure workspace" />
      </div>
    );
  }
  if (status === "signed-out" || !profile) {
    return <Navigate to="/sign-in" state={{ from: location }} replace />;
  }
  if (profile.mustChangePin && location.pathname !== "/change-pin") {
    return <Navigate to="/change-pin" replace />;
  }
  return children;
}

function PublicOnlyRoute({ children }: PropsWithChildren) {
  const { status, profile } = useAuth();
  if (status === "loading") {
    return (
      <div className="route-loading route-loading--public">
        <LoadingState label="Checking session" />
      </div>
    );
  }
  if (status === "signed-in" && profile) {
    return <Navigate to={profile.mustChangePin ? "/change-pin" : "/"} replace />;
  }
  return children;
}

function AdminRoute({ children }: PropsWithChildren) {
  const { profile } = useAuth();
  if (profile?.role !== "admin") {
    return (
      <div className="not-authorized">
        <p className="eyebrow">Restricted area</p>
        <h1>Administrator access required</h1>
        <p>Your account does not have permission to open this workspace.</p>
      </div>
    );
  }
  return children;
}

function NotFoundPage() {
  return (
    <div className="not-authorized">
      <p className="eyebrow">Page not found</p>
      <h1>That workspace is unavailable</h1>
      <p>Check the address or return to the dashboard.</p>
    </div>
  );
}

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/sign-in"
          element={
            <PublicOnlyRoute>
              <SignInPage />
            </PublicOnlyRoute>
          }
        />
        <Route
          path="/change-pin"
          element={
            <ProtectedRoute>
              <ChangePinPage />
            </ProtectedRoute>
          }
        />
        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<HomePage />} />
          <Route path="policy" element={<PolicyPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="reports/new" element={<ReportWorkspacePage />} />
          <Route path="reports/:reportId" element={<ReportWorkspacePage />} />
          <Route path="library" element={<PolicyLibraryPage />} />
          <Route path="saved" element={<SavedPage />} />
          <Route path="account" element={<AccountPage />} />
          <Route
            path="admin"
            element={
              <AdminRoute>
                <AdminOverviewPage />
              </AdminRoute>
            }
          />
          <Route
            path="admin/staff"
            element={
              <AdminRoute>
                <AdminStaffPage />
              </AdminRoute>
            }
          />
          <Route
            path="admin/reports"
            element={
              <AdminRoute>
                <AdminReportsPage />
              </AdminRoute>
            }
          />
          <Route
            path="admin/audit"
            element={
              <AdminRoute>
                <AdminAuditPage />
              </AdminRoute>
            }
          />
          <Route
            path="admin/health"
            element={
              <AdminRoute>
                <SystemHealthPage />
              </AdminRoute>
            }
          />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
