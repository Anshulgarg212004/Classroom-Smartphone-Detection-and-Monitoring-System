
import { Smartphone } from "lucide-react";

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(String(value).replace(" ", "T"));

  if (Number.isNaN(date.getTime())) {
    return String(value);
  }

  return date.toLocaleString();
}

function formatConfidence(value) {
  if (value === null || value === undefined || value === "") {
    return "—";
  }

  const confidence = Number(value);

  if (!Number.isFinite(confidence)) {
    return "—";
  }

  return `${(confidence * 100).toFixed(1)}%`;
}

function DetectionTable({ detections = [] }) {
  if (detections.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 px-4 py-12 text-center">
        <Smartphone
          size={36}
          className="mx-auto text-slate-400"
        />

        <h4 className="mt-3 font-semibold text-slate-800">
          No detections found
        </h4>

        <p className="mt-1 text-sm text-slate-500">
          Detection records will appear here after they are saved
          to the database.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-600">
              ID
            </th>
            <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-600">
              Classroom ID
            </th>
            <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-600">
              Object
            </th>
            <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-600">
              Confidence
            </th>
            <th className="whitespace-nowrap px-4 py-3 font-semibold text-slate-600">
              Date &amp; Time
            </th>
        
          </tr>
        </thead>

        <tbody className="divide-y divide-slate-100 bg-white">
          {detections.map((detection) => (
            <tr
              key={detection.id}
              className="transition-colors hover:bg-slate-50"
            >
              <td className="whitespace-nowrap px-4 py-3 font-medium text-slate-800">
                {detection.id}
              </td>

              <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                {detection.classroom_id ?? "—"}
              </td>

              <td className="whitespace-nowrap px-4 py-3">
                <span className="inline-flex items-center gap-2 rounded-full bg-blue-50 px-3 py-1 font-medium text-blue-700">
                  <Smartphone size={14} />
                  {detection.object_name || "Unknown"}
                </span>
              </td>

              <td className="whitespace-nowrap px-4 py-3">
                {formatConfidence(detection.confidence)}
              </td>

              <td className="whitespace-nowrap px-4 py-3 text-slate-600">
                {formatDate(detection.detected_at)}
              </td>

              
              
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default DetectionTable;
