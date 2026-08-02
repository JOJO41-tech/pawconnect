"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Navbar from "@/components/Navbar";

const RECOMMENDATION_STORAGE_KEY =
  "pawconnect_selected_recommendation";

export default function AdoptionApplicationPage() {
  const params = useParams();
  const router = useRouter();

  const [animal, setAnimal] = useState(null);
  const [user, setUser] = useState(null);
  const [recommendation, setRecommendation] = useState(null);

  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [success, setSuccess] = useState(false);

  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!params?.id) {
      return;
    }

    loadUser();
    loadRecommendation();
    loadAnimal();
  }, [params?.id]);

  function loadUser() {
    const savedUser = localStorage.getItem("user");

    if (!savedUser) {
      setUser(null);
      return;
    }

    try {
      const parsedUser = JSON.parse(savedUser);
      setUser(parsedUser);
    } catch {
      localStorage.removeItem("user");
      setUser(null);
    }
  }

  function loadRecommendation() {
    try {
      const savedRecommendation = sessionStorage.getItem(
        RECOMMENDATION_STORAGE_KEY
      );

      if (!savedRecommendation) {
        setRecommendation(null);
        return;
      }

      const parsedRecommendation = JSON.parse(savedRecommendation);

      const currentAnimalId = Number(params.id);

      const storedAnimalId = Number(
        parsedRecommendation.animal_id ??
          parsedRecommendation.animalId ??
          parsedRecommendation.id
      );

      if (currentAnimalId === storedAnimalId) {
        setRecommendation(parsedRecommendation);
      } else {
        setRecommendation(null);
      }
    } catch {
      sessionStorage.removeItem(RECOMMENDATION_STORAGE_KEY);
      setRecommendation(null);
    }
  }

  async function loadAnimal() {
    try {
      setLoading(true);
      setMessage("");

      const response = await fetch(`/api/animals/${params.id}`, {
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
          data.error || "Animal could not be loaded."
        );
      }

      setAnimal(data);
    } catch (error) {
      setMessage(
        error.message || "Animal could not be loaded."
      );
    } finally {
      setLoading(false);
    }
  }

  const compatibilityScore = useMemo(() => {
    const rawScore =
      recommendation?.compatibility_score ??
      recommendation?.compatibilityScore;

    if (
      rawScore === null ||
      rawScore === undefined ||
      rawScore === ""
    ) {
      return null;
    }

    const numericScore = Number(rawScore);

    if (Number.isNaN(numericScore)) {
      return null;
    }

    return Math.min(Math.max(numericScore, 0), 100);
  }, [recommendation]);

  const lifestyleAnswers = useMemo(() => {
    return (
      recommendation?.lifestyle_answers ??
      recommendation?.lifestyleAnswers ??
      null
    );
  }, [recommendation]);

  const matchReasons = useMemo(() => {
    const reasons =
      recommendation?.match_reasons ??
      recommendation?.matchReasons ??
      [];

    return Array.isArray(reasons) ? reasons : [];
  }, [recommendation]);

  const concerns = useMemo(() => {
    return Array.isArray(recommendation?.concerns)
      ? recommendation.concerns
      : [];
  }, [recommendation]);

  const aiExplanation =
    recommendation?.ai_explanation ??
    recommendation?.aiExplanation ??
    "";

  const hasRecommendation =
    recommendation && compatibilityScore !== null;

  async function handleSubmit(event) {
    event.preventDefault();

    if (!user?.id) {
      router.push(`/login?redirect=/adoption/${params.id}`);
      return;
    }

    if (!reason.trim()) {
      setSuccess(false);
      setMessage(
        "Please explain why you would like to adopt this animal."
      );
      return;
    }

    if (reason.trim().length < 20) {
      setSuccess(false);
      setMessage(
        "Please provide at least 20 characters in your adoption reason."
      );
      return;
    }

    try {
      setSubmitting(true);
      setMessage("");
      setSuccess(false);

      const requestBody = {
        user_id: Number(user.id),
        animal_id: Number(params.id),
        reason: reason.trim(),
        compatibility_score: hasRecommendation
          ? compatibilityScore
          : null,
        lifestyle_answers: hasRecommendation
          ? lifestyleAnswers
          : null,
      };

      const response = await fetch("/api/adoption-requests", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestBody),
      });

      const contentType = response.headers.get("content-type");

      if (!contentType?.includes("application/json")) {
        throw new Error(
          "The application API returned an invalid response."
        );
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.error || "Application could not be submitted."
        );
      }

      setSuccess(true);
      setMessage(
        "Your adoption application was submitted successfully."
      );

      setReason("");
      setRecommendation(null);

      sessionStorage.removeItem(RECOMMENDATION_STORAGE_KEY);
    } catch (error) {
      setSuccess(false);

      setMessage(
        error.message || "Application could not be submitted."
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <main className="min-h-screen bg-[#fffaf4]">
        <Navbar />

        <section className="flex min-h-[70vh] items-center justify-center px-6">
          <div className="rounded-3xl border border-emerald-100 bg-white p-10 text-center shadow-xl">
            <div className="mx-auto h-14 w-14 animate-spin rounded-full border-4 border-emerald-100 border-t-emerald-700" />

            <p className="mt-5 font-bold text-slate-600">
              Loading adoption application...
            </p>
          </div>
        </section>
      </main>
    );
  }

  if (!animal) {
    return (
      <main className="min-h-screen bg-[#fffaf4]">
        <Navbar />

        <section className="flex min-h-[70vh] items-center justify-center px-6 py-16">
          <div className="w-full max-w-xl rounded-[2rem] border border-red-200 bg-white p-10 text-center shadow-xl">
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-red-50 text-xl font-black text-red-700">
              PET
            </div>

            <h1 className="mt-6 text-3xl font-black text-red-700">
              Animal Not Found
            </h1>

            <p className="mt-3 leading-7 text-slate-600">
              {message ||
                "This animal record could not be found."}
            </p>

            <Link
              href="/animals"
              className="mt-7 inline-flex rounded-2xl bg-emerald-700 px-7 py-4 font-extrabold text-white hover:bg-emerald-800"
            >
              Back to Browse Pets
            </Link>
          </div>
        </section>
      </main>
    );
  }

  const isAvailable =
    animal.adoption_status?.toLowerCase() === "available";

  return (
    <main className="min-h-screen bg-[#fffaf4] text-slate-900">
      <Navbar />

      <section className="relative overflow-hidden bg-gradient-to-br from-emerald-950 via-emerald-900 to-slate-950 text-white">
        <div className="absolute left-10 top-10 h-40 w-40 rounded-full bg-emerald-700/20 blur-3xl" />

        <div className="absolute right-10 top-14 h-52 w-52 rounded-full bg-orange-400/10 blur-3xl" />

        <div className="relative mx-auto max-w-7xl px-6 py-14 md:py-20">
          <Link
            href={`/animals/${animal.id}`}
            className="inline-flex items-center gap-2 font-extrabold text-emerald-300 hover:text-white"
          >
            Back to {animal.name}
          </Link>

          <div className="mt-8 max-w-4xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-700 bg-emerald-900 px-4 py-2 text-sm font-extrabold text-emerald-200">
              Adoption Application
            </div>

            <h1 className="mt-5 text-5xl font-black leading-tight md:text-6xl">
              Apply to adopt{" "}
              <span className="text-orange-300">
                {animal.name}.
              </span>
            </h1>

            <p className="mt-5 max-w-3xl text-lg leading-8 text-emerald-100">
              Tell the shelter about your home, experience,
              lifestyle, and why you believe you can provide a
              safe and caring home.
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-6 py-12">
        <div className="grid items-start gap-8 lg:grid-cols-[0.85fr_1.15fr]">
          <aside className="space-y-6">
            <div className="overflow-hidden rounded-[2rem] border border-slate-200 bg-white shadow-sm">
              <AnimalImage
                src={animal.image_url}
                alt={animal.name}
                type={animal.type}
              />

              <div className="p-6">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <p className="text-sm font-extrabold capitalize text-emerald-700">
                      {animal.type || "Pet"}
                    </p>

                    <h2 className="mt-1 text-3xl font-black">
                      {animal.name || "Unnamed Pet"}
                    </h2>

                    <p className="mt-1 capitalize text-slate-500">
                      {animal.breed || "Mixed breed"}
                    </p>
                  </div>

                  <StatusBadge
                    status={animal.adoption_status}
                  />
                </div>

                <div className="mt-6 grid grid-cols-2 gap-3">
                  <PetInformation
                    label="Age"
                    value={animal.age}
                  />

                  <PetInformation
                    label="Gender"
                    value={animal.gender}
                  />

                  <PetInformation
                    label="Size"
                    value={animal.size}
                  />

                  <PetInformation
                    label="Location"
                    value={animal.location}
                  />
                </div>

                {animal.description && (
                  <div className="mt-6 rounded-2xl bg-slate-50 p-5">
                    <p className="text-sm font-extrabold text-slate-500">
                      About {animal.name}
                    </p>

                    <p className="mt-2 leading-7 text-slate-700">
                      {animal.description}
                    </p>
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-[2rem] border border-orange-200 bg-orange-50 p-6">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-100 text-sm font-black text-orange-800">
                TIPS
              </div>

              <h2 className="mt-5 text-2xl font-black">
                Write a helpful adoption reason
              </h2>

              <div className="mt-5 space-y-4">
                <ApplicationTip text="Describe your home and living situation." />

                <ApplicationTip text="Mention your experience caring for pets." />

                <ApplicationTip text="Explain your daily schedule and available time." />

                <ApplicationTip
                  text={`Explain why ${animal.name} suits your lifestyle.`}
                />
              </div>
            </div>
          </aside>

          <div className="space-y-6">
            {hasRecommendation ? (
              <RecommendationSummary
                score={compatibilityScore}
                explanation={aiExplanation}
                matchReasons={matchReasons}
                concerns={concerns}
              />
            ) : (
              <div className="rounded-[2rem] border border-violet-200 bg-violet-50 p-6">
                <div className="flex items-start gap-4">
                  <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-violet-100 text-sm font-black text-violet-800">
                    AI
                  </div>

                  <div>
                    <h2 className="text-2xl font-black text-violet-950">
                      No AI match was included
                    </h2>

                    <p className="mt-2 leading-7 text-violet-800">
                      You can continue with a normal adoption
                      application, or complete the lifestyle
                      questionnaire first to include a compatibility
                      score and recommendation information.
                    </p>

                    <Link
                      href="/ai-assistant"
                      className="mt-4 inline-flex rounded-xl bg-violet-700 px-5 py-3 font-extrabold text-white hover:bg-violet-800"
                    >
                      Try AI Pet Matching
                    </Link>
                  </div>
                </div>
              </div>
            )}

            <div className="rounded-[2rem] border border-slate-200 bg-white p-6 shadow-sm md:p-8">
              <div className="mb-7">
                <p className="font-extrabold text-emerald-700">
                  Application details
                </p>

                <h2 className="mt-2 text-3xl font-black">
                  Tell the shelter about yourself
                </h2>

                <p className="mt-3 leading-7 text-slate-600">
                  A detailed and honest response helps shelter staff
                  understand whether your home and lifestyle may suit{" "}
                  {animal.name}.
                </p>
              </div>

              {!isAvailable && (
                <div className="mb-6 rounded-2xl border border-orange-300 bg-orange-50 p-5 font-bold text-orange-800">
                  This animal is no longer available for adoption.
                </div>
              )}

              {!user && isAvailable && (
                <div className="mb-6 rounded-2xl border border-blue-200 bg-blue-50 p-5 text-blue-800">
                  <p className="font-black">Login required</p>

                  <p className="mt-1">
                    You must log in before submitting an adoption
                    application.
                  </p>
                </div>
              )}

              {message && (
                <div
                  className={`mb-6 rounded-2xl border p-5 font-semibold ${
                    success
                      ? "border-emerald-300 bg-emerald-50 text-emerald-800"
                      : "border-red-300 bg-red-50 text-red-800"
                  }`}
                >
                  {success && (
                    <p className="mb-1 font-black">
                      Application submitted
                    </p>
                  )}

                  {message}
                </div>
              )}

              {isAvailable && !success && (
                <form
                  onSubmit={handleSubmit}
                  className="space-y-6"
                >
                  {user && (
                    <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
                      <p className="text-sm font-extrabold text-emerald-700">
                        Applying as
                      </p>

                      <div className="mt-3 flex items-center gap-4">
                        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-700 text-xl font-black text-white">
                          {user.name
                            ?.charAt(0)
                            ?.toUpperCase() || "U"}
                        </span>

                        <div className="min-w-0">
                          <p className="truncate font-black text-slate-950">
                            {user.name || "Registered User"}
                          </p>

                          <p className="truncate text-slate-600">
                            {user.email || ""}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="mb-2 block text-lg font-black">
                      Why would you like to adopt {animal.name}?
                    </label>

                    <textarea
                      value={reason}
                      onChange={(event) =>
                        setReason(event.target.value)
                      }
                      placeholder={`Describe your home, pet experience, daily routine, and why ${animal.name} would be a good match...`}
                      className="min-h-48 w-full rounded-2xl border border-slate-300 p-4 leading-7 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100"
                      required
                    />

                    <div className="mt-2 flex flex-wrap items-center justify-between gap-3 text-sm">
                      <p
                        className={
                          reason.trim().length < 20
                            ? "font-bold text-orange-600"
                            : "font-bold text-emerald-700"
                        }
                      >
                        {reason.trim().length < 20
                          ? "Please provide at least 20 characters."
                          : "Your response has enough detail to submit."}
                      </p>

                      <p className="text-slate-400">
                        {reason.trim().length} characters
                      </p>
                    </div>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                    <p className="font-black text-slate-800">
                      Before submitting
                    </p>

                    <p className="mt-2 text-sm leading-6 text-slate-600">
                      AI matching information supports shelter review
                      only. Shelter staff make the final adoption
                      decision and may request interviews, documents,
                      or a home check.
                    </p>
                  </div>

                  <button
                    type="submit"
                    disabled={submitting}
                    className="w-full rounded-2xl bg-emerald-700 py-4 font-black text-white shadow-lg shadow-emerald-100 transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-400"
                  >
                    {submitting
                      ? "Submitting Application..."
                      : user
                        ? "Submit Adoption Application"
                        : "Login to Apply"}
                  </button>
                </form>
              )}

              {success && (
                <div className="grid gap-3 sm:grid-cols-2">
                  <Link
                    href="/my-applications"
                    className="rounded-xl bg-emerald-700 px-6 py-3.5 text-center font-extrabold text-white hover:bg-emerald-800"
                  >
                    View My Applications
                  </Link>

                  <Link
                    href="/animals"
                    className="rounded-xl border-2 border-emerald-700 bg-white px-6 py-3.5 text-center font-extrabold text-emerald-800 hover:bg-emerald-50"
                  >
                    Browse More Pets
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-emerald-900 bg-emerald-950 text-emerald-200">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-5 px-6 py-8">
          <Link href="/" className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-800 text-xs font-black text-white">
              PC
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

function RecommendationSummary({
  score,
  explanation,
  matchReasons,
  concerns,
}) {
  return (
    <section className="rounded-[2rem] border border-violet-200 bg-white p-6 shadow-sm md:p-8">
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div>
          <div className="inline-flex rounded-full bg-violet-100 px-4 py-2 text-sm font-extrabold text-violet-800">
            AI Assistant Recommendation
          </div>

          <h2 className="mt-4 text-3xl font-black">
            Your compatibility result
          </h2>

          <p className="mt-2 leading-7 text-slate-600">
            This information will be included with your application
            for shelter review.
          </p>
        </div>

        <CompatibilityBadge score={score} />
      </div>

      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between text-sm font-extrabold">
          <span>Compatibility</span>
          <span>{score}%</span>
        </div>

        <div className="h-3 overflow-hidden rounded-full bg-slate-200">
          <div
            className="h-full rounded-full bg-emerald-700"
            style={{
              width: `${score}%`,
            }}
          />
        </div>
      </div>

      {explanation && (
        <div className="mt-6 rounded-2xl border border-violet-200 bg-violet-50 p-5">
          <p className="font-black text-violet-900">
            AI Explanation
          </p>

          <p className="mt-2 leading-7 text-slate-700">
            {explanation}
          </p>
        </div>
      )}

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <ReasonList
          title="Why this pet matches"
          items={matchReasons}
          positive
        />

        <ReasonList
          title="Things to consider"
          items={concerns}
        />
      </div>
    </section>
  );
}

function CompatibilityBadge({ score }) {
  let label = "Possible Match";
  let styles = "bg-orange-100 text-orange-800";

  if (score >= 85) {
    label = "Excellent Match";
    styles = "bg-emerald-100 text-emerald-800";
  } else if (score >= 70) {
    label = "Good Match";
    styles = "bg-blue-100 text-blue-800";
  }

  return (
    <div className={`rounded-2xl px-5 py-4 text-center ${styles}`}>
      <p className="text-3xl font-black">{score}%</p>

      <p className="text-xs font-extrabold">{label}</p>
    </div>
  );
}

function ReasonList({ title, items, positive = false }) {
  return (
    <div
      className={`rounded-2xl border p-5 ${
        positive
          ? "border-emerald-200 bg-emerald-50"
          : "border-orange-200 bg-orange-50"
      }`}
    >
      <h3
        className={`font-black ${
          positive ? "text-emerald-900" : "text-orange-900"
        }`}
      >
        {title}
      </h3>

      {Array.isArray(items) && items.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {items.map((item, index) => (
            <li
              key={`${item}-${index}`}
              className="flex items-start gap-2 text-sm leading-6"
            >
              <span
                className={
                  positive
                    ? "text-emerald-700"
                    : "text-orange-700"
                }
              >
                {positive ? "+" : "-"}
              </span>

              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-slate-600">
          {positive
            ? "No additional match reasons were provided."
            : "No major concerns were identified."}
        </p>
      )}
    </div>
  );
}

function AnimalImage({ src, alt, type }) {
  const [failed, setFailed] = useState(false);

  const fallbackText =
    type?.toLowerCase() === "cat" ? "CAT" : "DOG";

  if (!src || failed) {
    return (
      <div className="flex h-80 flex-col items-center justify-center bg-gradient-to-br from-orange-100 via-rose-100 to-emerald-100">
        <div className="flex h-28 w-28 items-center justify-center rounded-full bg-white text-2xl font-black text-emerald-800 shadow-xl">
          {fallbackText}
        </div>

        <p className="mt-4 font-bold text-slate-500">
          Photo coming soon
        </p>
      </div>
    );
  }

  return (
    <div className="h-80 overflow-hidden bg-slate-200">
      <img
        src={src}
        alt={alt || "Adoptable pet"}
        onError={() => setFailed(true)}
        className="h-full w-full object-cover"
      />
    </div>
  );
}

function PetInformation({ label, value }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <p className="text-xs font-extrabold uppercase tracking-wide text-slate-400">
        {label}
      </p>

      <p className="mt-1 truncate font-bold capitalize text-slate-700">
        {value || "Not provided"}
      </p>
    </div>
  );
}

function ApplicationTip({ text }) {
  return (
    <div className="flex items-start gap-3">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-emerald-700 text-sm font-black text-white">
        +
      </span>

      <p className="leading-6 text-slate-700">{text}</p>
    </div>
  );
}

function StatusBadge({ status }) {
  const normalized = status?.toLowerCase();

  const styles = {
    available:
      "border-emerald-200 bg-emerald-100 text-emerald-800",
    pending:
      "border-orange-200 bg-orange-100 text-orange-800",
    adopted:
      "border-violet-200 bg-violet-100 text-violet-800",
  };

  return (
    <span
      className={`inline-flex h-fit items-center rounded-full border px-4 py-2 text-sm font-extrabold capitalize ${
        styles[normalized] ||
        "border-slate-200 bg-slate-100 text-slate-700"
      }`}
    >
      {status || "Unknown"}
    </span>
  );
}