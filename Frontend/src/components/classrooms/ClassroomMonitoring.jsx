import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  Camera,
  CameraOff,
  CircleAlert,
  LoaderCircle,
  RefreshCw,
  Video,
} from "lucide-react";

import {
  getClassrooms,
  startClassroomMonitoring,
  stopClassroomMonitoring,
  getMonitoringStatus,
  getMonitoringFrame,
} from "../../services/classroomService";

export default function ClassroomMonitoring() {
  const navigate = useNavigate();

  const [classrooms, setClassrooms] = useState([]);
  const [classroomId, setClassroomId] = useState("");

  const [monitoring, setMonitoring] = useState({
    is_running: false,
    classroom_id: null,
  });

  const [frameUrl, setFrameUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  // Load classrooms and camera status
  const refreshData = useCallback(async () => {
    try {
      const [classroomData, monitoringData] = await Promise.all([
        getClassrooms(),
        getMonitoringStatus(),
      ]);

      setClassrooms(classroomData);
      setMonitoring(monitoringData);

      if (
        !classroomId &&
        classroomData.length > 0 &&
        !monitoringData.is_running
      ) {
        setClassroomId(String(classroomData[0].id));
      }

      setError("");
    } catch (err) {
      setError(
        err.response?.data?.message ||
          "Data load nahi ho saka. Login aur backend check karo."
      );
    } finally {
      setLoading(false);
    }
  }, [classroomId]);

  useEffect(() => {
    refreshData();

    const interval = setInterval(refreshData, 3000);

    return () => clearInterval(interval);
  }, [refreshData]);

  // Load live laptop camera frames
  useEffect(() => {
    if (!monitoring.is_running) {
      setFrameUrl(null);
      return;
    }

    let active = true;
    let currentUrl = null;
    let requestInProgress = false;

    const loadFrame = async () => {
      if (requestInProgress) return;

      requestInProgress = true;

      try {
        const newUrl = await getMonitoringFrame();

        if (!active) {
          URL.revokeObjectURL(newUrl);
          return;
        }

        if (currentUrl) {
          URL.revokeObjectURL(currentUrl);
        }

        currentUrl = newUrl;
        setFrameUrl(newUrl);
      } catch (err) {
        if (active) {
          setError(
            err.response?.data?.message ||
              "Laptop camera frame load nahi ho raha."
          );
        }
      } finally {
        requestInProgress = false;
      }
    };

    loadFrame();

    const interval = setInterval(loadFrame, 700);

    return () => {
      active = false;
      clearInterval(interval);

      if (currentUrl) {
        URL.revokeObjectURL(currentUrl);
      }
    };
  }, [monitoring.is_running]);

  // Start laptop webcam
  const handleStart = async () => {
    if (!classroomId) {
      setError("Pehle classroom select karo.");
      return;
    }

    setError("");
    setNotice("");
    setActionLoading(true);

    try {
      const result = await startClassroomMonitoring(classroomId);

      setNotice(
        result.message || "Laptop webcam monitoring started."
      );

      await refreshData();
    } catch (err) {
      setError(
        err.response?.data?.message ||
          err.response?.data?.error ||
          err.message ||
          "Laptop camera start nahi ho saka."
      );
    } finally {
      setActionLoading(false);
    }
  };

  // Stop laptop webcam
  const handleStop = async () => {
    setError("");
    setNotice("");
    setActionLoading(true);

    try {
      const result = await stopClassroomMonitoring();

      setNotice(
        result.message || "Laptop webcam monitoring stopped."
      );

      await refreshData();
    } catch (err) {
      setError(
        err.response?.data?.message ||
          err.response?.data?.error ||
          err.message ||
          "Laptop camera stop nahi ho saka."
      );
    } finally {
      setActionLoading(false);
    }
  };

  const isRunning = Boolean(monitoring.is_running);

  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      {/* Navbar */}
      <header className="border-b border-slate-200 bg-white px-5 py-5 sm:px-8">
        <div className="mx-auto flex max-w-6xl items-center gap-4">
          <button
            onClick={() => navigate("/")}
            className="rounded-xl border border-slate-200 p-2.5 hover:bg-slate-100"
          >
            <ArrowLeft size={20} />
          </button>

          <div>
            <h1 className="text-xl font-bold sm:text-2xl">
              Laptop Camera Monitoring
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              AI-Based Classroom Smartphone Detection System
            </p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl p-4 sm:p-8">
        {/* Heading */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold">
            Webcam Monitoring
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            Detect smartphone usage using your laptop webcam and YOLO.
          </p>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-5 flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
            <CircleAlert size={20} />
            <p>{error}</p>
          </div>
        )}

        {/* Success */}
        {notice && (
          <div className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-700">
            {notice}
          </div>
        )}

        {/* Camera Card */}
        <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 p-5">
            <div className="flex items-center gap-3">
              <div
                className={`rounded-xl p-3 ${
                  isRunning
                    ? "bg-emerald-50 text-emerald-600"
                    : "bg-slate-100 text-slate-600"
                }`}
              >
                {isRunning ? (
                  <Video size={25} />
                ) : (
                  <CameraOff size={25} />
                )}
              </div>

              <div>
                <h3 className="font-bold">
                  Built-in Laptop Webcam
                </h3>
                <p className="text-sm text-slate-500">
                  Camera Index: 0
                </p>
              </div>
            </div>

            <span
              className={`rounded-full px-3 py-2 text-xs font-bold ${
                isRunning
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-slate-100 text-slate-600"
              }`}
            >
              {isRunning ? "MONITORING ON" : "MONITORING OFF"}
            </span>
          </div>

          {/* Live Feed */}
          <div className="p-5">
            <div className="overflow-hidden rounded-xl bg-black">
              {isRunning && frameUrl ? (
                <img
                  src={frameUrl}
                  alt="Laptop webcam live feed"
                  className="aspect-video w-full object-contain"
                />
              ) : (
                <div className="flex aspect-video flex-col items-center justify-center gap-3 text-slate-400">
                  {isRunning ? (
                    <LoaderCircle
                      size={38}
                      className="animate-spin"
                    />
                  ) : (
                    <CameraOff size={42} />
                  )}

                  <p className="text-sm">
                    {isRunning
                      ? "Connecting to laptop webcam..."
                      : "Camera is currently stopped"}
                  </p>
                </div>
              )}
            </div>

            {/* Classroom Selection */}
            <div className="mt-5">
              <label className="mb-2 block text-sm font-semibold">
                Select Classroom
              </label>

              <select
                value={classroomId}
                onChange={(e) => setClassroomId(e.target.value)}
                disabled={isRunning || actionLoading || loading}
                className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-blue-500"
              >
                <option value="">Choose a classroom</option>

                {classrooms.map((classroom) => (
                  <option
                    key={classroom.id}
                    value={classroom.id}
                  >
                    {classroom.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Controls */}
            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <button
                onClick={handleStart}
                disabled={
                  isRunning ||
                  actionLoading ||
                  loading ||
                  !classroomId
                }
                className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 font-semibold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {actionLoading && !isRunning ? (
                  <LoaderCircle size={19} className="animate-spin" />
                ) : (
                  <Camera size={19} />
                )}
                Start Monitoring
              </button>

              <button
                onClick={handleStop}
                disabled={!isRunning || actionLoading}
                className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-red-50 px-5 py-3 font-semibold text-red-600 hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-40"
              >
                {actionLoading && isRunning ? (
                  <LoaderCircle size={19} className="animate-spin" />
                ) : (
                  <CameraOff size={19} />
                )}
                Stop Monitoring
              </button>

              <button
                onClick={refreshData}
                disabled={loading}
                className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 px-5 py-3 font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              >
                <RefreshCw
                  size={18}
                  className={loading ? "animate-spin" : ""}
                />
                Refresh
              </button>
            </div>
          </div>
        </section>

        <p className="mt-5 text-sm text-slate-500">
          Detection engine: YOLO | Camera: Laptop Webcam | Source: 0
        </p>
      </main>
    </div>
  );
}