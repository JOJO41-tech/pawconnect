"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function ShelterLoginPage() {
  const router = useRouter();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [message, setMessage] = useState("");

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const res = await fetch("/api/shelters/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(form),
    });

    const data = await res.json();

    if (res.ok) {
      localStorage.setItem("shelter", JSON.stringify(data.shelter));
      router.push("/shelter");
    } else {
      setMessage(data.error);
    }
  };

  return (
    <main className="min-h-screen bg-slate-100 flex items-center justify-center p-8 text-slate-900">
      <div className="w-full max-w-md bg-white p-8 rounded-2xl shadow-lg border border-slate-200">
        <h1 className="text-4xl font-extrabold text-green-800 mb-2">
          Shelter Login
        </h1>

        <p className="text-slate-600 mb-8">
          Login to manage animals, requests, and volunteer activities.
        </p>

        {message && (
          <div className="mb-5 bg-red-100 border border-red-300 text-red-800 p-4 rounded-lg font-bold">
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block mb-2 font-bold">Shelter Email</label>
            <input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="shelter@example.com"
              className="w-full border border-slate-300 p-3 rounded-lg"
              required
            />
          </div>

          <div>
            <label className="block mb-2 font-bold">Password</label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={handleChange}
              placeholder="Enter password"
              className="w-full border border-slate-300 p-3 rounded-lg"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full bg-green-700 text-white py-3 rounded-lg font-bold hover:bg-green-800"
          >
            Login
          </button>
        </form>

        <p className="text-center text-slate-600 mt-6">
          No shelter account?{" "}
          <Link href="/shelter-register" className="text-green-700 font-bold">
            Join as Shelter
          </Link>
        </p>
      </div>
    </main>
  );
}