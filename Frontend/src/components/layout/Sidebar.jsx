
import { Activity, LayoutDashboard, Smartphone, Camera } from "lucide-react";
import { useLocation, useNavigate } from "react-router-dom";

const items = [
  {
    label: "Dashboard",
    icon: LayoutDashboard,
    path: "/",
  },
  {
    label: "Detection History",
    icon: Smartphone,
    path: "/#detection-history",
  },
  {
    label: "Monitoring Status",
    icon: Activity,
    path: "/#monitoring-status",
  },
  {
    label: "Classroom Monitoring",
    icon: Camera,
    path: "/classroom-monitoring",
  },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <aside className="hidden w-60 shrink-0 border-r border-slate-200 bg-white p-5 md:block">
      <p className="mb-4 px-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
        Workspace
      </p>

      <nav className="space-y-2" aria-label="Main navigation">
        {items.map(({ label, icon: Icon, path }) => {
          const active =
            path === "/"
              ? location.pathname === "/"
              : path === "/classroom-monitoring"
                ? location.pathname === "/classroom-monitoring"
                : false;

          return (
            <button
              key={label}
              type="button"
              onClick={() => {
                if (path === "/#detection-history") {
                  navigate("/");
                  setTimeout(() => {
                    document
                      .getElementById("detection-history")
                      ?.scrollIntoView({ behavior: "smooth" });
                  }, 100);
                } else if (path === "/#monitoring-status") {
                  navigate("/");
                  setTimeout(() => {
                    document
                      .getElementById("monitoring-status")
                      ?.scrollIntoView({ behavior: "smooth" });
                  }, 100);
                } else {
                  navigate(path);
                }
              }}
              className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm transition ${
                active
                  ? "bg-blue-50 font-semibold text-blue-700"
                  : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"
              }`}
            >
              <Icon size={18} />
              {label}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
