"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";

export default function MyApplicationsPage() {
  const router = useRouter();

  const [user, setUser] = useState(null);
  const [applications, setApplications] = useState([]);
  const [activeFilter, setActiveFilter] = useState("all");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const savedUser = localStorage.getItem("user");

    if (!savedUser) {
      router.push("/login?redirect=/my-applications");
      return;
    }

    try {
      const parsedUser = JSON.parse(savedUser);

      if (!parsedUser?.id) {
        throw new Error("Invalid user session.");
      }

      setUser(parsedUser);
      loadApplications(parsedUser.id);
    } catch {
      localStorage.removeItem("user");
      router.push("/login?redirect=/my-applications");
    }
  }, [router]);

  async function loadApplications(userId) {
    try {
      setLoading(true);
      setError("");

      const response = await fetch(
        `/api/adoption-requests?user_id=${userId}`,
        {
          cache: "no-store",
        }
      );

      const contentType =
        response.headers.get("content-type");

      if (!contentType?.includes("application/json")) {
        throw new Error(
          "The application API returned an invalid response."
        );
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error ||
            "Your adoption applications could not be loaded."
        );
      }

      setApplications(Array.isArray(data) ? data : []);
    } catch (error) {
      setError(
        error.message ||
          "Your adoption applications could not be loaded."
      );
    } finally {
      setLoading(false);
    }
  }

  const counts = useMemo(() => {
    return {
      all: applications.length,

      pending: applications.filter(
        (application) =>
          application.status?.toLowerCase() === "pending"
      ).length,

      approved: applications.filter(
        (application) =>
          application.status?.toLowerCase() === "approved"
      ).length,

      rejected: applications.filter(
        (application) =>
          application.status?.toLowerCase() === "rejected"
      ).length,
    };
  }, [applications]);

  const filteredApplications = useMemo(() => {
    if (activeFilter === "all") {
      return applications;
    }

    return applications.filter(
      (application) =>
        application.status?.toLowerCase() === activeFilter
    );
  }, [applications, activeFilter]);

  if (!user && loading) {
    return (
      <main className="min-h-screen bg-[#fffaf4]">
        <Navbar />

        <div className="flex min-h-[70vh] items-center justify-center px-6">
          <div className="rounded-3xl border border-emerald-100 bg-white p-10 text-center shadow-xl">
            <div className="mx-auto h-14 w-14 animate-spin rounded-full border-4 border-emerald-100 border-t-emerald-700" />

            <p className="mt-5 font-bold text-slate-600">
              Loading your applications...
            </p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#fffaf4] text-slate-900">
      <Navbar />

      <section className="relative overflow-hidden bg-gradient-to-br from-emerald-950 via-emerald-900 to-slate-950 text-white">
        <DecorativePaw className="left-[4%] top-14 rotate-12 text-emerald-800" />

        <DecorativePaw className="right-[6%] top-12 -rotate-12 text-emerald-800" />

        <div className="relative mx-auto max-w-7xl px-6 py-16 md:py-20">
          <div className="flex flex-wrap items-center justify-between gap-8">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-700 bg-emerald-900 px-4 py-2 text-sm font-extrabold text-emerald-200">
                <span>📋</span>
                Adoption application tracking
              </div>

              <h1 className="mt-5 text-5xl font-black md:text-6xl">
                My Applications
              </h1>

              <p className="mt-5 max-w-3xl text-lg leading-8 text-emerald-100">
                Follow the progress of every adoption request,
                review compatibility information, and see whether
                the shelter has approved, rejected, or is still
                reviewing your application.
              </p>
            </div>

            <div className="flex h-24 w-24 items-center justify-center rounded-[2rem] border border-emerald-700 bg-emerald-800 text-5xl shadow-xl">
              🐾
            </div>
          </div>
        </div>
      </section>

      <section className="relative z-10 mx-auto -mt-6 max-w-7xl px-6">
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          <SummaryCard
            icon="📋"
            label="All Applications"
            value={counts.all}
            theme="slate"
          />

          <SummaryCard
            icon="⏳"
            label="Pending Review"
            value={counts.pending}
            theme="orange"
          />

          <SummaryCard
            icon="✓"
            label="Approved"
            value={counts.approved}
            theme="emerald"
          />

          <SummaryCard
            icon="×"
            label="Rejected"
            value={counts.rejected}
            theme="red"
          />
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-14">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-5">
          <div>
            <p className="font-extrabold text-emerald-700">
              Application history
            </p>

            <h2 className="mt-2 text-4xl font-black">
              Track your requests
            </h2>

            <p className="mt-3 text-slate-600">
              {filteredApplications.length}{" "}
              {filteredApplications.length === 1
                ? "application"
                : "applications"}{" "}
              shown
            </p>
          </div>

          <Link
            href="/animals"
            className="rounded-xl bg-emerald-700 px-6 py-3.5 font-extrabold text-white hover:bg-emerald-800"
          >
            Browse More Pets
          </Link>
        </div>

        <div className="mb-8 flex flex-wrap gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <FilterButton
            label="All"
            value="all"
            count={counts.all}
            activeFilter={activeFilter}
            onSelect={setActiveFilter}
          />

          <FilterButton
            label="Pending"
            value="pending"
            count={counts.pending}
            activeFilter={activeFilter}
            onSelect={setActiveFilter}
          />

          <FilterButton
            label="Approved"
            value="approved"
            count={counts.approved}
            activeFilter={activeFilter}
            onSelect={setActiveFilter}
          />

          <FilterButton
            label="Rejected"
            value="rejected"
            count={counts.rejected}
            activeFilter={activeFilter}
            onSelect={setActiveFilter}
          />
        </div>

        {loading && <LoadingApplications />}

        {error && (
          <div className="rounded-[2rem] border border-red-200 bg-red-50 p-8 text-center">
            <div className="text-5xl">⚠️</div>

            <h3 className="mt-4 text-2xl font-black text-red-700">
              Applications could not be loaded
            </h3>

            <p className="mt-2 text-red-600">{error}</p>

            <button
              type="button"
              onClick={() => loadApplications(user.id)}
              className="mt-6 rounded-xl bg-red-700 px-6 py-3 font-extrabold text-white hover:bg-red-800"
            >
              Try Again
            </button>
          </div>
        )}

        {!loading &&
          !error &&
          filteredApplications.length === 0 && (
            <EmptyApplications activeFilter={activeFilter} />
          )}

        {!loading &&
          !error &&
          filteredApplications.length > 0 && (
            <div className="space-y-6">
              {filteredApplications.map((application) => (
                <ApplicationCard
                  key={application.id}
                  application={application}
                />
              ))}
            </div>
          )}
      </section>

      <section className="bg-violet-950 text-white">
        <div className="mx-auto grid max-w-7xl items-center gap-8 px-6 py-16 lg:grid-cols-[1fr_auto]">
          <div>
            <p className="font-extrabold text-violet-300">
              Looking for another match?
            </p>

            <h2 className="mt-2 text-4xl font-black md:text-5xl">
              Discover pets suited to your lifestyle.
            </h2>

            <p className="mt-4 max-w-3xl text-lg leading-8 text-violet-100">
              Use the AI-assisted questionnaire to compare your
              home, experience, activity level, and available time
              with the needs of adoptable pets.
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
          <Link href="/" className="flex items-center gap-3">
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
            <Link href="/animals" className="hover:text-white">
              Browse Pets
            </Link>

            <Link
              href="/ai-assistant"
              className="hover:text-white"
            >
              AI Pet Match
            </Link>

            <Link href="/dashboard" className="hover:text-white">
              Dashboard
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}

function ApplicationCard({ application }) {
  const scoreValue = Number(application.compatibility_score);

  const hasScore =
    application.compatibility_score !== null &&
    application.compatibility_score !== undefined &&
    !Number.isNaN(scoreValue);

  const score = hasScore
    ? Math.min(Math.max(scoreValue, 0), 100)
    : null;

  const status = application.status?.toLowerCase();

  return (
    <article className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
      <div className="grid lg:grid-cols-[260px_1fr]">
        <ApplicationAnimalImage
          src={application.image_url}
          alt={application.animal_name}
          type={application.animal_type}
        />

        <div className="p-6 md:p-8">
          <div className="flex flex-wrap items-start justify-between gap-5">
            <div>
              <p className="text-sm font-extrabold uppercase tracking-wide text-emerald-700">
                Adoption Application
              </p>

              <h2 className="mt-2 text-3xl font-black text-slate-950">
                {application.animal_name ||
                  "Animal Application"}
              </h2>

              <p className="mt-2 capitalize text-slate-600">
                {application.animal_type || "Pet"}

                {application.animal_breed
                  ? ` • ${application.animal_breed}`
                  : ""}
              </p>

              {application.shelter_name && (
                <p className="mt-2 text-sm font-bold text-slate-500">
                  🏡 {application.shelter_name}
                </p>
              )}
            </div>

            <StatusBadge status={application.status} />
          </div>

          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <ApplicationInfo
              label="Submitted"
              value={formatDate(application.created_at)}
            />

            <ApplicationInfo
              label="Status"
              value={application.status || "Unknown"}
            />

            <ApplicationInfo
              label="Compatibility"
              value={hasScore ? `${score}%` : "Not calculated"}
            />
          </div>

          {hasScore && (
            <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-extrabold text-emerald-700">
                    AI-Assisted Matching
                  </p>

                  <h3 className="font-black text-emerald-950">
                    Compatibility Score
                  </h3>
                </div>

                <span className="text-3xl font-black text-emerald-700">
                  {score}%
                </span>
              </div>

              <div className="mt-3 h-3 overflow-hidden rounded-full bg-emerald-100">
                <div
                  className="h-full rounded-full bg-emerald-700"
                  style={{
                    width: `${score}%`,
                  }}
                />
              </div>
            </div>
          )}

          <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5">
            <p className="text-sm font-extrabold text-slate-500">
              Your Adoption Reason
            </p>

            <p className="mt-2 leading-7 text-slate-700">
              {application.reason || "No reason was provided."}
            </p>
          </div>

          <StatusMessage status={status} />

          <div className="mt-6 flex flex-wrap gap-3">
            {application.animal_id && (
              <Link
                href={`/animals/${application.animal_id}`}
                className="rounded-xl bg-emerald-700 px-6 py-3 font-extrabold text-white hover:bg-emerald-800"
              >
                View Pet Profile
              </Link>
            )}

            <Link
              href="/animals"
              className="rounded-xl border-2 border-emerald-700 bg-white px-6 py-3 font-extrabold text-emerald-800 hover:bg-emerald-50"
            >
              Browse More Pets
            </Link>
          </div>
        </div>
      </div>
    </article>
  );
}

function ApplicationAnimalImage({ src, alt, type }) {
  const [failed, setFailed] = useState(false);

  const fallbackEmoji =
    type?.toLowerCase() === "cat" ? "🐱" : "🐶";

  if (!src || failed) {
    return (
      <div className="flex min-h-72 flex-col items-center justify-center bg-gradient-to-br from-orange-100 via-rose-100 to-emerald-100">
        <span className="text-8xl">{fallbackEmoji}</span>

        <p className="mt-3 font-bold text-slate-500">
          Pet photo
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-72 overflow-hidden bg-slate-200">
      <img
        src={src}
        alt={alt || "Adoptable pet"}
        onError={() => setFailed(true)}
        className="h-full min-h-72 w-full object-cover"
      />
    </div>
  );
}

function SummaryCard({ icon, label, value, theme }) {
  const themes = {
    slate: "bg-slate-100 text-slate-800",
    orange: "bg-orange-100 text-orange-800",
    emerald: "bg-emerald-100 text-emerald-800",
    red: "bg-red-100 text-red-800",
  };

  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/50">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-bold text-slate-500">{label}</p>

          <p className="mt-2 text-4xl font-black text-slate-950">
            {value}
          </p>
        </div>

        <div
          className={`flex h-12 w-12 items-center justify-center rounded-2xl text-2xl ${
            themes[theme] || themes.slate
          }`}
        >
          {icon}
        </div>
      </div>
    </article>
  );
}

function FilterButton({
  label,
  value,
  count,
  activeFilter,
  onSelect,
}) {
  const active = activeFilter === value;

  return (
    <button
      type="button"
      onClick={() => onSelect(value)}
      className={`inline-flex items-center gap-2 rounded-xl px-5 py-3 font-extrabold transition ${
        active
          ? "bg-emerald-700 text-white"
          : "bg-slate-50 text-slate-700 hover:bg-emerald-50 hover:text-emerald-800"
      }`}
    >
      <span>{label}</span>

      <span
        className={`flex h-6 min-w-6 items-center justify-center rounded-full px-1.5 text-xs ${
          active
            ? "bg-white/20 text-white"
            : "bg-slate-200 text-slate-600"
        }`}
      >
        {count}
      </span>
    </button>
  );
}

function ApplicationInfo({ label, value }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <p className="text-xs font-extrabold uppercase tracking-wide text-slate-400">
        {label}
      </p>

      <p className="mt-1 font-black capitalize text-slate-800">
        {value}
      </p>
    </div>
  );
}

function StatusBadge({ status }) {
  const normalized = status?.toLowerCase();

  const styles = {
    pending:
      "border-orange-200 bg-orange-100 text-orange-800",
    approved:
      "border-emerald-200 bg-emerald-100 text-emerald-800",
    rejected:
      "border-red-200 bg-red-100 text-red-800",
  };

  const icons = {
    pending: "⏳",
    approved: "✓",
    rejected: "×",
  };

  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 font-extrabold capitalize ${
        styles[normalized] ||
        "border-slate-200 bg-slate-100 text-slate-700"
      }`}
    >
      <span>{icons[normalized] || "🐾"}</span>

      {status || "Unknown"}
    </span>
  );
}

function StatusMessage({ status }) {
  if (status === "approved") {
    return (
      <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
        <p className="font-black text-emerald-900">
          ✓ Your application was approved
        </p>

        <p className="mt-2 leading-7 text-emerald-800">
          The shelter may contact you regarding the next steps,
          required documents, or a meeting with the animal.
        </p>
      </div>
    );
  }

  if (status === "rejected") {
    return (
      <div className="mt-6 rounded-2xl border border-red-200 bg-red-50 p-5">
        <p className="font-black text-red-900">
          This application was not approved
        </p>

        <p className="mt-2 leading-7 text-red-800">
          Adoption decisions are made by shelter staff based on
          the animal&apos;s needs and the information available
          during review.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-6 rounded-2xl border border-orange-200 bg-orange-50 p-5">
      <p className="font-black text-orange-900">
        ⏳ Waiting for shelter review
      </p>

      <p className="mt-2 leading-7 text-orange-800">
        Your application is still being reviewed. The shelter
        may contact you if additional information is required.
      </p>
    </div>
  );
}

function EmptyApplications({ activeFilter }) {
  const filtered = activeFilter !== "all";

  return (
    <div className="rounded-[2rem] border border-dashed border-slate-300 bg-white p-12 text-center">
      <div className="text-7xl">🐾</div>

      <h3 className="mt-5 text-3xl font-black">
        {filtered
          ? `No ${activeFilter} applications`
          : "You have not applied yet"}
      </h3>

      <p className="mx-auto mt-3 max-w-xl leading-7 text-slate-600">
        {filtered
          ? "There are currently no applications in this category."
          : "Browse available pets or use AI-assisted matching to find an animal suited to your lifestyle."}
      </p>

      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <Link
          href="/animals"
          className="rounded-xl bg-emerald-700 px-7 py-3.5 font-extrabold text-white hover:bg-emerald-800"
        >
          Browse Pets
        </Link>

        <Link
          href="/ai-assistant"
          className="rounded-xl bg-violet-700 px-7 py-3.5 font-extrabold text-white hover:bg-violet-800"
        >
          ✨ AI Pet Match
        </Link>
      </div>
    </div>
  );
}

function LoadingApplications() {
  return (
    <div className="space-y-6">
      {Array.from({ length: 3 }).map((_, index) => (
        <div
          key={index}
          className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white"
        >
          <div className="grid lg:grid-cols-[260px_1fr]">
            <div className="min-h-72 animate-pulse bg-slate-200" />

            <div className="space-y-5 p-8">
              <div className="h-4 w-40 animate-pulse rounded bg-slate-200" />

              <div className="h-9 w-72 max-w-full animate-pulse rounded bg-slate-200" />

              <div className="grid gap-4 md:grid-cols-3">
                <div className="h-20 animate-pulse rounded-xl bg-slate-100" />
                <div className="h-20 animate-pulse rounded-xl bg-slate-100" />
                <div className="h-20 animate-pulse rounded-xl bg-slate-100" />
              </div>

              <div className="h-28 animate-pulse rounded-2xl bg-slate-100" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function DecorativePaw({ className }) {
  return (
    <div
      className={`pointer-events-none absolute select-none text-8xl opacity-40 ${className}`}
    >
      🐾
    </div>
  );
}

function formatDate(value) {
  if (!value) {
    return "Not available";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}