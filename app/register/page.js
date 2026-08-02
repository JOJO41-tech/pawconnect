"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function RegisterPage() {
  const router = useRouter();

  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    phone: "",
  });

  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    try {
      setSubmitting(true);
      setMessage("");
      setSuccess(false);

      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(form),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Registration failed.");
      }

      setSuccess(true);
      setMessage("Account created successfully.");

      setForm({
        name: "",
        email: "",
        password: "",
        phone: "",
      });

      setTimeout(() => {
        router.push("/login");
      }, 1200);
    } catch (error) {
      setSuccess(false);
      setMessage(error.message || "Registration failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-100 flex items-center justify-center p-6 text-slate-900">
      <div className="w-full max-w-md bg-white border border-slate-200 rounded-2xl shadow-lg p-8">
        <h1 className="text-4xl font-extrabold text-green-800 mb-2">
          Create User Account
        </h1>

        <p className="text-slate-600 mb-8">
          Register as an adopter to browse animals and submit adoption requests.
        </p>

        {message && (
          <div
            className={`mb-5 rounded-xl p-4 font-semibold ${
              success
                ? "bg-green-100 border border-green-300 text-green-800"
                : "bg-red-100 border border-red-300 text-red-800"
            }`}
          >
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block mb-2 font-bold">Full Name</label>
            <input
              type="text"
              name="name"
              value={form.name}
              onChange={handleChange}
              placeholder="Your full name"
              className="w-full border border-slate-300 rounded-lg p-3"
              required
            />
          </div>

          <div>
            <label className="block mb-2 font-bold">Email</label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="you@example.com"
              className="w-full border border-slate-300 rounded-lg p-3"
              required
            />
          </div>

          <div>
            <label className="block mb-2 font-bold">Phone Number</label>
            <input
              type="text"
              name="phone"
              value={form.phone}
              onChange={handleChange}
              placeholder="0812345678"
              className="w-full border border-slate-300 rounded-lg p-3"
            />
          </div>

          <div>
            <label className="block mb-2 font-bold">Password</label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              placeholder="Create a password"
              className="w-full border border-slate-300 rounded-lg p-3"
              required
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full bg-green-700 text-white py-3 rounded-lg font-bold hover:bg-green-800 disabled:bg-slate-400"
          >
            {submitting ? "Creating Account..." : "Register"}
          </button>
        </form>

        <div className="text-center mt-6 space-y-2">
          <p className="text-slate-600">
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-green-700 font-bold hover:underline"
            >
              Login
            </Link>
          </p>

          <p className="text-slate-600">
            Represent a shelter?{" "}
            <Link
              href="/shelter-register"
              className="text-green-700 font-bold hover:underline"
            >
              Join as Shelter
            </Link>
          </p>
        </div>
      </div>
    </main>
  );
}