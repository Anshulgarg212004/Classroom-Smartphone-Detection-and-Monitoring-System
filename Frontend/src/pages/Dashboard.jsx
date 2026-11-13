
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Activity,
  CalendarDays,
  Clock,
  RefreshCw,
  Smartphone,
  Target,
  School,
  Camera,
  ChevronRight,
  Plus,
} from "lucide-react";

import api from "../api/axios";
import { getDetections } from "../services/detectionService";

import Sidebar from "../components/layout/Sidebar";
import DetectionTable from "../components/dashboard/DetectionTable";
import AnalyticsCharts from "../components/dashboard/AnalyticsCharts";
import StatCard from "../components/dashboard/StatCard";
import Loading from "../components/common/Loading";

function getDateValue(value) {
  if (!value) return null;

  const normalized = String(value).replace(" ", "T");
  const date = new Date(normalized);

  return Number.isNaN(date.getTime()) ? null : date;
}

function formatTime(value) {
  const date = getDateValue(value);

  if (!date) return "No detections";

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function Dashboard({ token, user, onLogout }) {
  const navigate = useNavigate();

  const [detections, setDetections] = useState([]);
  const [classroomId, setClassroomId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [dashboardStats, setDashboardStats] = useState({
    total_detections: 0,
    today_detections: 0,
    total_classrooms: 0,
  });

  // Load detection records
  const loadDetections = useCallback(async () => {
    if (!token) {
      setError("Login session missing. Please log in again.");
      setLoading(false);
      return;
    }

    setLoading(true);
    setError("");

    try {
      const records = await getDetections(token, classroomId);

      setDetections(Array.isArray(records) ? records : []);
    } catch (err) {
      setError(
        err.response?.data?.message ||
          err.message ||
          "Could not load detection records."
      );
    } finally {
      setLoading(false);
    }
  }, [token, classroomId]);

  // Load dashboard statistics
  const loadDashboardStats = useCallback(async () => {
    try {
      const response = await api.get("/dashboard");

      if (response.data.success) {
        setDashboardStats(response.data.stats);
      }
    } catch (err) {
      console.error(
        "Dashboard statistics error:",
        err.response?.data?.message || err.message || err
      );
    }
  }, []);

  useEffect(() => {
    loadDetections();
  }, [loadDetections]);

  useEffect(() => {
    loadDashboardStats();

    const intervalId = setInterval(() => {
      loadDashboardStats();
    }, 5000);

    return () => clearInterval(intervalId);
  }, [loadDashboardStats]);

  // Today's detections
  const today = new Date().toDateString();

  const todayDetections = detections.filter((item) => {
    const date = getDateValue(item.detected_at);

    return date && date.toDateString() === today;
  }).length;

  // Average confidence
  const averageConfidence =
    detections.length > 0
      ? (
          (detections.reduce(
            (sum, item) => sum + Number(item.confidence || 0),
            0
          ) /
            detections.length) *
          100
        ).toFixed(1)
      : "0.0";

  // Latest detection
  const latestDetection =
    detections.length > 0
      ? detections.reduce((latest, item) => {
          const currentDate = getDateValue(item.detected_at);
          const latestDate = getDateValue(latest?.detected_at);

          if (!currentDate) return latest;
          if (!latestDate || currentDate > latestDate) return item;

          return latest;
        }, null)
      : null;

  // Refresh dashboard
  const handleRefresh = () => {
    loadDetections();
    loadDashboardStats();
  };

  // Open Add Classroom page
  const handleAddClassroom = () => {
    navigate("/add-classroom");
  };

  // Open Classroom Monitoring page
  const handleMonitoring = () => {
    navigate("/classroom-monitoring");
  };

  return (
    <div className="min-h-screen bg-slate-100">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-5 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              Classroom Monitoring
            </h1>

            <p className="mt-1 text-sm text-slate-500">
              AI-Based Smartphone Detection System
            </p>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-semibold text-slate-800">
                {user?.name || user?.username || user?.email || "User"}
              </p>

              <p className="text-xs text-slate-500">
                Monitoring Dashboard
              </p>
            </div>

            <button
              type="button"
              onClick={onLogout}
              className="rounded-lg bg-red-50 px-4 py-2 text-sm font-semibold text-red-600 transition hover:bg-red-100"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Sidebar + Main Content */}
      <div className="flex min-h-[calc(100vh-85px)]">
        <Sidebar />

        <main className="min-w-0 flex-1 px-4 py-8 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-7xl">

            {/* Dashboard heading and actions */}
            <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">
                  Dashboard Overview
                </h2>

                <p className="mt-1 text-sm text-slate-500">
                  Monitor smartphone detections and classroom activity.
                </p>
              </div>

              <div className="flex flex-wrap gap-3">

                {/* Add Classroom Button */}
                <button
                  type="button"
                  onClick={handleAddClassroom}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700"
                >
                  <Plus size={18} />
                  Add Classroom
                </button>

                {/* Classroom Monitoring Button */}
                <button
                  type="button"
                  onClick={handleMonitoring}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-700"
                >
                  <Camera size={18} />
                  Classroom Monitoring
                  <ChevronRight size={17} />
                </button>

                {/* Refresh Button */}
                <button
                  type="button"
                  onClick={handleRefresh}
                  disabled={loading}
                  className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <RefreshCw
                    size={17}
                    className={loading ? "animate-spin" : ""}
                  />
                  Refresh Data
                </button>
              </div>
            </div>

            {/* Statistics */}
            <section className="mb-8 grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-5">
              <StatCard
                title="Total Detections"
                value={dashboardStats.total_detections ?? 0}
                description="All records in database"
                icon={Smartphone}
                color="blue"
              />

              <StatCard
                title="Today's Detections"
                value={dashboardStats.today_detections ?? todayDetections}
                description="Detections recorded today"
                icon={CalendarDays}
                color="green"
              />

              <StatCard
                title="Total Classrooms"
                value={dashboardStats.total_classrooms ?? 0}
                description="Classrooms in database"
                icon={School}
                color="blue"
              />

              <StatCard
                title="Average Confidence"
                value={`${averageConfidence}%`}
                description="Across loaded records"
                icon={Target}
                color="purple"
              />

              <StatCard
                title="Latest Detection"
                value={formatTime(latestDetection?.detected_at)}
                description={
                  latestDetection
                    ? getDateValue(
                        latestDetection.detected_at
                      )?.toLocaleDateString() || "Latest record"
                    : "No records available"
                }
                icon={Clock}
                color="orange"
              />
            </section>

            {/* Analytics Charts */}
            {!loading && !error && (
              <div className="mb-8">
                <AnalyticsCharts detections={detections} />
              </div>
            )}

            {/* Detection History */}
            <section
              id="detection-history"
              className="scroll-mt-6 rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6"
            >
              <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="flex items-center gap-2 text-lg font-bold text-slate-900">
                    <Activity size={21} className="text-blue-600" />
                    Detection History
                  </h3>

                  <p className="mt-1 text-sm text-slate-500">
                    View and filter recorded smartphone detections.
                  </p>
                </div>

                <div className="w-full sm:w-64">
                  <label
                    htmlFor="classroomId"
                    className="mb-1.5 block text-sm font-medium text-slate-700"
                  >
                    Filter by Classroom ID
                  </label>

                  <input
                    id="classroomId"
                    type="number"
                    min="1"
                    value={classroomId}
                    onChange={(event) =>
                      setClassroomId(event.target.value)
                    }
                    placeholder="Enter classroom ID"
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                  />
                </div>
              </div>

              {/* Error Message */}
              {error && (
                <div
                  role="alert"
                  className="mb-5 flex flex-col gap-3 rounded-lg border border-red-200 bg-red-50 p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <p className="text-sm text-red-700">{error}</p>

                  <button
                    type="button"
                    onClick={loadDetections}
                    className="shrink-0 rounded-md bg-red-100 px-3 py-2 text-sm font-semibold text-red-700 transition hover:bg-red-200"
                  >
                    Try Again
                  </button>
                </div>
              )}

              {/* Detection Table */}
              {loading ? (
                <Loading />
              ) : (
                <DetectionTable detections={detections} />
              )}

              {!loading && !error && (
                <div className="mt-4 border-t border-slate-100 pt-4">
                  <p className="text-sm text-slate-500">
                    Records loaded:{" "}
                    <span className="font-semibold text-slate-700">
                      {detections.length}
                    </span>
                  </p>
                </div>
              )}
            </section>

            {/* Footer */}
            <footer className="mt-6 text-center text-xs text-slate-500">
              <p>
                Dashboard statistics refresh automatically every 5 seconds.
              </p>

              <p className="mt-1">
                Charts and confidence calculations use currently loaded
                detection records.
              </p>
            </footer>

          </div>
        </main>
      </div>
    </div>
  );
}
