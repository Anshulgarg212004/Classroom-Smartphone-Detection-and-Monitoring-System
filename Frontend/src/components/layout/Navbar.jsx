
import { Camera, LogOut } from "lucide-react";

export default function Navbar({ user, onLogout }) {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="rounded-xl bg-blue-700 p-2.5 text-white">
            <Camera size={23} />
          </div>
          <div>
            <h1 className="font-bold text-slate-900">Classroom Monitor</h1>
            <p className="text-xs text-slate-500">
              Smartphone detection system
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden text-right sm:block">
            <p className="text-sm font-semibold text-slate-800">
              {user?.name || user?.email || "Staff"}
            </p>
            <p className="text-xs capitalize text-slate-500">
              {user?.role || "staff"}
            </p>
          </div>

          <button
            type="button"
            onClick={onLogout}
            className="flex items-center gap-2 rounded-xl border border-slate-200 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50"
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </div>
    </header>
  );
}
