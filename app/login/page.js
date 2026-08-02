"use client";

import { Suspense, useState } from "react";
import {
  useRouter,
  useSearchParams,
} from "next/navigation";
import Link from "next/link";

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [message, setMessage] =
    useState("");

  const [submitting, setSubmitting] =
    useState(false);

  function handleChange(event) {
    const { name, value } =
      event.target;

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

      const response = await fetch(
        "/api/auth/login",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify(form),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Login failed."
        );
      }

      if (!data.user) {
        throw new Error(
          "Login API did not return user data."
        );
      }

      localStorage.setItem(
        "user",
        JSON.stringify(data.user)
      );

      const redirectPath =
        searchParams.get("redirect");

      router.push(
        redirectPath || "/animals"
      );

      router.refresh();
    } catch (error) {
      setMessage(
        error.message ||
          "Login failed."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 p-6 text-slate-900">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-lg">
        <h1 className="mb-2 text-4xl font-extrabold text-green-800">
          User Login
        </h1>

        <p className="mb-8 text-slate-600">
          Login to submit adoption
          applications and view their
          status.
        </p>

        {message && (
          <div className="mb-5 rounded-xl border border-red-300 bg-red-100 p-4 font-semibold text-red-800">
            {message}
          </div>
        )}

        <form
          onSubmit={handleSubmit}
          className="space-y-5"
        >
          <div>
            <label className="mb-2 block font-bold">
              Email
            </label>

            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="you@example.com"
              className="w-full rounded-lg border border-slate-300 p-3"
              required
            />
          </div>

          <div>
            <label className="mb-2 block font-bold">
              Password
            </label>

            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              placeholder="Enter password"
              className="w-full rounded-lg border border-slate-300 p-3"
              required
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-green-700 py-3 font-bold text-white hover:bg-green-800 disabled:bg-slate-400"
          >
            {submitting
              ? "Logging In..."
              : "Login"}
          </button>
        </form>

        <p className="mt-6 text-center text-slate-600">
          Don&apos;t have an account?{" "}
          <Link
            href="/register"
            className="font-bold text-green-700 hover:underline"
          >
            Register
          </Link>
        </p>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen items-center justify-center bg-slate-100">
          <p className="text-lg font-semibold text-slate-700">
            Loading login page...
          </p>
        </main>
      }
    >
      <LoginPageContent />
    </Suspense>
  );
}