
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowLeft,
  School,
  MapPin,
  FileText,
  Save,
  LoaderCircle,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";

import api from "../api/axios";
import Sidebar from "../components/layout/Sidebar";

export default function AddClassroom() {
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    name: "",
    location: "",
    description: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  function handleChange(event) {
    const { name, value } = event.target;

    setFormData((previous) => ({
      ...previous,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setError("");
    setSuccess("");

    if (!formData.name.trim()) {
      setError("Please enter a classroom name.");
      return;
    }

    try {
      setLoading(true);

      const response = await api.post("/classrooms/", {
        name: formData.name.trim(),
        location: formData.location.trim(),
        description: formData.description.trim(),
      });

      setSuccess(
        response.data.message || "Classroom added successfully."
      );

      setFormData({
        name: "",
        location: "",
        description: "",
      });

      // Dashboard par wapas jaane ke liye thoda time
      setTimeout(() => {
        navigate("/");
      }, 1200);
    } catch (err) {
      setError(
        err.response?.data?.message ||
          err.message ||
          "Could not add classroom. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-5 sm:px-6 lg:px-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              Add Classroom
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              AI-Based Smartphone Detection System
            </p>
          </div>

          <button
            type="button"
            onClick={() => navigate("/")}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
          >
            <ArrowLeft size={17} />
            Dashboard
          </button>
        </div>
      </header>

      <div className="flex min-h-[calc(100vh-85px)]">
        <Sidebar />

        <main className="min-w-0 flex-1 px-4 py-8 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-slate-900">
                Create New Classroom
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Enter the classroom details below to add it to your system.
              </p>
            </div>

            <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
              <div className="mb-7 flex items-center gap-3 border-b border-slate-100 pb-5">
                <div className="rounded-xl bg-blue-50 p-3 text-blue-600">
                  <School size={25} />
                </div>

                <div>
                  <h3 className="font-bold text-slate-900">
                    Classroom Information
                  </h3>
                  <p className="text-sm text-slate-500">
                    Fields marked with * are required.
                  </p>
                </div>
              </div>

              <form onSubmit={handleSubmit} className="space-y-6">
                <div>
                  <label
                    htmlFor="name"
                    className="mb-2 block text-sm font-semibold text-slate-700"
                  >
                    Classroom Name *
                  </label>

                  <div className="relative">
                    <School
                      size={18}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    />

                    <input
                      id="name"
                      name="name"
                      type="text"
                      value={formData.name}
                      onChange={handleChange}
                      placeholder="e.g. CSE - Room 101"
                      maxLength={100}
                      required
                      className="w-full rounded-lg border border-slate-300 bg-white py-3 pl-10 pr-4 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="location"
                    className="mb-2 block text-sm font-semibold text-slate-700"
                  >
                    Classroom Location
                  </label>

                  <div className="relative">
                    <MapPin
                      size={18}
                      className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                    />

                    <input
                      id="location"
                      name="location"
                      type="text"
                      value={formData.location}
                      onChange={handleChange}
                      placeholder="e.g. First Floor, Block A"
                      maxLength={255}
                      className="w-full rounded-lg border border-slate-300 bg-white py-3 pl-10 pr-4 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor="description"
                    className="mb-2 block text-sm font-semibold text-slate-700"
                  >
                    Description
                  </label>

                  <div className="relative">
                    <FileText
                      size={18}
                      className="absolute left-3 top-3 text-slate-400"
                    />

                    <textarea
                      id="description"
                      name="description"
                      value={formData.description}
                      onChange={handleChange}
                      placeholder="Enter classroom details..."
                      rows={4}
                      className="w-full resize-y rounded-lg border border-slate-300 bg-white py-3 pl-10 pr-4 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                    />
                  </div>
                </div>

                {error && (
                  <div
                    role="alert"
                    className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700"
                  >
                    <AlertCircle size={18} className="mt-0.5 shrink-0" />
                    <p>{error}</p>
                  </div>
                )}

                {success && (
                  <div
                    role="status"
                    className="flex items-start gap-2 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700"
                  >
                    <CheckCircle2 size={18} className="mt-0.5 shrink-0" />
                    <p>{success}</p>
                  </div>
                )}

                <div className="flex flex-col-reverse gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:justify-end">
                  <button
                    type="button"
                    onClick={() => navigate("/")}
                    disabled={loading}
                    className="rounded-lg border border-slate-300 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 disabled:opacity-60"
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    disabled={loading}
                    className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {loading ? (
                      <>
                        <LoaderCircle size={18} className="animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Save size={18} />
                        Save Classroom
                      </>
                    )}
                  </button>
                </div>
              </form>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
