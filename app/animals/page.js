"use client";

import {
  Suspense,
  useEffect,
  useMemo,
  useState,
} from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import Navbar from "@/components/Navbar";

const PETS_PER_PAGE = 9;

const initialFilters = {
  keyword: "",
  location: "",
  type: "all",
  breed: "all",
  gender: "all",
  size: "all",
  ageGroup: "all",
};

function AnimalsPageContent()  {
  const searchParams = useSearchParams();

  const [animals, setAnimals] = useState([]);
  const [filters, setFilters] =
    useState(initialFilters);

  const [sortOption, setSortOption] =
    useState("newest");

  const [
    mobileFiltersOpen,
    setMobileFiltersOpen,
  ] = useState(false);

  const [currentPage, setCurrentPage] =
    useState(1);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] = useState("");

  useEffect(() => {
    const queryFilters = {
      keyword:
        searchParams.get("keyword") || "",
      location:
        searchParams.get("location") || "",
      type:
        searchParams.get("type") || "all",
      breed:
        searchParams.get("breed") || "all",
      gender:
        searchParams.get("gender") || "all",
      size:
        searchParams.get("size") || "all",
      ageGroup:
        searchParams.get("age") || "all",
    };

    setFilters(queryFilters);
    setCurrentPage(1);
  }, [searchParams]);

  useEffect(() => {
    loadAnimals();
  }, []);

  useEffect(() => {
    setCurrentPage(1);
  }, [filters, sortOption]);

  async function loadAnimals() {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        "/api/animals",
        {
          cache: "no-store",
        }
      );

      const contentType =
        response.headers.get(
          "content-type"
        );

      if (
        !contentType?.includes(
          "application/json"
        )
      ) {
        throw new Error(
          "The animal API returned an invalid response."
        );
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Animals could not be loaded."
        );
      }

      setAnimals(
        Array.isArray(data) ? data : []
      );
    } catch (error) {
      setError(
        error.message ||
          "Animals could not be loaded."
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

  const dogCount = useMemo(() => {
    return availableAnimals.filter(
      (animal) =>
        animal.type?.toLowerCase() ===
        "dog"
    ).length;
  }, [availableAnimals]);

  const catCount = useMemo(() => {
    return availableAnimals.filter(
      (animal) =>
        animal.type?.toLowerCase() ===
        "cat"
    ).length;
  }, [availableAnimals]);

  const breedOptions = useMemo(() => {
    const breeds = availableAnimals
      .map((animal) =>
        animal.breed?.trim()
      )
      .filter(Boolean);

    return [...new Set(breeds)].sort(
      (a, b) => a.localeCompare(b)
    );
  }, [availableAnimals]);

  const locationOptions = useMemo(() => {
    const locations = availableAnimals
      .map((animal) =>
        animal.location?.trim()
      )
      .filter(Boolean);

    return [...new Set(locations)].sort(
      (a, b) => a.localeCompare(b)
    );
  }, [availableAnimals]);

  const filteredAnimals = useMemo(() => {
    const filtered =
      availableAnimals.filter((animal) => {
        const searchableText = [
          animal.name,
          animal.type,
          animal.breed,
          animal.temperament,
          animal.description,
          animal.location,
        ]
          .filter(Boolean)
          .join(" ")
          .toLowerCase();

        const keywordMatch =
          !filters.keyword.trim() ||
          searchableText.includes(
            filters.keyword
              .trim()
              .toLowerCase()
          );

        const locationMatch =
          !filters.location.trim() ||
          animal.location
            ?.toLowerCase()
            .includes(
              filters.location
                .trim()
                .toLowerCase()
            );

        const typeMatch =
          filters.type === "all" ||
          animal.type?.toLowerCase() ===
            filters.type;

        const breedMatch =
          filters.breed === "all" ||
          animal.breed?.toLowerCase() ===
            filters.breed.toLowerCase();

        const genderMatch =
          filters.gender === "all" ||
          animal.gender?.toLowerCase() ===
            filters.gender;

        const sizeMatch =
          filters.size === "all" ||
          animal.size?.toLowerCase() ===
            filters.size;

        const ageMatch = matchesAgeGroup(
          animal.age,
          filters.ageGroup
        );

        return (
          keywordMatch &&
          locationMatch &&
          typeMatch &&
          breedMatch &&
          genderMatch &&
          sizeMatch &&
          ageMatch
        );
      });

    return [...filtered].sort((a, b) => {
      if (sortOption === "name") {
        return (
          a.name || ""
        ).localeCompare(b.name || "");
      }

      if (
        sortOption === "youngest"
      ) {
        return (
          extractAgeNumber(a.age) -
          extractAgeNumber(b.age)
        );
      }

      if (
        sortOption === "oldest"
      ) {
        return (
          extractAgeNumber(b.age) -
          extractAgeNumber(a.age)
        );
      }

      return (
        Number(b.id || 0) -
        Number(a.id || 0)
      );
    });
  }, [
    availableAnimals,
    filters,
    sortOption,
  ]);

  const totalPages = Math.max(
    1,
    Math.ceil(
      filteredAnimals.length /
        PETS_PER_PAGE
    )
  );

  const paginatedAnimals = useMemo(() => {
    const startIndex =
      (currentPage - 1) *
      PETS_PER_PAGE;

    return filteredAnimals.slice(
      startIndex,
      startIndex + PETS_PER_PAGE
    );
  }, [
    filteredAnimals,
    currentPage,
  ]);

  const firstVisiblePet =
    filteredAnimals.length === 0
      ? 0
      : (currentPage - 1) *
          PETS_PER_PAGE +
        1;

  const lastVisiblePet = Math.min(
    currentPage * PETS_PER_PAGE,
    filteredAnimals.length
  );

  const activeFilterCount =
    useMemo(() => {
      let count = 0;

      if (filters.keyword.trim()) {
        count += 1;
      }

      if (filters.location.trim()) {
        count += 1;
      }

      if (filters.type !== "all") {
        count += 1;
      }

      if (filters.breed !== "all") {
        count += 1;
      }

      if (filters.gender !== "all") {
        count += 1;
      }

      if (filters.size !== "all") {
        count += 1;
      }

      if (
        filters.ageGroup !== "all"
      ) {
        count += 1;
      }

      return count;
    }, [filters]);

  function handleFilterChange(event) {
    const { name, value } =
      event.target;

    setFilters((currentFilters) => ({
      ...currentFilters,
      [name]: value,
    }));
  }

  function setType(type) {
    setFilters((currentFilters) => ({
      ...currentFilters,
      type,
    }));
  }

  function clearFilters() {
    setFilters(initialFilters);
    setSortOption("newest");
    setCurrentPage(1);
  }

  function changePage(page) {
    const safePage = Math.min(
      Math.max(page, 1),
      totalPages
    );

    setCurrentPage(safePage);

    window.scrollTo({
      top:
        document.getElementById(
          "available-pets"
        )?.offsetTop || 0,
      behavior: "smooth",
    });
  }

  return (
    <main className="min-h-screen bg-[#fffaf4] text-slate-900">
      <Navbar />

      <section className="relative overflow-hidden bg-gradient-to-br from-emerald-950 via-emerald-900 to-slate-950 text-white">
        <DecorativePaw className="left-[4%] top-12 rotate-12 text-emerald-800" />

        <DecorativePaw className="right-[6%] top-10 -rotate-12 text-emerald-800" />

        <div className="relative mx-auto grid max-w-7xl items-center gap-10 px-6 py-14 lg:grid-cols-[1fr_auto] lg:py-20">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-700 bg-emerald-900 px-4 py-2 text-sm font-extrabold text-emerald-200">
              <span>🐾</span>

              Adoptable pets from
              registered shelters
            </div>

            <h1 className="mt-5 text-5xl font-black leading-tight md:text-6xl">
              Find someone waiting for{" "}
              <span className="text-orange-300">
                a loving home.
              </span>
            </h1>

            <p className="mt-5 max-w-3xl text-lg leading-8 text-emerald-100">
              Search available dogs and
              cats by breed, location,
              age, size, gender, and
              personality. Open a profile
              to learn more or use
              AI-assisted matching to
              discover pets suited to your
              lifestyle.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <Link
                href="/ai-assistant"
                className="rounded-2xl bg-violet-600 px-7 py-4 font-extrabold text-white shadow-lg transition hover:-translate-y-0.5 hover:bg-violet-700"
              >
                ✨ Find My AI Pet Match
              </Link>

              <a
                href="#available-pets"
                className="rounded-2xl border border-emerald-500 px-7 py-4 font-extrabold text-white hover:bg-emerald-900"
              >
                Browse Available Pets
              </a>
            </div>
          </div>

          <div className="hidden rounded-[2rem] border border-emerald-700 bg-emerald-900/70 p-6 shadow-2xl lg:block">
            <div className="grid grid-cols-2 gap-4">
              <HeroMiniCard
                emoji="🐶"
                value={dogCount}
                label="Dogs"
              />

              <HeroMiniCard
                emoji="🐱"
                value={catCount}
                label="Cats"
              />

              <div className="col-span-2 rounded-2xl bg-white p-5 text-slate-900">
                <p className="text-sm font-bold text-slate-500">
                  Available now
                </p>

                <p className="mt-1 text-4xl font-black text-emerald-800">
                  {
                    availableAnimals.length
                  }
                </p>

                <p className="mt-1 text-sm text-slate-600">
                  animals waiting to meet
                  adopters
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section
        id="available-pets"
        className="mx-auto max-w-7xl px-6 py-12"
      >
        <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
          <div>
            <p className="font-extrabold text-emerald-700">
              Waiting for a home
            </p>

            <h2 className="mt-2 text-4xl font-black md:text-5xl">
              Browse adoptable pets
            </h2>

            <p className="mt-3 text-slate-600">
              {loading
                ? "Loading available animals..."
                : filteredAnimals.length >
                    0
                ? `Showing ${firstVisiblePet}-${lastVisiblePet} of ${filteredAnimals.length} pets`
                : "No pets found"}
            </p>
          </div>

          <button
            type="button"
            onClick={() =>
              setMobileFiltersOpen(
                (current) => !current
              )
            }
            className="flex items-center gap-2 rounded-xl border border-emerald-300 bg-white px-5 py-3 font-extrabold text-emerald-800 shadow-sm lg:hidden"
          >
            <span>⚙</span>
            Filters

            {activeFilterCount > 0 && (
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-700 text-xs text-white">
                {activeFilterCount}
              </span>
            )}
          </button>
        </div>

        <div className="grid items-start gap-8 lg:grid-cols-[300px_1fr]">
          <aside
            className={`rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm ${
              mobileFiltersOpen
                ? "block"
                : "hidden lg:block"
            }`}
          >
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-extrabold uppercase tracking-wide text-emerald-700">
                  Search and Filter
                </p>

                <h3 className="mt-1 text-2xl font-black">
                  Find your match
                </h3>
              </div>

              {activeFilterCount >
                0 && (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="text-sm font-extrabold text-red-600 hover:underline"
                >
                  Clear
                </button>
              )}
            </div>

            <div className="mt-7 space-y-6">
              <FilterGroup label="Search">
                <input
                  type="text"
                  name="keyword"
                  value={
                    filters.keyword
                  }
                  onChange={
                    handleFilterChange
                  }
                  placeholder="Name, breed, personality..."
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                />
              </FilterGroup>

              <FilterGroup label="Animal Type">
                <div className="grid grid-cols-3 gap-2">
                  <TypeFilterButton
                    label="All"
                    value="all"
                    selected={
                      filters.type
                    }
                    onSelect={setType}
                  />

                  <TypeFilterButton
                    label="Dog"
                    value="dog"
                    selected={
                      filters.type
                    }
                    onSelect={setType}
                  />

                  <TypeFilterButton
                    label="Cat"
                    value="cat"
                    selected={
                      filters.type
                    }
                    onSelect={setType}
                  />
                </div>
              </FilterGroup>

              <FilterGroup label="Location">
                <input
                  type="text"
                  name="location"
                  value={
                    filters.location
                  }
                  onChange={
                    handleFilterChange
                  }
                  list="animal-location-options"
                  placeholder="Bangkok, Rangsit..."
                  className="w-full rounded-xl border border-slate-300 px-4 py-3 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                />

                <datalist id="animal-location-options">
                  {locationOptions.map(
                    (location) => (
                      <option
                        key={
                          location
                        }
                        value={
                          location
                        }
                      />
                    )
                  )}
                </datalist>
              </FilterGroup>

              <FilterGroup label="Breed">
                <select
                  name="breed"
                  value={
                    filters.breed
                  }
                  onChange={
                    handleFilterChange
                  }
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                >
                  <option value="all">
                    All breeds
                  </option>

                  {breedOptions.map(
                    (breed) => (
                      <option
                        key={breed}
                        value={breed}
                      >
                        {breed}
                      </option>
                    )
                  )}
                </select>
              </FilterGroup>

              <FilterGroup label="Gender">
                <select
                  name="gender"
                  value={
                    filters.gender
                  }
                  onChange={
                    handleFilterChange
                  }
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                >
                  <option value="all">
                    Any gender
                  </option>

                  <option value="male">
                    Male
                  </option>

                  <option value="female">
                    Female
                  </option>
                </select>
              </FilterGroup>

              <FilterGroup label="Size">
                <select
                  name="size"
                  value={filters.size}
                  onChange={
                    handleFilterChange
                  }
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                >
                  <option value="all">
                    Any size
                  </option>

                  <option value="small">
                    Small
                  </option>

                  <option value="medium">
                    Medium
                  </option>

                  <option value="large">
                    Large
                  </option>

                  <option value="extra large">
                    Extra Large
                  </option>
                </select>
              </FilterGroup>

              <FilterGroup label="Age">
                <select
                  name="ageGroup"
                  value={
                    filters.ageGroup
                  }
                  onChange={
                    handleFilterChange
                  }
                  className="w-full rounded-xl border border-slate-300 bg-white px-4 py-3 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                >
                  <option value="all">
                    Any age
                  </option>

                  <option value="young">
                    Young
                  </option>

                  <option value="adult">
                    Adult
                  </option>

                  <option value="senior">
                    Senior
                  </option>
                </select>
              </FilterGroup>

              <button
                type="button"
                onClick={() =>
                  setMobileFiltersOpen(
                    false
                  )
                }
                className="w-full rounded-xl bg-emerald-700 py-3.5 font-extrabold text-white hover:bg-emerald-800 lg:hidden"
              >
                Show{" "}
                {
                  filteredAnimals.length
                }{" "}
                Pets
              </button>
            </div>
          </aside>

          <div>
            <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4">
              <div className="flex flex-wrap gap-2">
                {filters.type !==
                  "all" && (
                  <ActiveFilter
                    label={`Type: ${capitalize(
                      filters.type
                    )}`}
                    onRemove={() =>
                      setType("all")
                    }
                  />
                )}

                {filters.location && (
                  <ActiveFilter
                    label={`Location: ${filters.location}`}
                    onRemove={() =>
                      setFilters(
                        (current) => ({
                          ...current,
                          location: "",
                        })
                      )
                    }
                  />
                )}

                {filters.breed !==
                  "all" && (
                  <ActiveFilter
                    label={`Breed: ${filters.breed}`}
                    onRemove={() =>
                      setFilters(
                        (current) => ({
                          ...current,
                          breed: "all",
                        })
                      )
                    }
                  />
                )}

                {filters.gender !==
                  "all" && (
                  <ActiveFilter
                    label={`Gender: ${capitalize(
                      filters.gender
                    )}`}
                    onRemove={() =>
                      setFilters(
                        (current) => ({
                          ...current,
                          gender:
                            "all",
                        })
                      )
                    }
                  />
                )}

                {filters.size !==
                  "all" && (
                  <ActiveFilter
                    label={`Size: ${capitalize(
                      filters.size
                    )}`}
                    onRemove={() =>
                      setFilters(
                        (current) => ({
                          ...current,
                          size: "all",
                        })
                      )
                    }
                  />
                )}

                {filters.ageGroup !==
                  "all" && (
                  <ActiveFilter
                    label={`Age: ${capitalize(
                      filters.ageGroup
                    )}`}
                    onRemove={() =>
                      setFilters(
                        (current) => ({
                          ...current,
                          ageGroup:
                            "all",
                        })
                      )
                    }
                  />
                )}

                {filters.keyword && (
                  <ActiveFilter
                    label={`Search: ${filters.keyword}`}
                    onRemove={() =>
                      setFilters(
                        (current) => ({
                          ...current,
                          keyword: "",
                        })
                      )
                    }
                  />
                )}

                {activeFilterCount ===
                  0 && (
                  <p className="px-2 text-sm font-bold text-slate-500">
                    Showing all
                    available pets
                  </p>
                )}
              </div>

              <div className="flex items-center gap-3">
                <label
                  htmlFor="sort"
                  className="text-sm font-bold text-slate-500"
                >
                  Sort:
                </label>

                <select
                  id="sort"
                  value={sortOption}
                  onChange={(event) =>
                    setSortOption(
                      event.target.value
                    )
                  }
                  className="rounded-xl border border-slate-300 bg-white px-4 py-2.5 font-bold outline-none focus:border-emerald-500"
                >
                  <option value="newest">
                    Newest first
                  </option>

                  <option value="name">
                    Name A-Z
                  </option>

                  <option value="youngest">
                    Youngest first
                  </option>

                  <option value="oldest">
                    Oldest first
                  </option>
                </select>
              </div>
            </div>

            {loading && <LoadingGrid />}

            {error && (
              <div className="rounded-3xl border border-red-200 bg-red-50 p-8 text-center">
                <div className="text-5xl">
                  ⚠️
                </div>

                <h3 className="mt-4 text-2xl font-black text-red-700">
                  Animals could not be
                  loaded
                </h3>

                <p className="mt-2 text-red-600">
                  {error}
                </p>

                <button
                  type="button"
                  onClick={loadAnimals}
                  className="mt-6 rounded-xl bg-red-700 px-6 py-3 font-extrabold text-white hover:bg-red-800"
                >
                  Try Again
                </button>
              </div>
            )}

            {!loading &&
              !error &&
              filteredAnimals.length ===
                0 && (
                <NoAnimalsFound
                  clearFilters={
                    clearFilters
                  }
                />
              )}

            {!loading &&
              !error &&
              paginatedAnimals.length >
                0 && (
                <>
                  <div className="grid auto-rows-fr gap-6 sm:grid-cols-2 xl:grid-cols-3">
                    {paginatedAnimals.map(
                      (animal) => (
                        <AnimalCard
                          key={
                            animal.id
                          }
                          animal={
                            animal
                          }
                        />
                      )
                    )}
                  </div>

                  {totalPages > 1 && (
                    <Pagination
                      currentPage={
                        currentPage
                      }
                      totalPages={
                        totalPages
                      }
                      onPageChange={
                        changePage
                      }
                    />
                  )}
                </>
              )}
          </div>
        </div>
      </section>

      <section className="bg-violet-950 text-white">
        <div className="mx-auto grid max-w-7xl items-center gap-8 px-6 py-16 lg:grid-cols-[1fr_auto]">
          <div>
            <p className="font-extrabold text-violet-300">
              Need help choosing?
            </p>

            <h2 className="mt-2 text-4xl font-black md:text-5xl">
              Let PawConnect compare pets
              with your lifestyle.
            </h2>

            <p className="mt-4 max-w-3xl text-lg leading-8 text-violet-100">
              Complete the AI matching
              questionnaire to receive
              compatibility scores,
              matching reasons, concerns,
              and explainable
              recommendations.
            </p>
          </div>

          <Link
            href="/ai-assistant"
            className="rounded-2xl bg-white px-8 py-4 font-black text-violet-900 hover:bg-violet-100"
          >
            ✨ Start AI Matching
          </Link>
        </div>
      </section>

      <footer className="border-t border-emerald-900 bg-emerald-950 text-emerald-200">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-5 px-6 py-8">
          <Link
            href="/"
            className="flex items-center gap-3"
          >
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-800 text-2xl">
              🐾
            </div>

            <div>
              <p className="text-xl font-black text-white">
                PawConnect
              </p>

              <p className="text-xs font-bold text-emerald-300">
                Find. Match. Adopt.
              </p>
            </div>
          </Link>

          <div className="flex flex-wrap gap-5 font-bold">
            <Link
              href="/ai-assistant"
              className="hover:text-white"
            >
              AI Pet Match
            </Link>

            <Link
              href="/dashboard"
              className="hover:text-white"
            >
              Dashboard
            </Link>

            <Link
              href="/my-applications"
              className="hover:text-white"
            >
              My Applications
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}

function Pagination({
  currentPage,
  totalPages,
  onPageChange,
}) {
  const visiblePages =
    getVisiblePages(
      currentPage,
      totalPages
    );

  return (
    <nav
      className="mt-10 flex flex-wrap items-center justify-center gap-2"
      aria-label="Pet listing pages"
    >
      <button
        type="button"
        onClick={() =>
          onPageChange(
            currentPage - 1
          )
        }
        disabled={currentPage === 1}
        className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-extrabold text-slate-700 transition hover:border-emerald-500 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        ← Previous
      </button>

      {visiblePages.map(
        (page, index) => {
          if (page === "...") {
            return (
              <span
                key={`ellipsis-${index}`}
                className="px-2 font-bold text-slate-400"
              >
                ...
              </span>
            );
          }

          const active =
            currentPage === page;

          return (
            <button
              key={page}
              type="button"
              onClick={() =>
                onPageChange(page)
              }
              className={`flex h-12 min-w-12 items-center justify-center rounded-xl border px-4 font-extrabold transition ${
                active
                  ? "border-emerald-700 bg-emerald-700 text-white shadow-lg shadow-emerald-100"
                  : "border-slate-300 bg-white text-slate-700 hover:border-emerald-500 hover:bg-emerald-50"
              }`}
              aria-current={
                active
                  ? "page"
                  : undefined
              }
            >
              {page}
            </button>
          );
        }
      )}

      <button
        type="button"
        onClick={() =>
          onPageChange(
            currentPage + 1
          )
        }
        disabled={
          currentPage === totalPages
        }
        className="rounded-xl border border-slate-300 bg-white px-5 py-3 font-extrabold text-slate-700 transition hover:border-emerald-500 hover:bg-emerald-50 disabled:cursor-not-allowed disabled:opacity-40"
      >
        Next →
      </button>
    </nav>
  );
}

function AnimalCard({ animal }) {
  const isCat =
    animal.type?.toLowerCase() === "cat";

  const ageText = String(
    animal.age || ""
  ).toLowerCase();

  let ageBadge = "";

  if (
    ageText.includes("month") ||
    ageText.includes("week")
  ) {
    ageBadge = isCat
      ? "🐱 Kitten"
      : "🐶 Puppy";
  } else {
    const ageNumber = parseFloat(
      ageText
    );

    if (
      Number.isFinite(ageNumber)
    ) {
      if (ageNumber < 2) {
        ageBadge = "🌱 Young";
      } else if (ageNumber < 8) {
        ageBadge = "🐾 Adult";
      } else {
        ageBadge = "❤️ Senior";
      }
    }
  }

  const temperamentTraits = String(
    animal.temperament || ""
  )
    .split(",")
    .map((trait) => trait.trim())
    .filter(Boolean)
    .slice(0, 3);

  return (
    <article className="group flex h-full flex-col overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm transition-all duration-300 hover:-translate-y-1.5 hover:shadow-2xl">
      <div className="relative">
        <AnimalImage
          src={animal.image_url}
          alt={animal.name}
          type={animal.type}
        />

        <div className="absolute left-4 top-4 flex flex-wrap gap-2">
          <span className="rounded-full bg-emerald-600 px-3 py-1.5 text-xs font-extrabold text-white shadow-md">
            ● Available
          </span>

          {ageBadge && (
            <span className="rounded-full bg-white/95 px-3 py-1.5 text-xs font-extrabold text-slate-800 shadow-md backdrop-blur">
              {ageBadge}
            </span>
          )}
        </div>

        <div className="absolute right-4 top-4 flex h-11 w-11 items-center justify-center rounded-full bg-white/95 text-xl shadow-md backdrop-blur">
          {isCat ? "🐱" : "🐶"}
        </div>
      </div>

      <div className="flex flex-1 flex-col p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-xs font-extrabold uppercase tracking-[0.14em] text-emerald-700">
              {animal.type || "Pet"}
            </p>

            <h3 className="mt-1 truncate text-3xl font-black text-slate-950">
              {animal.name ||
                "Unnamed Pet"}
            </h3>

            <p className="mt-1 truncate font-semibold capitalize text-slate-500">
              {animal.breed ||
                "Mixed breed"}
            </p>
          </div>

          <span className="shrink-0 rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-extrabold capitalize text-emerald-800">
            {animal.gender ||
              "Unknown"}
          </span>
        </div>

        <div className="mt-4 min-h-[58px]">
          {temperamentTraits.length >
          0 ? (
            <div className="flex flex-wrap gap-2">
              {temperamentTraits.map(
                (trait) => (
                  <span
                    key={trait}
                    className="rounded-full bg-orange-50 px-3 py-1.5 text-xs font-bold capitalize text-orange-700"
                  >
                    {trait}
                  </span>
                )
              )}
            </div>
          ) : (
            <p className="line-clamp-2 leading-6 text-slate-600">
              Friendly companion waiting
              for a caring home.
            </p>
          )}
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3">
          <PetDetail
            label="Age"
            value={
              animal.age ||
              "Unknown"
            }
          />

          <PetDetail
            label="Size"
            value={
              animal.size ||
              "Unknown"
            }
          />

          <PetDetail
            label="Location"
            value={
              animal.location ||
              "Unknown"
            }
          />

          <PetDetail
            label="Energy"
            value={
              animal.energy_level ||
              "Unknown"
            }
          />
        </div>

        <div className="mt-4 min-h-[64px]">
          <div className="flex flex-wrap gap-2">
            {Number(
              animal.apartment_friendly
            ) === 1 && (
              <span className="rounded-full bg-blue-100 px-3 py-1.5 text-xs font-extrabold text-blue-700">
                🏠 Apartment
              </span>
            )}

            {Number(
              animal.child_friendly
            ) === 1 && (
              <span className="rounded-full bg-amber-100 px-3 py-1.5 text-xs font-extrabold text-amber-700">
                👶 Child Friendly
              </span>
            )}

            {Number(
              animal.pet_friendly
            ) === 1 && (
              <span className="rounded-full bg-violet-100 px-3 py-1.5 text-xs font-extrabold text-violet-700">
                🐾 Pet Friendly
              </span>
            )}
          </div>
        </div>

        <div className="mt-auto pt-5">
          <Link
            href={`/animals/${animal.id}`}
            className="flex min-h-14 w-full items-center justify-center gap-2 rounded-2xl bg-emerald-700 px-4 py-3.5 text-center text-base font-black text-white shadow-sm transition hover:bg-emerald-800 focus:outline-none focus:ring-4 focus:ring-emerald-200"
          >
            Meet{" "}
            {animal.name ||
              "This Pet"}
            <span className="transition-transform duration-200 group-hover:translate-x-1">
              →
            </span>
          </Link>
        </div>
      </div>
    </article>
  );
}

function AnimalImage({
  src,
  alt,
  type,
}) {
  const [failed, setFailed] =
    useState(false);

  const emoji =
    type?.toLowerCase() === "cat"
      ? "🐱"
      : "🐶";

  if (!src || failed) {
    return (
      <div className="flex aspect-[4/3] items-center justify-center bg-gradient-to-br from-orange-100 via-rose-100 to-emerald-100">
        <div className="text-center">

          <div className="text-8xl">
            {emoji}
          </div>

          <p className="mt-3 font-bold text-slate-500">
            Photo Coming Soon
          </p>

        </div>
      </div>
    );
  }

  return (
    <div className="aspect-[4/3] overflow-hidden bg-slate-100">

      <img
        src={src}
        alt={alt}
        onError={() =>
          setFailed(true)
        }
        className="h-full w-full object-cover transition duration-500 group-hover:scale-110"
      />

    </div>
  );
}

function PetDetail({
  label,
  value,
}) {
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <p className="text-xs font-extrabold uppercase tracking-wide text-slate-400">
        {label}
      </p>

      <p className="mt-1 truncate font-bold capitalize text-slate-700">
        {value}
      </p>
    </div>
  );
}

function FilterGroup({
  label,
  children,
}) {
  return (
    <div>
      <label className="mb-2 block text-sm font-extrabold text-slate-700">
        {label}
      </label>

      {children}
    </div>
  );
}

function TypeFilterButton({
  label,
  value,
  selected,
  onSelect,
}) {
  const active =
    selected === value;

  return (
    <button
      type="button"
      onClick={() =>
        onSelect(value)
      }
      className={`rounded-xl border py-2.5 text-sm font-extrabold transition ${
        active
          ? "border-emerald-700 bg-emerald-700 text-white"
          : "border-slate-300 bg-white text-slate-700 hover:border-emerald-500 hover:bg-emerald-50"
      }`}
    >
      {label}
    </button>
  );
}

function ActiveFilter({
  label,
  onRemove,
}) {
  return (
    <span className="inline-flex items-center gap-2 rounded-full bg-emerald-100 px-3 py-2 text-sm font-bold text-emerald-800">
      {label}

      <button
        type="button"
        onClick={onRemove}
        className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-200 text-xs hover:bg-emerald-300"
        aria-label={`Remove ${label}`}
      >
        ×
      </button>
    </span>
  );
}

function HeroMiniCard({
  emoji,
  value,
  label,
}) {
  return (
    <div className="rounded-2xl bg-white p-5 text-center text-slate-900">
      <div className="text-4xl">
        {emoji}
      </div>

      <p className="mt-2 text-3xl font-black text-emerald-800">
        {value}
      </p>

      <p className="text-sm font-bold text-slate-500">
        {label}
      </p>
    </div>
  );
}

function LoadingGrid() {
  return (
    <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({
        length: 6,
      }).map((_, index) => (
        <div
          key={index}
          className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white"
        >
          <div className="h-72 animate-pulse bg-slate-200" />

          <div className="space-y-4 p-5">
            <div className="h-4 w-20 animate-pulse rounded bg-slate-200" />

            <div className="h-8 w-40 animate-pulse rounded bg-slate-200" />

            <div className="h-4 w-32 animate-pulse rounded bg-slate-200" />

            <div className="grid grid-cols-2 gap-3">
              <div className="h-16 animate-pulse rounded-xl bg-slate-100" />

              <div className="h-16 animate-pulse rounded-xl bg-slate-100" />

              <div className="h-16 animate-pulse rounded-xl bg-slate-100" />

              <div className="h-16 animate-pulse rounded-xl bg-slate-100" />
            </div>

            <div className="h-12 animate-pulse rounded-xl bg-slate-200" />
          </div>
        </div>
      ))}
    </div>
  );
}

function NoAnimalsFound({
  clearFilters,
}) {
  return (
    <div className="rounded-[2rem] border border-dashed border-slate-300 bg-white p-12 text-center">
      <div className="text-7xl">
        🐾
      </div>

      <h3 className="mt-5 text-3xl font-black">
        No pets match these filters
      </h3>

      <p className="mx-auto mt-3 max-w-xl leading-7 text-slate-600">
        Try changing the location,
        breed, age, or other filters
        to discover more animals
        waiting for homes.
      </p>

      <button
        type="button"
        onClick={clearFilters}
        className="mt-6 rounded-xl bg-emerald-700 px-7 py-3.5 font-extrabold text-white hover:bg-emerald-800"
      >
        Clear All Filters
      </button>
    </div>
  );
}

function DecorativePaw({
  className,
}) {
  return (
    <div
      className={`pointer-events-none absolute select-none text-8xl opacity-40 ${className}`}
    >
      🐾
    </div>
  );
}

function matchesAgeGroup(
  ageValue,
  selectedGroup
) {
  if (
    selectedGroup === "all"
  ) {
    return true;
  }

  const age =
    extractAgeNumber(ageValue);

  if (!Number.isFinite(age)) {
    return false;
  }

  if (
    selectedGroup === "young"
  ) {
    return age < 2;
  }

  if (
    selectedGroup === "adult"
  ) {
    return (
      age >= 2 && age < 8
    );
  }

  if (
    selectedGroup === "senior"
  ) {
    return age >= 8;
  }

  return true;
}

function extractAgeNumber(
  ageValue
) {
  if (
    ageValue === null ||
    ageValue === undefined
  ) {
    return Number.POSITIVE_INFINITY;
  }

  if (
    typeof ageValue === "number"
  ) {
    return ageValue;
  }

  const text = String(
    ageValue
  ).toLowerCase();

  const match =
    text.match(/[\d.]+/);

  if (!match) {
    return Number.POSITIVE_INFINITY;
  }

  const number =
    Number(match[0]);

  if (
    !Number.isFinite(number)
  ) {
    return Number.POSITIVE_INFINITY;
  }

  if (
    text.includes("month") ||
    text.includes("months")
  ) {
    return number / 12;
  }

  return number;
}

function getVisiblePages(
  currentPage,
  totalPages
) {
  if (totalPages <= 7) {
    return Array.from(
      { length: totalPages },
      (_, index) => index + 1
    );
  }

  if (currentPage <= 4) {
    return [
      1,
      2,
      3,
      4,
      5,
      "...",
      totalPages,
    ];
  }

  if (
    currentPage >=
    totalPages - 3
  ) {
    return [
      1,
      "...",
      totalPages - 4,
      totalPages - 3,
      totalPages - 2,
      totalPages - 1,
      totalPages,
    ];
  }

  return [
    1,
    "...",
    currentPage - 1,
    currentPage,
    currentPage + 1,
    "...",
    totalPages,
  ];
}

function capitalize(value) {
  if (!value) {
    return "";
  }

  return (
    value
      .charAt(0)
      .toUpperCase() +
    value.slice(1)
  );
}

export default function AnimalsPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen flex items-center justify-center">
          <p className="text-lg font-semibold">
            Loading pets...
          </p>
        </main>
      }
    >
      <AnimalsPageContent />
    </Suspense>
  );
}