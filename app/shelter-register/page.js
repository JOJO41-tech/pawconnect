"use client";

import { useState } from "react";
import Link from "next/link";

export default function ShelterRegisterPage() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    phone: "",
    shelter_name: "",
    location: "",
    contact_number: "",
    description: "",
    verification_link: "",
  });

  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState(false);

  const handleChange = (e) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const res = await fetch("/api/shelters/register", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(form),
    });

    const data = await res.json();

    if (res.ok) {
      setSuccess(true);
      setMessage(data.message || "Shelter account created successfully.");
      setForm({
        name: "",
        email: "",
        password: "",
        phone: "",
        shelter_name: "",
        location: "",
        contact_number: "",
        description: "",
        verification_link: "",
      });
    } else {
      setSuccess(false);
      setMessage(data.error || "Registration failed.");
    }
  };

  return (
    <main className="min-h-screen bg-slate-100 p-8 text-slate-900">
      <div className="max-w-3xl mx-auto bg-white p-8 rounded-2xl shadow-lg border border-slate-200">
        <h1 className="text-4xl font-extrabold text-green-800 mb-2">
          Create Shelter Account
        </h1>

        <p className="text-slate-600 mb-8">
          Register your shelter to manage animal listings and adoption requests.
        </p>

        {message && (
          <div
            className={`mb-6 rounded-lg p-4 font-semibold ${
              success
                ? "bg-green-100 border border-green-300 text-green-800"
                : "bg-red-100 border border-red-300 text-red-800"
            }`}
          >
            {message}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <h2 className="text-2xl font-bold text-slate-900">
            Account Information
          </h2>

          <div>
            <label className="block mb-2 font-bold">Contact Person Name</label>
            <input
              name="name"
              value={form.name}
              onChange={handleChange}
              placeholder="Example: John Smith"
              className="w-full border border-slate-300 p-3 rounded-lg"
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
              placeholder="Create password"
              className="w-full border border-slate-300 p-3 rounded-lg"
              required
            />
          </div>

          <div>
            <label className="block mb-2 font-bold">Phone Number</label>
            <input
              name="phone"
              value={form.phone}
              onChange={handleChange}
              placeholder="0812345678"
              className="w-full border border-slate-300 p-3 rounded-lg"
            />
          </div>

          <h2 className="text-2xl font-bold text-slate-900 pt-4">
            Shelter Information
          </h2>

          <div>
            <label className="block mb-2 font-bold">Shelter Name</label>
            <input
              name="shelter_name"
              value={form.shelter_name}
              onChange={handleChange}
              placeholder="Example: Happy Tails Shelter"
              className="w-full border border-slate-300 p-3 rounded-lg"
              required
            />
          </div>

          <div>
            <label className="block mb-2 font-bold">Shelter Location</label>
            <input
              name="location"
              value={form.location}
              onChange={handleChange}
              placeholder="Example: Rangsit, Pathum Thani"
              className="w-full border border-slate-300 p-3 rounded-lg"
              required
            />
          </div>

          <div>
            <label className="block mb-2 font-bold">
              Shelter Contact Number
            </label>
            <input
              name="contact_number"
              value={form.contact_number}
              onChange={handleChange}
              placeholder="Shelter phone number"
              className="w-full border border-slate-300 p-3 rounded-lg"
            />
          </div>

          <div>
            <label className="block mb-2 font-bold">Shelter Description</label>
            <textarea
              name="description"
              value={form.description}
              onChange={handleChange}
              placeholder="Briefly describe your shelter..."
              className="w-full border border-slate-300 p-3 rounded-lg min-h-28"
            />
          </div>

          <div>
            <label className="block mb-2 font-bold">
              Facebook Page / Website Link
            </label>
            <input
              name="verification_link"
              value={form.verification_link}
              onChange={handleChange}
              placeholder="https://facebook.com/your-shelter"
              className="w-full border border-slate-300 p-3 rounded-lg"
            />
          </div>

          <button
            type="submit"
            className="w-full bg-green-700 text-white py-3 rounded-lg font-bold hover:bg-green-800"
          >
            Create Shelter Account
          </button>

          <div className="text-center mt-6">
            <p className="text-slate-600">
              Already have a shelter account?
            </p>

            <Link
              href="/shelter-login"
              className="inline-block mt-2 text-green-700 font-bold hover:underline"
            >
              Login Here
            </Link>
          </div>
        </form>

        {success && (
          <Link
            href="/shelter-login"
            className="block text-center mt-5 bg-slate-900 text-white py-3 rounded-lg font-bold"
          >
            Continue to Shelter Login
          </Link>
        )}
      </div>
    </main>
  );
}