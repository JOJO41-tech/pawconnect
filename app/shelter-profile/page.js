"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const emptyForm = {
  contact_person: "",
  email: "",
  shelter_name: "",
  location: "",
  contact_number: "",
  description: "",
  verification_link: "",
  status: "",
};

export default function ShelterProfilePage() {
  const router = useRouter();

  const [shelterId, setShelterId] = useState(null);
  const [form, setForm] = useState(emptyForm);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [message, setMessage] = useState("");
  const [messageType, setMessageType] = useState("success");

  useEffect(() => {
    const savedShelter = localStorage.getItem("shelter");

    if (!savedShelter) {
      router.replace("/shelter-login");
      return;
    }

    try {
      const parsedShelter = JSON.parse(savedShelter);

      if (!parsedShelter?.shelter_id) {
        throw new Error("Invalid shelter session.");
      }

      setShelterId(parsedShelter.shelter_id);
      loadProfile(parsedShelter.shelter_id);
    } catch {
      localStorage.removeItem("shelter");
      router.replace("/shelter-login");
    }
  }, [router]);

  async function loadProfile(id) {
    try {
      setLoading(true);
      setMessage("");

      const response = await fetch(
        `/api/shelters/profile?shelter_id=${id}`,
        {
          cache: "no-store",
        }
      );

      const data = await readJsonResponse(response);

      if (!response.ok) {
        throw new Error(
          data.error || "Shelter profile could not be loaded."
        );
      }

      setForm({
        contact_person: data.contact_person || "",
        email: data.email || "",
        shelter_name: data.shelter_name || "",
        location: data.location || "",
        contact_number:
          data.contact_number || data.phone || "",
        description: data.description || "",
        verification_link: data.verification_link || "",
        status: data.status || "",
      });
    } catch (error) {
      showMessage(
        error.message || "Shelter profile could not be loaded.",
        "error"
      );
    } finally {
      setLoading(false);
    }
  }

  function handleChange(event) {
    const { name, value } = event.target;

    setForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    if (!shelterId) {
      showMessage("Shelter session could not be found.", "error");
      return;
    }

    try {
      setSaving(true);
      setMessage("");

      const response = await fetch("/api/shelters/profile", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          shelter_id: shelterId,
          contact_person: form.contact_person,
          shelter_name: form.shelter_name,
          location: form.location,
          contact_number: form.contact_number,
          description: form.description,
          verification_link: form.verification_link,
        }),
      });

      const data = await readJsonResponse(response);

      if (!response.ok) {
        throw new Error(
          data.error || "Shelter profile could not be updated."
        );
      }

      const currentSession = JSON.parse(
        localStorage.getItem("shelter") || "{}"
      );

      const updatedSession = {
        ...currentSession,
        ...data.shelter,
        name: data.shelter.contact_person,
      };

      localStorage.setItem(
        "shelter",
        JSON.stringify(updatedSession)
      );

      setForm((current) => ({
        ...current,
        ...data.shelter,
        contact_person: data.shelter.contact_person || "",
      }));

      showMessage("Shelter profile updated successfully.");
    } catch (error) {
      showMessage(
        error.message || "Shelter profile could not be updated.",
        "error"
      );
    } finally {
      setSaving(false);
    }
  }

  function showMessage(text, type = "success") {
    setMessage(text);
    setMessageType(type);
  }

  function handleLogout() {
    localStorage.removeItem("shelter");
    router.push("/shelter-login");
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-slate-100 flex items-center justify-center">
        <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
          <p className="font-semibold text-slate-600">
            Loading shelter profile...
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-100 text-slate-900">
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-5 flex flex-wrap items-center justify-between gap-4">
          <Link
            href="/"
            className="text-2xl font-extrabold text-green-800"
          >
            🐾 PawConnect
          </Link>

          <nav className="flex items-center gap-5 font-semibold">
            <Link
              href="/shelter"
              className="hover:text-green-700"
            >
              Dashboard
            </Link>

            <Link
              href="/shelter-profile"
              className="text-green-700"
            >
              Shelter Profile
            </Link>

            <button
              type="button"
              onClick={handleLogout}
              className="hover:text-red-600"
            >
              Logout
            </button>
          </nav>
        </div>
      </header>

      <section className="max-w-6xl mx-auto px-6 py-12">
        <div className="mb-8">
          <p className="text-green-700 font-bold mb-2">
            Shelter Management
          </p>

          <h1 className="text-4xl md:text-5xl font-extrabold mb-3">
            Edit Shelter Profile
          </h1>

          <p className="text-slate-600 max-w-2xl">
            Keep your shelter information accurate so adopters can
            contact and learn more about your organization.
          </p>
        </div>

        {message && (
          <div
            className={`mb-6 rounded-xl border p-4 font-semibold ${
              messageType === "error"
                ? "bg-red-100 border-red-300 text-red-800"
                : "bg-green-100 border-green-300 text-green-800"
            }`}
          >
            {message}
          </div>
        )}

        <div className="grid lg:grid-cols-[0.7fr_1.3fr] gap-6">
          <aside className="bg-slate-950 text-white rounded-2xl p-7 h-fit">
            <div className="w-24 h-24 rounded-2xl bg-green-100 text-5xl flex items-center justify-center mb-5">
              🏠
            </div>

            <h2 className="text-3xl font-extrabold text-green-400">
              {form.shelter_name || "Your Shelter"}
            </h2>

            <p className="text-slate-300 mt-2">
              {form.location || "Location not provided"}
            </p>

            <div className="border-t border-slate-800 mt-6 pt-6 space-y-4">
              <ProfilePreview
                label="Contact Person"
                value={form.contact_person}
              />

              <ProfilePreview label="Email" value={form.email} />

              <ProfilePreview
                label="Phone"
                value={form.contact_number}
              />

              <ProfilePreview
                label="Account Status"
                value={form.status || "Active"}
              />
            </div>

            {form.verification_link && (
              <a
                href={form.verification_link}
                target="_blank"
                rel="noreferrer"
                className="block text-center mt-6 border border-green-400 text-green-300 py-3 rounded-xl font-bold hover:bg-green-950"
              >
                Visit Shelter Page
              </a>
            )}
          </aside>

          <form
            onSubmit={handleSubmit}
            className="bg-white border border-slate-200 rounded-2xl shadow-sm p-7"
          >
            <div className="mb-7">
              <h2 className="text-2xl font-extrabold">
                Profile Information
              </h2>

              <p className="text-slate-500 mt-1">
                Fields marked with an asterisk are required.
              </p>
            </div>

            <div className="grid md:grid-cols-2 gap-5">
              <Input
                label="Contact Person"
                name="contact_person"
                value={form.contact_person}
                onChange={handleChange}
                placeholder="Example: John Smith"
                required
              />

              <Input
                label="Email"
                name="email"
                value={form.email}
                onChange={handleChange}
                disabled
              />

              <Input
                label="Shelter Name"
                name="shelter_name"
                value={form.shelter_name}
                onChange={handleChange}
                placeholder="Example: Happy Tails Shelter"
                required
              />

              <Input
                label="Contact Number"
                name="contact_number"
                value={form.contact_number}
                onChange={handleChange}
                placeholder="0812345678"
              />

              <div className="md:col-span-2">
                <Input
                  label="Location"
                  name="location"
                  value={form.location}
                  onChange={handleChange}
                  placeholder="Example: Rangsit, Pathum Thani"
                  required
                />
              </div>

              <div className="md:col-span-2">
                <Input
                  label="Facebook Page or Website"
                  name="verification_link"
                  value={form.verification_link}
                  onChange={handleChange}
                  placeholder="https://facebook.com/your-shelter"
                />
              </div>

              <div className="md:col-span-2">
                <label className="block mb-2 font-bold">
                  About the Shelter
                </label>

                <textarea
                  name="description"
                  value={form.description}
                  onChange={handleChange}
                  placeholder="Describe your shelter, mission, services, and animal welfare activities..."
                  className="w-full min-h-40 border border-slate-300 rounded-xl p-4"
                />
              </div>
            </div>

            <div className="flex flex-wrap gap-3 border-t border-slate-200 mt-7 pt-6">
              <button
                type="submit"
                disabled={saving}
                className="bg-green-700 text-white px-8 py-3 rounded-xl font-bold hover:bg-green-800 disabled:bg-slate-400"
              >
                {saving ? "Saving Profile..." : "Save Changes"}
              </button>

              <Link
                href="/shelter"
                className="border border-slate-300 px-8 py-3 rounded-xl font-bold hover:bg-slate-100"
              >
                Back to Dashboard
              </Link>
            </div>
          </form>
        </div>
      </section>
    </main>
  );
}

function Input({
  label,
  name,
  value,
  onChange,
  placeholder,
  required,
  disabled,
}) {
  return (
    <div>
      <label className="block mb-2 font-bold">
        {label}

        {required && (
          <span className="text-red-600 ml-1">*</span>
        )}
      </label>

      <input
        type="text"
        name={name}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        className={`w-full border border-slate-300 rounded-xl p-3 ${
          disabled
            ? "bg-slate-100 text-slate-500 cursor-not-allowed"
            : "bg-white"
        }`}
      />
    </div>
  );
}

function ProfilePreview({ label, value }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">
        {label}
      </p>

      <p className="font-semibold text-slate-200 mt-1 break-words">
        {value || "Not provided"}
      </p>
    </div>
  );
}

async function readJsonResponse(response) {
  const contentType = response.headers.get("content-type");

  if (!contentType?.includes("application/json")) {
    const text = await response.text();

    throw new Error(
      `The server returned an invalid response: ${text.slice(
        0,
        100
      )}`
    );
  }

  return response.json();
}