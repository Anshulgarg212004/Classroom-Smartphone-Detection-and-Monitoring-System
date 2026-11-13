
import { useCallback, useEffect, useState } from "react";
import api from "../api/axios";

export default function DashboardStats() {
  const [stats, setStats] = useState({
    total_detections: 0,
    today_detections: 0,
    total_classrooms: 0,
  });

  const [recentDetections, setRecentDetections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchDashboard = useCallback(async () => {
    try {
      const response = await api.get("/dashboard");
      const data = response.data;

      if (!data.success) {
        throw new Error("Dashboard data could not be loaded.");
      }

      setStats(data.stats);
      setRecentDetections(data.recent_detections || []);
      setError("");
    } catch (err) {
      console.error("Dashboard error:", err);
      setError(
        err.response?.data?.message ||
          "Unable to load dashboard statistics."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();

    const intervalId = setInterval(fetchDashboard, 5000);

    return () => clearInterval(intervalId);
  }, [fetchDashboard]);

  const cards = [
    {
      title: "Total Detections",
      value: stats.total_detections,
      icon: "📱",
    },
    {
      title: "Today's Detections",
      value: stats.today_detections,
      icon: "📅",
    },
    {
      title: "Total Classrooms",
      value: stats.total_classrooms,
      icon: "🏫",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-gray-800">
            Dashboard Overview
          </h2>
          <p className="text-sm text-gray-500">
            Classroom smartphone monitoring
          </p>
        </div>

        <button
          onClick={fetchDashboard}
          className="rounded-lg bg-blue-600 px-4 py-2 text-white
                     hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-100 p-3 text-red-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => (
          <div
            key={card.title}
            className="rounded-xl border border-gray-200
                       bg-white p-5 shadow-sm"
          >
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">{card.title}</p>
              <span className="text-3xl">{card.icon}</span>
            </div>

            <p className="mt-4 text-3xl font-bold text-gray-800">
              {loading ? "..." : card.value}
            </p>
          </div>
        ))}
      </div>

      <div className="overflow-hidden rounded-xl border bg-white">
        <div className="border-b p-5">
          <h3 className="text-lg font-semibold text-gray-800">
            Recent Detections
          </h3>
        </div>

        {loading && recentDetections.length === 0 ? (
          <p className="p-5 text-gray-500">Loading detections...</p>
        ) : recentDetections.length === 0 ? (
          <p className="p-5 text-gray-500">
            No detections recorded yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-gray-50">
                <tr>
                  <th className="p-3">ID</th>
                  <th className="p-3">Classroom</th>
                  <th className="p-3">Object</th>
                  <th className="p-3">Confidence</th>
                  <th className="p-3">Date & Time</th>
                </tr>
              </thead>

              <tbody>
                {recentDetections.map((item) => {
                  const confidence =
                    item.confidence == null
                      ? null
                      : Number(item.confidence);

                  return (
                    <tr key={item.id} className="border-t">
                      <td className="p-3">{item.id}</td>
                      <td className="p-3">
                        {item.classroom_name || "Unknown"}
                      </td>
                      <td className="p-3">
                        {item.object_name || "Unknown"}
                      </td>
                      <td className="p-3">
                        {confidence == null ||
                        !Number.isFinite(confidence)
                          ? "—"
                          : `${(
                              confidence <= 1
                                ? confidence * 100
                                : confidence
                            ).toFixed(1)}%`}
                      </td>
                      <td className="p-3">
                        {item.detected_at
                          ? new Date(item.detected_at).toLocaleString()
                          : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="text-xs text-gray-500">
        Data automatically refreshes every 5 seconds.
      </p>
    </div>
  );
}
