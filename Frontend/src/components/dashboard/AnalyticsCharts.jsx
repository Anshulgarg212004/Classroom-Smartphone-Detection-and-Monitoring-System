import { useMemo } from "react";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

function getValidDate(value) {
  if (!value) return null;

  const date = new Date(String(value).replace(" ", "T"));

  return Number.isNaN(date.getTime()) ? null : date;
}

function EmptyChart({ message }) {
  return (
    <div className="flex h-64 items-center justify-center rounded-lg bg-slate-50 text-sm text-slate-500">
      {message}
    </div>
  );
}

function ChartCard({ title, description, children }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <h3 className="text-base font-bold text-slate-900">
          {title}
        </h3>

        <p className="mt-1 text-sm text-slate-500">
          {description}
        </p>
      </div>

      {children}
    </div>
  );
}

function AnalyticsCharts({ detections = [] }) {
  const dailyData = useMemo(() => {
    const grouped = {};

    detections.forEach((item) => {
      const date = getValidDate(item.detected_at);

      if (!date) return;

      const key = [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, "0"),
        String(date.getDate()).padStart(2, "0"),
      ].join("-");

      if (!grouped[key]) {
        grouped[key] = {
          date: key,
          detections: 0,
        };
      }

      grouped[key].detections += 1;
    });

    return Object.values(grouped)
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(-14)
      .map((item) => ({
        ...item,
        label: item.date.slice(5),
      }));
  }, [detections]);

  const classroomData = useMemo(() => {
    const grouped = {};

    detections.forEach((item) => {
      const classroomId = item.classroom_id;

      if (classroomId === null || classroomId === undefined) {
        return;
      }

      const key = String(classroomId);

      if (!grouped[key]) {
        grouped[key] = {
          classroom: `Classroom ${key}`,
          detections: 0,
        };
      }

      grouped[key].detections += 1;
    });

    return Object.values(grouped).sort(
      (a, b) => b.detections - a.detections
    );
  }, [detections]);

  const confidenceData = useMemo(() => {
    return detections
      .map((item) => {
        const date = getValidDate(item.detected_at);
        const confidence = Number(item.confidence);

        if (
          !date ||
          item.confidence === null ||
          item.confidence === undefined ||
          !Number.isFinite(confidence)
        ) {
          return null;
        }

        return {
          timestamp: date.getTime(),
          time: date.toLocaleString([], {
            month: "short",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
          }),
          confidence: Number((confidence * 100).toFixed(1)),
          id: item.id,
        };
      })
      .filter(Boolean)
      .sort((a, b) => a.timestamp - b.timestamp)
      .slice(-30);
  }, [detections]);

  const hasDetections = detections.length > 0;

  return (
    <section className="mb-8">
      <div className="mb-5">
        <h2 className="text-xl font-bold text-slate-900">
          Analytics & Reports
        </h2>

        <p className="mt-1 text-sm text-slate-500">
          Visual analysis of the detection records currently loaded.
        </p>
      </div>

      {!hasDetections ? (
        <div className="rounded-xl border border-slate-200 bg-white p-8 text-center shadow-sm">
          <p className="font-semibold text-slate-700">
            No detection data available
          </p>

          <p className="mt-2 text-sm text-slate-500">
            Once detection records are available, your charts will
            appear here.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
          {/* Daily detections */}
          <ChartCard
            title="Daily Smartphone Detections"
            description="Number of detection records per day, for up to 14 dates."
          >
            {dailyData.length === 0 ? (
              <EmptyChart message="No valid dates found." />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={dailyData}
                  margin={{
                    top: 8,
                    right: 8,
                    left: -16,
                    bottom: 8,
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" />

                  <XAxis
                    dataKey="label"
                    tick={{ fontSize: 12 }}
                  />

                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 12 }}
                  />

                  <Tooltip />

                  <Legend />

                  <Bar
                    dataKey="detections"
                    name="Detections"
                    fill="#2563eb"
                    radius={[5, 5, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          {/* Classroom comparison */}
          <ChartCard
            title="Classroom Comparison"
            description="Detection count grouped by classroom ID."
          >
            {classroomData.length === 0 ? (
              <EmptyChart message="No classroom IDs found." />
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  data={classroomData}
                  margin={{
                    top: 8,
                    right: 8,
                    left: -16,
                    bottom: 8,
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" />

                  <XAxis
                    dataKey="classroom"
                    tick={{ fontSize: 11 }}
                    interval={0}
                  />

                  <YAxis
                    allowDecimals={false}
                    tick={{ fontSize: 12 }}
                  />

                  <Tooltip />

                  <Legend />

                  <Bar
                    dataKey="detections"
                    name="Detections"
                    fill="#7c3aed"
                    radius={[5, 5, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          {/* Confidence trend */}
          <div className="xl:col-span-2">
            <ChartCard
              title="YOLO Confidence Trend"
              description="Confidence percentage for the latest 30 loaded detection records."
            >
              {confidenceData.length === 0 ? (
                <EmptyChart message="No valid confidence values found." />
              ) : (
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart
                    data={confidenceData}
                    margin={{
                      top: 8,
                      right: 20,
                      left: 0,
                      bottom: 8,
                    }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis
                      dataKey="time"
                      tick={{ fontSize: 11 }}
                      interval="preserveStartEnd"
                    />

                    <YAxis
                      domain={[0, 100]}
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) => `${value}%`}
                    />

                    <Tooltip
                      formatter={(value) => [
                        `${value}%`,
                        "Confidence",
                      ]}
                    />

                    <Legend />

                    <Line
                      type="monotone"
                      dataKey="confidence"
                      name="Confidence"
                      stroke="#059669"
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 5 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              )}
            </ChartCard>
          </div>
        </div>
      )}

      <p className="mt-3 text-xs text-slate-500">
        Note: These charts use the records loaded by the detection
        API. Applying a classroom filter may change the chart data.
      </p>
    </section>
  );
}

export default AnalyticsCharts;
