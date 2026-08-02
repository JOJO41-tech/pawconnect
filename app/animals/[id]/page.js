"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";

export default function AnimalDetailsPage() {
  const params = useParams();
  const router = useRouter();

  const [animal, setAnimal] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    loadCurrentUser();

    if (params?.id) {
      loadAnimal(params.id);
    }
  }, [params?.id]);

  function loadCurrentUser() {
    const savedUser = localStorage.getItem("user");

    if (!savedUser) {
      setCurrentUser(null);
      return;
    }

    try {
      setCurrentUser(JSON.parse(savedUser));
    } catch {
      localStorage.removeItem("user");
      setCurrentUser(null);
    }
  }

  async function loadAnimal(id) {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(`/api/animals/${id}`, {
        cache: "no-store",
      });

      const contentType = response.headers.get("content-type");

      if (!contentType?.includes("application/json")) {
        throw new Error(
          "The animal API returned an invalid response."
        );
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Unable to load animal details."
        );
      }

      setAnimal(data);
    } catch (error) {
      setError(
        error.message || "Unable to load animal details."
      );
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    localStorage.removeItem("user");
    setCurrentUser(null);
    router.push("/");
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-[#fbf8f3] flex items-center justify-center">
        <div className="bg-white border border-slate-200 rounded-2xl p-8 shadow-sm">
          <p className="font-semibold text-slate-600">
            Loading animal details...
          </p>
        </div>
      </main>
    );
  }

  if (error || !animal) {
    return (
      <main className="min-h-screen bg-[#fbf8f3] flex items-center justify-center p-6">
        <div className="w-full max-w-lg bg-white border border-red-200 rounded-3xl p-10 text-center shadow-sm">
          <div className="text-7xl mb-5">🐾</div>

          <h1 className="text-3xl font-extrabold text-red-700 mb-3">
            Animal Not Found
          </h1>

          <p className="text-slate-600 mb-7">
            {error || "This animal record could not be found."}
          </p>

          <Link
            href="/animals"
            className="inline-block bg-green-700 text-white px-6 py-3 rounded-xl font-bold hover:bg-green-800"
          >
            Back to Browse Pets
          </Link>
        </div>
      </main>
    );
  }

  const normalizedStatus =
    animal.adoption_status?.toLowerCase();

  const isAvailable = normalizedStatus === "available";

  return (
    <main className="min-h-screen bg-[#fbf8f3] text-slate-900">
      <header className="bg-white border-b border-green-100 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-wrap items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-2xl bg-green-100 flex items-center justify-center text-2xl">
              🐾
            </div>

            <div>
              <p className="text-2xl font-extrabold text-green-900">
                PawConnect
              </p>

              <p className="text-sm text-slate-500">
                Find. Match. Adopt.
              </p>
            </div>
          </Link>

          <nav className="flex flex-wrap items-center gap-6 font-bold text-slate-700">
            <Link
              href="/"
              className="hover:text-green-700"
            >
              Home
            </Link>

            <Link
              href="/animals"
              className="bg-green-50 text-green-800 px-5 py-3 rounded-2xl"
            >
              Browse Pets
            </Link>

            <Link
              href="/ai-assistant"
              className="bg-violet-100 text-violet-800 px-5 py-3 rounded-2xl hover:bg-violet-200"
            >
              ✨ AI Pet Match
            </Link>

            <Link
              href="/#how-it-works"
              className="hover:text-green-700"
            >
              How It Works
            </Link>

            <Link
              href="/shelter-register"
              className="hover:text-green-700"
            >
              For Shelters
            </Link>

            {currentUser ? (
              <div className="relative">
                <button
                  type="button"
                  onClick={() =>
                    setMenuOpen((current) => !current)
                  }
                  className="flex items-center gap-3 border border-green-200 rounded-full px-3 py-2 hover:bg-green-50"
                >
                  <span className="w-10 h-10 rounded-full bg-green-700 text-white flex items-center justify-center font-extrabold">
                    {currentUser.name
                      ?.charAt(0)
                      ?.toUpperCase() || "U"}
                  </span>

                  <span>
                    {currentUser.name || "Profile"}
                  </span>

                  <span>▾</span>
                </button>

                {menuOpen && (
                  <div className="absolute right-0 mt-3 w-56 bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden z-50">
                    <div className="px-4 py-3 border-b border-slate-200">
                      <p className="font-extrabold">
                        {currentUser.name || "User"}
                      </p>

                      <p className="text-sm text-slate-500 truncate">
                        {currentUser.email || ""}
                      </p>
                    </div>

                    <Link
                      href="/my-applications"
                      className="block px-4 py-3 hover:bg-slate-50"
                    >
                      My Applications
                    </Link>

                    <button
                      type="button"
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-3 text-red-600 hover:bg-red-50"
                    >
                      Logout
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Link
                href="/login"
                className="border border-green-200 rounded-full px-5 py-3 hover:bg-green-50"
              >
                Login
              </Link>
            )}
          </nav>
        </div>
      </header>

      <section className="max-w-7xl mx-auto px-6 py-12">
        <Link
          href="/animals"
          className="inline-block mb-7 text-green-700 font-bold hover:underline"
        >
          ← Back to Browse Pets
        </Link>

        <article className="bg-white border border-green-100 rounded-[2rem] shadow-sm overflow-hidden">
          <div className="grid lg:grid-cols-[0.9fr_1.1fr]">
            <AnimalImage
              src={animal.image_url}
              alt={animal.name}
              type={animal.type}
            />

            <div className="p-7 md:p-10">
              <div className="flex flex-wrap items-start justify-between gap-5">
                <div>
                  <span className="inline-block bg-green-100 text-green-800 px-4 py-2 rounded-full font-bold capitalize">
                    {animal.type || "Animal"}
                  </span>

                  <h1 className="text-5xl md:text-6xl font-extrabold mt-5">
                    {animal.name}
                  </h1>

                  <p className="text-xl text-slate-600 mt-2">
                    {animal.breed || "Mixed Breed"}
                  </p>
                </div>

                <StatusBadge status={animal.adoption_status} />
              </div>

              <section className="bg-green-900 text-white rounded-3xl p-6 mt-8">
                <p className="text-green-200 text-sm font-extrabold uppercase mb-3">
                  About {animal.name}
                </p>

                <p className="text-lg leading-8">
                  {animal.description ||
                    `${animal.name} is looking for a responsible and caring home.`}
                </p>
              </section>

              <div className="grid sm:grid-cols-2 gap-4 mt-7">
                <InformationCard
                  icon="🐾"
                  label="Animal Type"
                  value={animal.type}
                />

                <InformationCard
                  icon="🧬"
                  label="Breed"
                  value={animal.breed}
                />

                <InformationCard
                  icon="🎂"
                  label="Age"
                  value={animal.age}
                />

                <InformationCard
                  icon="⚥"
                  label="Gender"
                  value={animal.gender}
                />

                <InformationCard
                  icon="📏"
                  label="Size"
                  value={animal.size}
                />

                <InformationCard
                  icon="💚"
                  label="Temperament"
                  value={animal.temperament}
                />

                <InformationCard
                  icon="📍"
                  label="Location"
                  value={animal.location}
                />

                <InformationCard
                  icon="🩺"
                  label="Health"
                  value={animal.health_status}
                />

                <InformationCard
                  icon="💉"
                  label="Vaccination"
                  value={animal.vaccination_status}
                />

                <InformationCard
                  icon="✂️"
                  label="Sterilization"
                  value={animal.sterilization_status}
                />
              </div>

              <section className="bg-slate-50 border border-slate-200 rounded-3xl p-6 mt-7">
                <p className="text-green-700 text-sm font-extrabold uppercase mb-2">
                  Registered Shelter
                </p>

                <h2 className="text-2xl font-extrabold">
                  {animal.shelter_name ||
                    "Shelter Information"}
                </h2>

                <div className="grid sm:grid-cols-2 gap-4 mt-5">
                  <ContactItem
                    label="Location"
                    value={
                      animal.shelter_location ||
                      animal.location
                    }
                  />

                  <ContactItem
                    label="Phone"
                    value={animal.contact_number}
                  />

                  <ContactItem
                    label="Email"
                    value={animal.shelter_email}
                  />

                  <ContactItem
                    label="Contact Person"
                    value={animal.contact_person}
                  />
                </div>

                {animal.shelter_description && (
                  <p className="text-slate-600 leading-7 mt-5">
                    {animal.shelter_description}
                  </p>
                )}

                <div className="flex flex-wrap gap-3 mt-6">
                  {animal.contact_number && (
                    <a
                      href={`tel:${animal.contact_number}`}
                      className="bg-slate-950 text-white px-6 py-3 rounded-xl font-bold hover:bg-slate-800"
                    >
                      Call Shelter
                    </a>
                  )}

                  {animal.verification_link && (
                    <a
                      href={animal.verification_link}
                      target="_blank"
                      rel="noreferrer"
                      className="border border-green-700 text-green-700 px-6 py-3 rounded-xl font-bold hover:bg-green-50"
                    >
                      Visit Shelter Page
                    </a>
                  )}
                </div>
              </section>

              <div className="mt-7">
                {isAvailable ? (
                  <Link
                    href={
                      currentUser
                        ? `/adoption/${animal.id}`
                        : `/login?redirect=/adoption/${animal.id}`
                    }
                    className="block text-center bg-green-700 text-white py-4 rounded-2xl font-extrabold text-lg hover:bg-green-800"
                  >
                    {currentUser
                      ? `Apply to Adopt ${animal.name}`
                      : "Login to Apply"}
                  </Link>
                ) : (
                  <button
                    type="button"
                    disabled
                    className="w-full bg-slate-300 text-slate-600 py-4 rounded-2xl font-extrabold cursor-not-allowed"
                  >
                    This Animal Is Not Available
                  </button>
                )}
              </div>
            </div>
          </div>
        </article>
      </section>
    </main>
  );
}

function AnimalImage({ src, alt, type }) {
  const [failed, setFailed] = useState(false);

  const fallbackEmoji =
    type?.toLowerCase() === "cat" ? "🐱" : "🐶";

  return (
    <div className="relative h-[520px] overflow-hidden rounded-l-[2rem] bg-slate-100">
      <div className="absolute top-5 left-5 z-10 bg-white/90 backdrop-blur px-4 py-2 rounded-full font-bold text-green-800 shadow-sm">
        🐾 Adoptable Pet
      </div>

      {src && !failed ? (
        <img
  src={src}
  alt={alt}
  onError={() => setFailed(true)}
  className="absolute inset-0 h-full w-full object-cover object-center transition-transform duration-500 hover:scale-105"
/>
      ) : (
        <div className="flex flex-col items-center justify-center">
          <span className="text-9xl">
            {fallbackEmoji}
          </span>

          <p className="text-slate-500 mt-4 font-semibold">
            Image coming soon
          </p>
        </div>
      )}
    </div>
  );
}

function InformationCard({ icon, label, value }) {
  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-4 flex items-center gap-4 shadow-sm">
      <div className="w-12 h-12 rounded-xl bg-green-100 flex items-center justify-center text-xl flex-shrink-0">
        {icon}
      </div>

      <div className="min-w-0">
        <p className="text-sm text-slate-500 font-bold">
          {label}
        </p>

        <p className="font-extrabold capitalize break-words">
          {value || "Not provided"}
        </p>
      </div>
    </div>
  );
}

function ContactItem({ label, value }) {
  return (
    <div>
      <p className="text-sm text-slate-500 font-bold">
        {label}
      </p>

      <p className="font-semibold break-words mt-1">
        {value || "Not provided"}
      </p>
    </div>
  );
}

function StatusBadge({ status }) {
  const normalizedStatus = status?.toLowerCase();

  const styles = {
    available:
      "bg-green-100 border-green-200 text-green-800",
    pending:
      "bg-orange-100 border-orange-200 text-orange-800",
    adopted:
      "bg-violet-100 border-violet-200 text-violet-800",
  };

  return (
    <span
      className={`px-5 py-3 rounded-full border font-extrabold capitalize ${
        styles[normalizedStatus] ||
        "bg-slate-100 border-slate-200 text-slate-700"
      }`}
    >
      {status || "Unknown"}
    </span>
  );
}