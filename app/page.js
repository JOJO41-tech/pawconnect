"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function HomePage() {
  const router = useRouter();

  const [animals, setAnimals] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);

  const [keyword, setKeyword] = useState("");
  const [location, setLocation] = useState("");
  const [animalType, setAnimalType] = useState("all");

  const [mobileMenuOpen, setMobileMenuOpen] =
    useState(false);

  const [profileMenuOpen, setProfileMenuOpen] =
    useState(false);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    loadCurrentUser();
    loadAnimals();
  }, []);

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

  async function loadAnimals() {
    try {
      setLoading(true);
      setError("");

      const response = await fetch("/api/animals", {
        cache: "no-store",
      });

      const contentType =
        response.headers.get("content-type");

      if (!contentType?.includes("application/json")) {
        throw new Error(
          "The animal API returned an invalid response."
        );
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Available animals could not be loaded."
        );
      }

      setAnimals(Array.isArray(data) ? data : []);
    } catch (error) {
      setError(
        error.message ||
          "Available animals could not be loaded."
      );
    } finally {
      setLoading(false);
    }
  }

  const availableAnimals = useMemo(() => {
    return animals.filter(
      (animal) =>
        animal.adoption_status?.toLowerCase() ===
        "available"
    );
  }, [animals]);

  const adoptedAnimals = useMemo(() => {
    return animals.filter(
      (animal) =>
        animal.adoption_status?.toLowerCase() ===
        "adopted"
    );
  }, [animals]);

  const uniqueShelters = useMemo(() => {
    const shelterIds = availableAnimals
      .map((animal) => animal.shelter_id)
      .filter(Boolean);

    return new Set(shelterIds).size;
  }, [availableAnimals]);

  const featuredAnimals = useMemo(() => {
    return availableAnimals.slice(0, 6);
  }, [availableAnimals]);

  const heroAnimals = useMemo(() => {
    return availableAnimals
      .filter((animal) => animal.image_url)
      .slice(0, 3);
  }, [availableAnimals]);

  const locationSuggestions = useMemo(() => {
    const values = availableAnimals
      .map((animal) => animal.location?.trim())
      .filter(Boolean);

    return [...new Set(values)].sort((a, b) =>
      a.localeCompare(b)
    );
  }, [availableAnimals]);

  function handleSearch(event) {
    event.preventDefault();

    const params = new URLSearchParams();

    if (keyword.trim()) {
      params.set("keyword", keyword.trim());
    }

    if (location.trim()) {
      params.set("location", location.trim());
    }

    if (animalType !== "all") {
      params.set("type", animalType);
    }

    const queryString = params.toString();

    router.push(
      queryString
        ? `/animals?${queryString}`
        : "/animals"
    );
  }

  function handleLogout() {
    localStorage.removeItem("user");
    setCurrentUser(null);
    setProfileMenuOpen(false);
    router.push("/");
  }

  return (
    <main className="min-h-screen bg-[#fffaf4] text-slate-900">
      <Header
        currentUser={currentUser}
        mobileMenuOpen={mobileMenuOpen}
        setMobileMenuOpen={setMobileMenuOpen}
        profileMenuOpen={profileMenuOpen}
        setProfileMenuOpen={setProfileMenuOpen}
        onLogout={handleLogout}
      />

      <section className="relative overflow-hidden bg-gradient-to-br from-[#f3fbf5] via-[#fffaf4] to-[#fff1e6]">
        <DecorativePaw className="left-[4%] top-16 rotate-12 text-emerald-100" />
        <DecorativePaw className="right-[7%] top-24 -rotate-12 text-orange-100" />
        <DecorativePaw className="bottom-8 left-[42%] rotate-45 text-emerald-100" />

        <div className="relative mx-auto grid max-w-7xl items-center gap-14 px-6 py-16 lg:grid-cols-[1fr_0.95fr] lg:py-24">
          <div>
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white px-4 py-2 text-sm font-extrabold text-emerald-800 shadow-sm">
              <span>🐾</span>
              <span>Helping pets find the right home</span>
            </div>

            <h1 className="max-w-3xl text-5xl font-black leading-[1.05] tracking-tight text-slate-950 md:text-6xl lg:text-7xl">
              Meet the pet who{" "}
              <span className="text-emerald-700">
                fits your life.
              </span>
            </h1>

            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600 md:text-xl">
              Browse adoptable animals from registered
              shelters or use our AI-assisted matching tool
              to discover pets that suit your home,
              experience, routine, and activity level.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <Link
                href="/ai-assistant"
                className="inline-flex items-center gap-2 rounded-2xl bg-violet-700 px-7 py-4 font-extrabold text-white shadow-lg shadow-violet-200 transition hover:-translate-y-0.5 hover:bg-violet-800"
              >
                <span>✨</span>
                <span>Find My AI Pet Match</span>
              </Link>

              <Link
                href="/animals"
                className="inline-flex items-center gap-2 rounded-2xl border-2 border-emerald-700 bg-white px-7 py-4 font-extrabold text-emerald-800 transition hover:bg-emerald-50"
              >
                <span>Browse All Pets</span>
                <span>→</span>
              </Link>
            </div>

            <div className="mt-9 flex flex-wrap gap-x-8 gap-y-3 text-sm font-bold text-slate-600">
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                  ✓
                </span>
                Registered shelters
              </div>

              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                  ✓
                </span>
                Lifestyle matching
              </div>

              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-100 text-emerald-700">
                  ✓
                </span>
                Direct applications
              </div>
            </div>
          </div>

          <HeroAnimalGallery animals={heroAnimals} />
        </div>
      </section>

      <section className="relative z-10 mx-auto -mt-2 max-w-7xl px-6">
        <div className="grid gap-4 rounded-3xl border border-emerald-100 bg-white p-5 shadow-xl shadow-slate-200/60 sm:grid-cols-3">
          <StatisticCard
            icon="🐾"
            value={availableAnimals.length}
            label="Pets Waiting"
            note="Currently available"
          />

          <StatisticCard
            icon="🏡"
            value={uniqueShelters}
            label="Partner Shelters"
            note="Connected through PawConnect"
          />

          <StatisticCard
            icon="💚"
            value={adoptedAnimals.length}
            label="Happy Adoptions"
            note="Animals who found homes"
          />
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-20">
        <div className="grid items-start gap-8 lg:grid-cols-[0.8fr_1.2fr]">
          <div className="rounded-3xl bg-emerald-950 p-8 text-white lg:sticky lg:top-28">
            <p className="font-extrabold text-emerald-300">
              Start your search
            </p>

            <h2 className="mt-2 text-4xl font-black">
              Find a pet near you
            </h2>

            <p className="mt-4 leading-7 text-emerald-100">
              Search by animal type, location, name, breed,
              or personality.
            </p>

            <form
              onSubmit={handleSearch}
              className="mt-8 space-y-5"
            >
              <div>
                <label className="mb-2 block font-bold">
                  Animal Type
                </label>

                <div className="grid grid-cols-3 gap-3">
                  <TypeButton
                    label="All"
                    value="all"
                    selected={animalType}
                    setSelected={setAnimalType}
                  />

                  <TypeButton
                    label="Dog"
                    value="dog"
                    selected={animalType}
                    setSelected={setAnimalType}
                  />

                  <TypeButton
                    label="Cat"
                    value="cat"
                    selected={animalType}
                    setSelected={setAnimalType}
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block font-bold">
                  Location
                </label>

                <input
                  type="text"
                  value={location}
                  onChange={(event) =>
                    setLocation(event.target.value)
                  }
                  list="homepage-location-options"
                  placeholder="Bangkok, Rangsit..."
                  className="w-full rounded-xl border border-emerald-800 bg-white px-4 py-3.5 text-slate-900 outline-none focus:ring-2 focus:ring-emerald-400"
                />

                <datalist id="homepage-location-options">
                  {locationSuggestions.map((item) => (
                    <option key={item} value={item} />
                  ))}
                </datalist>
              </div>

              <div>
                <label className="mb-2 block font-bold">
                  Keyword
                </label>

                <input
                  type="text"
                  value={keyword}
                  onChange={(event) =>
                    setKeyword(event.target.value)
                  }
                  placeholder="Name, breed, personality..."
                  className="w-full rounded-xl border border-emerald-800 bg-white px-4 py-3.5 text-slate-900 outline-none focus:ring-2 focus:ring-emerald-400"
                />
              </div>

              <button
                type="submit"
                className="w-full rounded-xl bg-orange-400 py-4 font-extrabold text-slate-950 transition hover:bg-orange-300"
              >
                Search Available Pets
              </button>
            </form>
          </div>

          <div>
            <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
              <div>
                <p className="font-extrabold text-emerald-700">
                  Waiting for someone special
                </p>

                <h2 className="mt-2 text-4xl font-black md:text-5xl">
                  Meet our featured pets
                </h2>

                <p className="mt-3 max-w-2xl text-slate-600">
                  Every face has a story. Open a profile to
                  learn about personality, health, and shelter
                  information.
                </p>
              </div>

              <Link
                href="/animals"
                className="font-extrabold text-emerald-700 hover:underline"
              >
                View all pets →
              </Link>
            </div>

            {loading && (
              <div className="rounded-3xl border border-slate-200 bg-white p-12 text-center">
                <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-emerald-100 border-t-emerald-700" />

                <p className="mt-5 font-bold text-slate-600">
                  Loading adoptable pets...
                </p>
              </div>
            )}

            {error && (
              <div className="rounded-2xl border border-red-300 bg-red-50 p-5 font-semibold text-red-800">
                {error}
              </div>
            )}

            {!loading &&
              !error &&
              featuredAnimals.length === 0 && (
                <div className="rounded-3xl border border-dashed border-slate-300 bg-white p-12 text-center">
                  <div className="text-6xl">🐾</div>

                  <h3 className="mt-4 text-2xl font-black">
                    No pets are available yet
                  </h3>

                  <p className="mt-2 text-slate-600">
                    New listings will appear when shelters add
                    animals.
                  </p>
                </div>
              )}

            {!loading &&
              !error &&
              featuredAnimals.length > 0 && (
                <div className="grid gap-6 sm:grid-cols-2">
                  {featuredAnimals.map((animal) => (
                    <FeaturedAnimalCard
                      key={animal.id}
                      animal={animal}
                    />
                  ))}
                </div>
              )}
          </div>
        </div>
      </section>

      <section className="overflow-hidden bg-violet-950 text-white">
        <div className="mx-auto grid max-w-7xl items-center gap-12 px-6 py-20 lg:grid-cols-[1fr_0.9fr]">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full bg-violet-800 px-4 py-2 text-sm font-extrabold text-violet-100">
              <span>✨</span>
              AI-assisted pet matching
            </div>

            <h2 className="mt-5 text-4xl font-black md:text-5xl">
              Unsure which pet fits your lifestyle?
            </h2>

            <p className="mt-5 max-w-2xl text-lg leading-8 text-violet-100">
              Answer seven questions about your home,
              experience, available time, and activity level.
              PawConnect compares your answers with available
              pets and explains why each recommendation may
              suit you.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <Link
                href="/ai-assistant"
                className="rounded-2xl bg-white px-7 py-4 font-extrabold text-violet-900 transition hover:bg-violet-100"
              >
                Try AI Pet Matching
              </Link>

              <Link
                href="/animals"
                className="rounded-2xl border border-violet-400 px-7 py-4 font-bold text-white hover:bg-violet-900"
              >
                Browse Manually
              </Link>
            </div>
          </div>

          <div className="rounded-3xl border border-violet-700 bg-violet-900/70 p-6 shadow-2xl">
            <div className="rounded-2xl bg-white p-6 text-slate-900">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-extrabold text-violet-700">
                    Example Recommendation
                  </p>

                  <h3 className="mt-1 text-3xl font-black">
                    Lifestyle Match
                  </h3>
                </div>

                <div className="rounded-2xl bg-emerald-100 px-4 py-3 text-center text-emerald-800">
                  <p className="text-3xl font-black">92%</p>
                  <p className="text-xs font-extrabold">
                    Excellent
                  </p>
                </div>
              </div>

              <div className="mt-6 h-3 overflow-hidden rounded-full bg-slate-200">
                <div className="h-full w-[92%] rounded-full bg-emerald-700" />
              </div>

              <div className="mt-6 space-y-3">
                <AiReason text="Suitable for your home type" />
                <AiReason text="Matches your activity level" />
                <AiReason text="Daily attention needs are compatible" />
              </div>

              <div className="mt-6 rounded-2xl border border-violet-200 bg-violet-50 p-4">
                <p className="font-extrabold text-violet-900">
                  🤖 AI Explanation
                </p>

                <p className="mt-2 text-sm leading-6 text-slate-600">
                  This pet may be a strong match because its
                  energy level and care needs align with your
                  routine.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        id="how-it-works"
        className="mx-auto max-w-7xl px-6 py-20"
      >
        <div className="mx-auto max-w-3xl text-center">
          <p className="font-extrabold text-emerald-700">
            A clearer path to adoption
          </p>

          <h2 className="mt-2 text-4xl font-black md:text-5xl">
            How PawConnect works
          </h2>

          <p className="mt-4 text-lg text-slate-600">
            From discovering a pet to shelter review, every
            step happens in one connected platform.
          </p>
        </div>

        <div className="mt-12 grid gap-6 md:grid-cols-4">
          <StepCard
            number="1"
            emoji="🔎"
            title="Discover"
            text="Browse available pets by type, breed, age, gender, and location."
          />

          <StepCard
            number="2"
            emoji="✨"
            title="Match"
            text="Use AI-assisted matching to compare pets with your lifestyle."
          />

          <StepCard
            number="3"
            emoji="📝"
            title="Apply"
            text="Submit an adoption request with your information and reason."
          />

          <StepCard
            number="4"
            emoji="🏡"
            title="Shelter Review"
            text="The shelter reviews your request and decides the next steps."
          />
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 pb-20">
        <div className="relative overflow-hidden rounded-[2.5rem] bg-gradient-to-r from-orange-100 via-amber-50 to-emerald-100 p-8 md:p-12">
          <DecorativePaw className="-right-8 -top-8 rotate-12 text-white/60" />

          <div className="relative grid items-center gap-8 lg:grid-cols-[1fr_auto]">
            <div>
              <p className="font-extrabold text-emerald-700">
                For shelters and rescue organizations
              </p>

              <h2 className="mt-2 max-w-4xl text-4xl font-black md:text-5xl">
                Give every animal a better chance to be seen.
              </h2>

              <p className="mt-4 max-w-3xl text-lg leading-8 text-slate-600">
                Create animal profiles, manage adoption
                requests, review compatibility information, and
                keep pet availability updated from one shelter
                dashboard.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <Link
                href="/shelter-register"
                className="rounded-2xl bg-emerald-700 px-7 py-4 font-extrabold text-white hover:bg-emerald-800"
              >
                Join as Shelter
              </Link>

              <Link
                href="/shelter-login"
                className="rounded-2xl border-2 border-emerald-700 bg-white px-7 py-4 font-bold text-emerald-800 hover:bg-emerald-50"
              >
                Shelter Login
              </Link>
            </div>
          </div>
        </div>
      </section>

      <footer className="bg-emerald-950 text-emerald-50">
        <div className="mx-auto grid max-w-7xl gap-10 px-6 py-12 md:grid-cols-[1.2fr_0.8fr_0.8fr]">
          <div>
            <Link
              href="/"
              className="inline-flex items-center gap-3"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-800 text-2xl">
                🐾
              </div>

              <div>
                <p className="text-2xl font-black">
                  PawConnect
                </p>

                <p className="text-sm text-emerald-300">
                  Find. Match. Adopt.
                </p>
              </div>
            </Link>

            <p className="mt-5 max-w-md leading-7 text-emerald-200">
              A web-based platform connecting adopters with
              shelter animals through searchable listings,
              adoption applications, and AI-assisted matching.
            </p>
          </div>

          <div>
            <h3 className="font-black text-white">
              For Adopters
            </h3>

            <div className="mt-4 space-y-3">
              <FooterLink href="/animals">
                Browse Pets
              </FooterLink>

              <FooterLink href="/ai-assistant">
                AI Pet Match
              </FooterLink>

              <FooterLink href="/my-applications">
                My Applications
              </FooterLink>
            </div>
          </div>

          <div>
            <h3 className="font-black text-white">
              For Shelters
            </h3>

            <div className="mt-4 space-y-3">
              <FooterLink href="/shelter-register">
                Register Shelter
              </FooterLink>

              <FooterLink href="/shelter-login">
                Shelter Login
              </FooterLink>

              <FooterLink href="/animals">
                View Listings
              </FooterLink>
            </div>
          </div>
        </div>

        <div className="border-t border-emerald-900">
          <div className="mx-auto max-w-7xl px-6 py-5 text-sm text-emerald-300">
            PawConnect Pet Adoption and Shelter Management
            System
          </div>
        </div>
      </footer>
    </main>
  );
}

function Header({
  currentUser,
  mobileMenuOpen,
  setMobileMenuOpen,
  profileMenuOpen,
  setProfileMenuOpen,
  onLogout,
}) {
  const initial =
    currentUser?.name?.charAt(0)?.toUpperCase() || "U";

  return (
    <header className="sticky top-0 z-50 border-b border-emerald-100 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-5 px-6 py-4">
        <Link
          href="/"
          className="flex items-center gap-3"
        >
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-100 text-2xl">
            🐾
          </div>

          <div>
            <p className="text-xl font-black text-emerald-900">
              PawConnect
            </p>

            <p className="text-xs font-bold text-slate-500">
              Find. Match. Adopt.
            </p>
          </div>
        </Link>

        <nav className="hidden items-center gap-7 font-bold lg:flex">
          <Link
            href="/animals"
            className="text-slate-700 hover:text-emerald-700"
          >
            Browse Pets
          </Link>

          <Link
            href="/ai-assistant"
            className="rounded-full bg-violet-100 px-5 py-2.5 font-extrabold text-violet-800 transition hover:bg-violet-200"
          >
            ✨ AI Pet Match
          </Link>

          <Link
            href="/#how-it-works"
            className="text-slate-700 hover:text-emerald-700"
          >
            How It Works
          </Link>

          <Link
            href="/shelter-login"
            className="text-slate-700 hover:text-emerald-700"
          >
            For Shelters
          </Link>

          {currentUser ? (
            <div className="relative">
              <button
                type="button"
                onClick={() =>
                  setProfileMenuOpen((current) => !current)
                }
                className="flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 py-1.5 pl-1.5 pr-3 text-emerald-900"
              >
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-700 font-black text-white">
                  {initial}
                </span>

                <span>
                  {currentUser.name || "Profile"}
                </span>

                <span className="text-xs">▾</span>
              </button>

              {profileMenuOpen && (
                <div className="absolute right-0 mt-3 w-64 overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl">
                  <div className="border-b border-slate-200 px-5 py-4">
                    <p className="font-black text-slate-900">
                      {currentUser.name || "User"}
                    </p>

                    <p className="mt-1 truncate text-sm text-slate-500">
                      {currentUser.email || ""}
                    </p>
                  </div>

                  <Link
                    href="/dashboard"
                    className="block px-5 py-3 hover:bg-slate-50"
                  >
                    User Dashboard
                  </Link>

                  <Link
                    href="/my-applications"
                    className="block px-5 py-3 hover:bg-slate-50"
                  >
                    My Applications
                  </Link>

                  <button
                    type="button"
                    onClick={onLogout}
                    className="w-full px-5 py-3 text-left font-bold text-red-600 hover:bg-red-50"
                  >
                    Logout
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Link
                href="/login"
                className="text-slate-700 hover:text-emerald-700"
              >
                Login
              </Link>

              <Link
                href="/register"
                className="rounded-xl bg-emerald-700 px-5 py-3 font-extrabold text-white hover:bg-emerald-800"
              >
                Create Account
              </Link>
            </>
          )}
        </nav>

        <button
          type="button"
          onClick={() =>
            setMobileMenuOpen((current) => !current)
          }
          className="flex h-11 w-11 items-center justify-center rounded-xl border border-slate-200 text-xl lg:hidden"
          aria-label="Open navigation"
        >
          {mobileMenuOpen ? "✕" : "☰"}
        </button>
      </div>

      {mobileMenuOpen && (
        <div className="border-t border-slate-200 bg-white px-6 py-5 lg:hidden">
          <div className="space-y-2 font-bold">
            <MobileNavLink href="/animals">
              Browse Pets
            </MobileNavLink>

            <MobileNavLink href="/ai-assistant">
              ✨ AI Pet Match
            </MobileNavLink>

            <MobileNavLink href="/#how-it-works">
              How It Works
            </MobileNavLink>

            <MobileNavLink href="/shelter-login">
              For Shelters
            </MobileNavLink>

            {currentUser ? (
              <>
                <MobileNavLink href="/dashboard">
                  User Dashboard
                </MobileNavLink>

                <MobileNavLink href="/my-applications">
                  My Applications
                </MobileNavLink>

                <button
                  type="button"
                  onClick={onLogout}
                  className="block w-full rounded-xl px-4 py-3 text-left text-red-600 hover:bg-red-50"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <MobileNavLink href="/login">
                  Login
                </MobileNavLink>

                <MobileNavLink href="/register">
                  Create Account
                </MobileNavLink>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

function HeroAnimalGallery({ animals }) {
  const mainAnimal = animals[0];
  const secondAnimal = animals[1];
  const thirdAnimal = animals[2];

  return (
    <div className="relative min-h-[520px]">
      <div className="absolute left-0 top-8 h-[430px] w-[78%] overflow-hidden rounded-[2.5rem] border-8 border-white bg-emerald-100 shadow-2xl">
        <HeroImage
          animal={mainAnimal}
          fallbackEmoji="🐶"
        />
      </div>

      <div className="absolute bottom-0 right-0 h-[250px] w-[48%] overflow-hidden rounded-[2rem] border-8 border-white bg-orange-100 shadow-2xl">
        <HeroImage
          animal={secondAnimal}
          fallbackEmoji="🐱"
        />
      </div>

      <div className="absolute right-6 top-0 h-[160px] w-[160px] overflow-hidden rounded-full border-8 border-white bg-violet-100 shadow-xl">
        <HeroImage
          animal={thirdAnimal}
          fallbackEmoji="🐾"
        />
      </div>

      <div className="absolute bottom-12 left-5 rounded-2xl border border-emerald-100 bg-white p-4 shadow-xl">
        <p className="text-sm font-bold text-slate-500">
          Ready to meet someone?
        </p>

        <p className="mt-1 font-black text-emerald-800">
          {mainAnimal?.name
            ? `${mainAnimal.name} is waiting 🐾`
            : "A new friend is waiting 🐾"}
        </p>
      </div>
    </div>
  );
}

function HeroImage({ animal, fallbackEmoji }) {
  const [failed, setFailed] = useState(false);

  if (!animal?.image_url || failed) {
    return (
      <div className="flex h-full w-full items-center justify-center text-8xl">
        {fallbackEmoji}
      </div>
    );
  }

  return (
    <img
      src={animal.image_url}
      alt={animal.name || "Adoptable animal"}
      onError={() => setFailed(true)}
      className="h-full w-full object-cover"
    />
  );
}

function TypeButton({
  label,
  value,
  selected,
  setSelected,
}) {
  const active = selected === value;

  return (
    <button
      type="button"
      onClick={() => setSelected(value)}
      className={`rounded-xl border py-3 font-bold transition ${
        active
          ? "border-orange-400 bg-orange-400 text-slate-950"
          : "border-emerald-700 bg-emerald-900 text-white hover:bg-emerald-800"
      }`}
    >
      {label}
    </button>
  );
}

function StatisticCard({
  icon,
  value,
  label,
  note,
}) {
  return (
    <div className="flex items-center gap-4 rounded-2xl p-4">
      <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-emerald-100 text-2xl">
        {icon}
      </div>

      <div>
        <p className="text-3xl font-black text-emerald-900">
          {value}
        </p>

        <p className="font-extrabold text-slate-900">
          {label}
        </p>

        <p className="text-sm text-slate-500">
          {note}
        </p>
      </div>
    </div>
  );
}

function FeaturedAnimalCard({ animal }) {
  return (
    <article className="group overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-1 hover:shadow-xl">
      <div className="relative">
        <AnimalImage
          src={animal.image_url}
          alt={animal.name}
          type={animal.type}
        />

        <span className="absolute left-4 top-4 rounded-full bg-white/95 px-3 py-1.5 text-sm font-extrabold text-emerald-800 shadow">
          Available
        </span>
      </div>

      <div className="p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-2xl font-black text-slate-950">
              {animal.name || "Unnamed Pet"}
            </h3>

            <p className="mt-1 capitalize text-slate-600">
              {animal.type || "Pet"} •{" "}
              {animal.breed || "Mixed breed"}
            </p>
          </div>

          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-orange-100 text-xl">
            {animal.type?.toLowerCase() === "cat"
              ? "🐱"
              : "🐶"}
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3">
          <PetInfo
            label="Age"
            value={animal.age || "Not provided"}
          />

          <PetInfo
            label="Gender"
            value={animal.gender || "Not provided"}
          />

          <PetInfo
            label="Location"
            value={
              animal.location || "Not provided"
            }
            full
          />
        </div>

        <Link
          href={`/animals/${animal.id}`}
          className="mt-5 flex items-center justify-center gap-2 rounded-xl bg-emerald-700 py-3.5 font-extrabold text-white transition group-hover:bg-emerald-800"
        >
          Meet {animal.name || "This Pet"}
          <span>→</span>
        </Link>
      </div>
    </article>
  );
}

function AnimalImage({ src, alt, type }) {
  const [failed, setFailed] = useState(false);

  const fallbackEmoji =
    type?.toLowerCase() === "cat"
      ? "🐱"
      : "🐶";

  if (!src || failed) {
    return (
      <div className="flex h-64 w-full flex-col items-center justify-center bg-gradient-to-br from-orange-100 to-emerald-100">
        <span className="text-8xl">
          {fallbackEmoji}
        </span>

        <p className="mt-3 font-bold text-slate-500">
          Photo coming soon
        </p>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      onError={() => setFailed(true)}
      className="h-64 w-full object-cover transition duration-500 group-hover:scale-105"
    />
  );
}

function PetInfo({ label, value, full }) {
  return (
    <div
      className={`rounded-xl bg-slate-50 p-3 ${
        full ? "col-span-2" : ""
      }`}
    >
      <p className="text-xs font-extrabold uppercase tracking-wide text-slate-400">
        {label}
      </p>

      <p className="mt-1 font-bold capitalize text-slate-700">
        {value}
      </p>
    </div>
  );
}

function AiReason({ text }) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-emerald-50 px-4 py-3">
      <span className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-700 text-sm font-black text-white">
        ✓
      </span>

      <span className="font-bold text-slate-700">
        {text}
      </span>
    </div>
  );
}

function StepCard({
  number,
  emoji,
  title,
  text,
}) {
  return (
    <div className="relative rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-100 text-2xl">
          {emoji}
        </div>

        <span className="text-4xl font-black text-slate-100">
          {number}
        </span>
      </div>

      <h3 className="mt-5 text-xl font-black">
        {title}
      </h3>

      <p className="mt-2 leading-7 text-slate-600">
        {text}
      </p>
    </div>
  );
}

function DecorativePaw({ className }) {
  return (
    <div
      className={`pointer-events-none absolute select-none text-8xl opacity-70 ${className}`}
    >
      🐾
    </div>
  );
}

function MobileNavLink({
  href,
  children,
}) {
  return (
    <Link
      href={href}
      className="block rounded-xl px-4 py-3 text-slate-700 hover:bg-emerald-50 hover:text-emerald-800"
    >
      {children}
    </Link>
  );
}

function FooterLink({
  href,
  children,
}) {
  return (
    <Link
      href={href}
      className="block text-emerald-200 hover:text-white"
    >
      {children}
    </Link>
  );
}