"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";

export default function UserDashboardPage() {
  const router = useRouter();

  const [user, setUser] = useState(null);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const savedUser = localStorage.getItem("user");

    if (!savedUser) {
      router.push("/login?redirect=/dashboard");
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
      router.push("/login?redirect=/dashboard");
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
            "Your applications could not be loaded."
        );
      }

      setApplications(
        Array.isArray(data) ? data : []
      );
    } catch (error) {
      setError(
        error.message ||
          "Your applications could not be loaded."
      );
    } finally {
      setLoading(false);
    }
  }

  const pendingApplications = useMemo(() => {
    return applications.filter(
      (application) =>
        application.status?.toLowerCase() ===
        "pending"
    );
  }, [applications]);

  const approvedApplications = useMemo(() => {
    return applications.filter(
      (application) =>
        application.status?.toLowerCase() ===
        "approved"
    );
  }, [applications]);

  const rejectedApplications = useMemo(() => {
    return applications.filter(
      (application) =>
        application.status?.toLowerCase() ===
        "rejected"
    );
  }, [applications]);

  if (!user && loading) {
    return (
      <main className="min-h-screen bg-[#fffaf4]">
        <Navbar />

        <div className="flex min-h-[70vh] items-center justify-center">
          <div className="rounded-3xl border border-emerald-100 bg-white p-10 text-center shadow-xl">
            <div className="mx-auto h-14 w-14 animate-spin rounded-full border-4 border-emerald-100 border-t-emerald-700" />

            <p className="mt-5 font-bold text-slate-600">
              Loading your dashboard...
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
        <DecorativePaw className="left-[4%] top-12 rotate-12 text-emerald-800" />
        <DecorativePaw className="right-[5%] top-16 -rotate-12 text-emerald-800" />

        <div className="relative mx-auto max-w-7xl px-6 py-14 md:py-20">
          <div className="flex flex-wrap items-center justify-between gap-8">
            <div>
              <p className="font-extrabold text-emerald-300">
                Adopter Dashboard
              </p>

              <h1 className="mt-2 text-4xl font-black md:text-6xl">
                Welcome back,{" "}
                {user?.name || "Pet Lover"}.
              </h1>

              <p className="mt-4 max-w-2xl text-lg leading-8 text-emerald-100">
                Discover pets, review your AI matches, and
                follow the progress of your adoption
                applications.
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
          <StatCard
            icon="📋"
            label="Total Applications"
            value={applications.length}
            note="All submitted requests"
          />

          <StatCard
            icon="⏳"
            label="Pending"
            value={pendingApplications.length}
            note="Waiting for shelter review"
          />

          <StatCard
            icon="✓"
            label="Approved"
            value={approvedApplications.length}
            note="Successful requests"
          />

          <StatCard
            icon="🐾"
            label="AI Matching"
            value="Ready"
            note="Find compatible pets"
          />
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-14">
        <div className="grid gap-6 lg:grid-cols-3">
          <DashboardAction
            href="/animals"
            icon="🐶"
            title="Browse Adoptable Pets"
            description="Explore dogs and cats from registered shelters."
            buttonText="Browse Pets"
            theme="emerald"
          />

          <DashboardAction
            href="/ai-assistant"
            icon="✨"
            title="Find My AI Pet Match"
            description="Answer the lifestyle questionnaire and receive explainable pet recommendations."
            buttonText="Start AI Matching"
            theme="violet"
          />

          <DashboardAction
            href="/my-applications"
            icon="📋"
            title="My Applications"
            description="Track pending, approved, and rejected adoption requests."
            buttonText="View Applications"
            theme="orange"
          />
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-8 px-6 pb-20 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm md:p-8">
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="font-extrabold text-emerald-700">
                Adoption activity
              </p>

              <h2 className="mt-1 text-3xl font-black">
                Recent applications
              </h2>
            </div>

            <Link
              href="/my-applications"
              className="font-extrabold text-emerald-700 hover:underline"
            >
              View all →
            </Link>
          </div>

          {loading && (
            <div className="rounded-2xl bg-slate-50 p-8 text-center">
              <div className="mx-auto h-10 w-10 animate-spin rounded-full border-4 border-emerald-100 border-t-emerald-700" />

              <p className="mt-4 font-bold text-slate-600">
                Loading applications...
              </p>
            </div>
          )}

          {error && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-5 font-semibold text-red-700">
              {error}
            </div>
          )}

          {!loading &&
            !error &&
            applications.length === 0 && (
              <div className="rounded-3xl border border-dashed border-slate-300 bg-slate-50 p-10 text-center">
                <div className="text-6xl">🐾</div>

                <h3 className="mt-4 text-2xl font-black">
                  No applications yet
                </h3>

                <p className="mt-2 text-slate-600">
                  Browse available pets or use the AI
                  matching assistant to find a suitable
                  companion.
                </p>

                <div className="mt-6 flex flex-wrap justify-center gap-3">
                  <Link
                    href="/animals"
                    className="rounded-xl bg-emerald-700 px-6 py-3 font-extrabold text-white hover:bg-emerald-800"
                  >
                    Browse Pets
                  </Link>

                  <Link
                    href="/ai-assistant"
                    className="rounded-xl bg-violet-700 px-6 py-3 font-extrabold text-white hover:bg-violet-800"
                  >
                    ✨ AI Pet Match
                  </Link>
                </div>
              </div>
            )}

          {!loading &&
            !error &&
            applications.length > 0 && (
              <div className="space-y-4">
                {applications
                  .slice(0, 4)
                  .map((application) => (
                    <ApplicationPreview
                      key={application.id}
                      application={application}
                    />
                  ))}
              </div>
            )}
        </div>

        <aside className="space-y-6">
          <div className="rounded-[2rem] bg-violet-950 p-7 text-white shadow-xl">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-violet-800 text-3xl">
              🤖
            </div>

            <p className="mt-5 font-extrabold text-violet-300">
              AI-assisted matching
            </p>

            <h2 className="mt-1 text-3xl font-black">
              Find pets suited to your lifestyle
            </h2>

            <p className="mt-4 leading-7 text-violet-100">
              Compare your home, experience, activity level,
              and available attention time with the needs of
              adoptable pets.
            </p>

            <Link
              href="/ai-assistant"
              className="mt-6 block rounded-xl bg-white px-6 py-3.5 text-center font-extrabold text-violet-900 hover:bg-violet-100"
            >
              Start Questionnaire
            </Link>
          </div>

          <div className="rounded-[2rem] border border-orange-200 bg-orange-50 p-7">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-100 text-3xl">
              💡
            </div>

            <h2 className="mt-5 text-2xl font-black">
              Before you apply
            </h2>

            <div className="mt-5 space-y-4">
              <TipItem text="Read the complete animal profile." />
              <TipItem text="Consider daily care and activity needs." />
              <TipItem text="Provide a detailed adoption reason." />
              <TipItem text="Wait for the shelter's final review." />
            </div>
          </div>
        </aside>
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
              href="/animals"
              className="hover:text-white"
            >
              Browse Pets
            </Link>

            <Link
              href="/ai-assistant"
              className="hover:text-white"
            >
              AI Pet Match
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

function StatCard({
  icon,
  label,
  value,
  note,
}) {
  return (
    <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-lg shadow-slate-200/50">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-bold text-slate-500">
            {label}
          </p>

          <p className="mt-2 text-4xl font-black text-slate-950">
            {value}
          </p>

          <p className="mt-2 text-sm text-slate-500">
            {note}
          </p>
        </div>

        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-100 text-2xl">
          {icon}
        </div>
      </div>
    </article>
  );
}

function DashboardAction({
  href,
  icon,
  title,
  description,
  buttonText,
  theme,
}) {
  const themes = {
    emerald: {
      card: "border-emerald-200 bg-emerald-50",
      icon: "bg-emerald-100",
      button:
        "bg-emerald-700 hover:bg-emerald-800 text-white",
    },
    violet: {
      card: "border-violet-200 bg-violet-50",
      icon: "bg-violet-100",
      button:
        "bg-violet-700 hover:bg-violet-800 text-white",
    },
    orange: {
      card: "border-orange-200 bg-orange-50",
      icon: "bg-orange-100",
      button:
        "bg-orange-500 hover:bg-orange-600 text-white",
    },
  };

  const selectedTheme =
    themes[theme] || themes.emerald;

  return (
    <article
      className={`flex flex-col rounded-[2rem] border p-7 ${selectedTheme.card}`}
    >
      <div
        className={`flex h-16 w-16 items-center justify-center rounded-2xl text-3xl ${selectedTheme.icon}`}
      >
        {icon}
      </div>

      <h2 className="mt-6 text-2xl font-black">
        {title}
      </h2>

      <p className="mt-3 flex-1 leading-7 text-slate-600">
        {description}
      </p>

      <Link
        href={href}
        className={`mt-6 rounded-xl px-6 py-3.5 text-center font-extrabold ${selectedTheme.button}`}
      >
        {buttonText}
      </Link>
    </article>
  );
}

function ApplicationPreview({
  application,
}) {
  return (
    <article className="flex flex-wrap items-center justify-between gap-5 rounded-2xl border border-slate-200 bg-slate-50 p-5">
      <div>
        <p className="text-sm font-extrabold text-slate-500">
          Adoption Application
        </p>

        <h3 className="mt-1 text-xl font-black text-emerald-800">
          {application.animal_name ||
            "Animal application"}
        </h3>

        <p className="mt-1 text-sm text-slate-600">
          Submitted{" "}
          {formatDate(application.created_at)}
        </p>

        {application.compatibility_score != null && (
          <p className="mt-2 font-bold text-violet-700">
            ✨ Compatibility:{" "}
            {application.compatibility_score}%
          </p>
        )}
      </div>

      <StatusBadge status={application.status} />
    </article>
  );
}

function StatusBadge({ status }) {
  const normalized =
    status?.toLowerCase();

  const styles = {
    pending:
      "bg-orange-100 text-orange-800",
    approved:
      "bg-emerald-100 text-emerald-800",
    rejected:
      "bg-red-100 text-red-800",
  };

  return (
    <span
      className={`rounded-full px-4 py-2 text-sm font-extrabold capitalize ${
        styles[normalized] ||
        "bg-slate-100 text-slate-700"
      }`}
    >
      {status || "Unknown"}
    </span>
  );
}

function TipItem({ text }) {
  return (
    <div className="flex items-start gap-3">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-700 text-sm font-black text-white">
        ✓
      </span>

      <p className="leading-6 text-slate-700">
        {text}
      </p>
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
    return "recently";
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