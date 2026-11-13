
import { useState } from "react";
import { Camera } from "lucide-react";
import { loginUser } from "../services/authService";
import Button from "../components/common/Button";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const data = await loginUser(email, password);

      if (!data.access_token) {
        throw new Error("Login response mein access_token nahi mila.");
      }

      onLogin(data.access_token, data.user || { email });
    } catch (err) {
      setError(
        err.message === "Failed to fetch"
          ? "Flask server se connection nahi ho raha."
          : err.message
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10">
      <div className="grid w-full max-w-4xl overflow-hidden rounded-3xl bg-white shadow-2xl md:grid-cols-2">
        <section className="hidden flex-col justify-between bg-blue-700 p-10 text-white md:flex">
          <div>
            <Camera size={36} />
            <h1 className="mt-8 text-4xl font-bold leading-tight">
              Classroom Smartphone Monitoring
            </h1>
            <p className="mt-5 leading-7 text-blue-100">
              Monitor smartphone detections and review classroom activity
              from one dashboard.
            </p>
          </div>
          <p className="text-sm text-blue-200">
            OpenCV · YOLO · Flask · MySQL
          </p>
        </section>

        <section className="p-7 sm:p-10">
          <div className="mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-700 md:hidden">
            <Camera size={26} />
          </div>

          <h2 className="text-2xl font-bold text-slate-900">Welcome back</h2>
          <p className="mt-2 text-sm text-slate-500">
            Sign in to access your monitoring dashboard.
          </p>

          <form onSubmit={handleSubmit} className="mt-8 space-y-5">
            <div>
              <label
                htmlFor="email"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Email address
              </label>
              <input
                id="email"
                type="email"
                required
                autoComplete="username"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                className="w-full rounded-xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                required
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Enter your password"
                className="w-full rounded-xl border border-slate-200 px-4 py-3 outline-none focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
              />
            </div>

            {error && (
              <p
                role="alert"
                className="rounded-lg bg-red-50 p-3 text-sm text-red-700"
              >
                {error}
              </p>
            )}

            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          <p className="mt-6 text-xs leading-5 text-slate-400">
            Use the staff account registered with your Flask backend.
          </p>
        </section>
      </div>
    </main>
  );
}
