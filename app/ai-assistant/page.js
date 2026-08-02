"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

const EXAMPLE_PROMPTS = [
  "I live in a condo and work all day. I want a calm, quiet cat that can stay alone.",
  "I live in a house with children. We want a friendly and playful dog.",
  "I am a first-time pet owner. I prefer a low-maintenance animal suitable for an apartment.",
];

export default function AiAssistantPage() {
  const [description, setDescription] = useState("");
  const [result, setResult] = useState(null);

  const [currentUser, setCurrentUser] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadCurrentUser();
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

  function handleLogout() {
    localStorage.removeItem("user");
    window.location.href = "/";
  }

  function useExamplePrompt(prompt) {
    setDescription(prompt);
    setError("");
    setResult(null);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const cleanedDescription = description.trim();

    if (!cleanedDescription) {
      setError("Please describe your lifestyle and preferred pet.");
      return;
    }

    if (cleanedDescription.length < 15) {
      setError(
        "Please provide a little more detail so the AI can understand your needs."
      );
      return;
    }

    try {
      setLoading(true);
      setError("");
      setResult(null);

      const response = await fetch("/api/ai/recommendation", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text: cleanedDescription,
        }),
      });

      const contentType = response.headers.get("content-type");

      if (!contentType?.includes("application/json")) {
        throw new Error(
          "The recommendation service returned an invalid response."
        );
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.details ||
            data.error ||
            "Unable to generate pet recommendations."
        );
      }

      setResult({
        input: data.input || cleanedDescription,
        labels: Array.isArray(data.labels) ? data.labels : [],
        confidence:
          data.confidence && typeof data.confidence === "object"
            ? data.confidence
            : {},
        modelVersion: data.modelVersion || "Unknown",
        recommendations: Array.isArray(data.recommendations)
          ? data.recommendations
          : [],
      });
    } catch (requestError) {
      console.error("AI recommendation request failed:", requestError);

      setError(
        requestError.message ||
          "Unable to generate pet recommendations."
      );
    } finally {
      setLoading(false);
    }
  }

  const recommendations = result?.recommendations || [];
  const bestMatch = recommendations[0] || null;
  const moreMatches = recommendations.slice(1);

  return (
    <main className="min-h-screen bg-[#fbf8f3] text-slate-900">
      <Header
        currentUser={currentUser}
        menuOpen={menuOpen}
        setMenuOpen={setMenuOpen}
        handleLogout={handleLogout}
      />

      <section className="max-w-7xl mx-auto px-5 sm:px-6 py-10 md:py-14">
        <div className="max-w-4xl mx-auto text-center mb-10">
          <div className="inline-flex items-center gap-2 bg-violet-100 text-violet-800 px-4 py-2 rounded-full font-extrabold text-sm mb-5">
            <span>✨</span>
            AI-POWERED PET RECOMMENDATION
          </div>

          <h1 className="text-4xl md:text-6xl font-extrabold tracking-tight text-slate-950">
            Find a pet that fits your life
          </h1>

          <p className="text-slate-600 mt-5 text-lg md:text-xl leading-8 max-w-3xl mx-auto">
            Describe your home, routine, experience, and preferred
            personality. PawConnect will analyze your description and
            rank suitable pets.
          </p>
        </div>

        <div className="grid xl:grid-cols-[440px_minmax(0,1fr)] gap-8 items-start">
          <InputPanel
            description={description}
            setDescription={setDescription}
            loading={loading}
            error={error}
            handleSubmit={handleSubmit}
            useExamplePrompt={useExamplePrompt}
          />

          <section className="min-w-0">
            {!loading && !result && (
              <EmptyState />
            )}

            {loading && <LoadingState />}

            {!loading && result && (
              <>
                <DetectedPreferences
                  labels={result.labels}
                  confidence={result.confidence}
                  modelVersion={result.modelVersion}
                />

                {bestMatch ? (
                  <>
                    <BestMatchCard animal={bestMatch} />

                    {moreMatches.length > 0 && (
                      <div className="mt-10">
                        <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
                          <div>
                            <p className="text-violet-700 font-extrabold text-sm mb-1">
                              MORE COMPATIBLE ANIMALS
                            </p>

                            <h2 className="text-3xl font-extrabold">
                              Other recommendations
                            </h2>
                          </div>

                          <Link
                            href="/animals"
                            className="text-green-700 font-extrabold hover:underline"
                          >
                            Browse all pets →
                          </Link>
                        </div>

                        <div className="grid md:grid-cols-2 2xl:grid-cols-3 gap-5 items-stretch">
                          {moreMatches.map((animal) => (
                            <RecommendationCard
                              key={animal.id}
                              animal={animal}
                            />
                          ))}
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <NoMatchesState />
                )}
              </>
            )}
          </section>
        </div>
      </section>
    </main>
  );
}

function Header({
  currentUser,
  menuOpen,
  setMenuOpen,
  handleLogout,
}) {
  return (
    <header className="bg-white border-b border-green-100 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-5 sm:px-6 py-4 flex flex-wrap items-center justify-between gap-4">
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

        <nav className="flex flex-wrap items-center gap-4 lg:gap-6 font-bold text-slate-700">
          <Link href="/" className="hover:text-green-700">
            Home
          </Link>

          <Link
            href="/animals"
            className="hover:text-green-700"
          >
            Browse Pets
          </Link>

          <Link
            href="/ai-assistant"
            className="bg-violet-700 text-white px-5 py-3 rounded-2xl hover:bg-violet-800"
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

                <span className="hidden sm:inline">
                  {currentUser.name || "Profile"}
                </span>

                <span>▾</span>
              </button>

              {menuOpen && (
                <div className="absolute right-0 mt-3 w-56 bg-white border border-slate-200 rounded-2xl shadow-xl overflow-hidden">
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
  );
}

function InputPanel({
  description,
  setDescription,
  loading,
  error,
  handleSubmit,
  useExamplePrompt,
}) {
  const characterCount = description.length;

  return (
    <aside className="bg-white border border-slate-200 rounded-3xl p-6 md:p-7 shadow-sm xl:sticky xl:top-28">
      <div className="w-14 h-14 rounded-2xl bg-violet-100 flex items-center justify-center text-3xl mb-5">
        🤖
      </div>

      <p className="text-violet-700 font-extrabold text-sm mb-2">
        TELL THE AI ABOUT YOURSELF
      </p>

      <h2 className="text-3xl font-extrabold mb-3">
        Describe your ideal pet
      </h2>

      <p className="text-slate-600 leading-7 mb-6">
        You can write naturally. Include your home type, daily
        routine, pet experience, activity level, and preferred pet
        personality.
      </p>

      <form onSubmit={handleSubmit}>
        <label
          htmlFor="lifestyle-description"
          className="block font-extrabold mb-3"
        >
          Your lifestyle description
        </label>

        <textarea
          id="lifestyle-description"
          value={description}
          onChange={(event) => {
            setDescription(event.target.value);

            if (error) {
              // The next submission will revalidate the text.
            }
          }}
          maxLength={1000}
          rows={9}
          placeholder="Example: I live in a condo and work during the day. I want a calm and quiet cat that can spend some time alone. I am a first-time pet owner."
          className="w-full resize-none border border-slate-300 rounded-2xl p-4 leading-7 outline-none transition focus:border-violet-500 focus:ring-4 focus:ring-violet-100"
        />

        <div className="flex justify-between gap-3 mt-2 text-sm text-slate-500">
          <span>Write at least 2 to 4 sentences.</span>
          <span>{characterCount}/1000</span>
        </div>

        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 text-red-800 rounded-xl p-4 text-sm font-semibold">
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="mt-5 w-full bg-violet-700 text-white py-4 rounded-xl font-extrabold text-lg hover:bg-violet-800 disabled:bg-violet-300 disabled:cursor-not-allowed transition"
        >
          {loading
            ? "Analyzing your lifestyle..."
            : "✨ Find My Pet Matches"}
        </button>
      </form>

      <div className="mt-7 pt-6 border-t border-slate-200">
        <p className="font-extrabold mb-3">
          Try an example
        </p>

        <div className="space-y-3">
          {EXAMPLE_PROMPTS.map((prompt, index) => (
            <button
              type="button"
              key={prompt}
              onClick={() => useExamplePrompt(prompt)}
              className="w-full text-left border border-slate-200 rounded-xl p-3 text-sm text-slate-600 hover:border-violet-300 hover:bg-violet-50 transition"
            >
              <span className="font-extrabold text-violet-700">
                Example {index + 1}:
              </span>{" "}
              {prompt}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-6 bg-green-50 border border-green-200 rounded-2xl p-4">
        <p className="font-extrabold text-green-900 text-sm mb-1">
          🔒 Privacy note
        </p>

        <p className="text-sm text-green-900/80 leading-6">
          Your description is processed to generate recommendations.
          This page does not permanently save your input.
        </p>
      </div>
    </aside>
  );
}

function EmptyState() {
  return (
    <div className="bg-white border border-slate-200 rounded-3xl min-h-[560px] p-8 md:p-12 flex flex-col items-center justify-center text-center shadow-sm">
      <div className="w-24 h-24 rounded-full bg-violet-100 flex items-center justify-center text-5xl mb-6">
        🐾
      </div>

      <p className="text-violet-700 font-extrabold text-sm mb-2">
        YOUR MATCHES WILL APPEAR HERE
      </p>

      <h2 className="text-3xl md:text-4xl font-extrabold max-w-xl">
        Tell PawConnect what kind of companion fits your life
      </h2>

      <p className="text-slate-600 mt-4 text-lg leading-8 max-w-2xl">
        The AI will detect preferences from your description, search
        available pets, and explain why each animal may be compatible.
      </p>

      <div className="grid sm:grid-cols-3 gap-4 w-full max-w-2xl mt-9">
        <FeatureBox
          icon="🧠"
          title="Understand"
          text="Analyzes your lifestyle description"
        />

        <FeatureBox
          icon="🔎"
          title="Compare"
          text="Checks available shelter animals"
        />

        <FeatureBox
          icon="💜"
          title="Recommend"
          text="Ranks pets by compatibility"
        />
      </div>
    </div>
  );
}

function FeatureBox({ icon, title, text }) {
  return (
    <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5">
      <div className="text-3xl mb-3">{icon}</div>

      <h3 className="font-extrabold mb-1">{title}</h3>

      <p className="text-sm text-slate-600 leading-6">
        {text}
      </p>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="bg-white border border-slate-200 rounded-3xl min-h-[560px] p-12 flex flex-col items-center justify-center text-center shadow-sm">
      <div className="relative w-24 h-24 mb-7">
        <div className="absolute inset-0 rounded-full border-8 border-violet-100" />

        <div className="absolute inset-0 rounded-full border-8 border-transparent border-t-violet-700 animate-spin" />

        <div className="absolute inset-0 flex items-center justify-center text-3xl">
          🐾
        </div>
      </div>

      <h2 className="text-3xl font-extrabold">
        Finding compatible pets
      </h2>

      <p className="text-slate-600 mt-3 text-lg">
        The AI is reading your description and ranking available
        animals.
      </p>

      <div className="mt-7 flex gap-2">
        <span className="w-3 h-3 rounded-full bg-violet-300 animate-bounce" />
        <span className="w-3 h-3 rounded-full bg-violet-400 animate-bounce [animation-delay:150ms]" />
        <span className="w-3 h-3 rounded-full bg-violet-500 animate-bounce [animation-delay:300ms]" />
      </div>
    </div>
  );
}

function DetectedPreferences({
  labels,
  confidence,
  modelVersion,
}) {
  if (!labels.length) {
    return null;
  }

  return (
    <section className="bg-white border border-violet-200 rounded-3xl p-6 mb-7 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-violet-700 font-extrabold text-sm mb-1">
            AI ANALYSIS
          </p>

          <h2 className="text-2xl font-extrabold">
            Detected preferences
          </h2>

          <p className="text-slate-600 mt-2">
            These preferences were identified from your description.
          </p>
        </div>

        <span className="bg-slate-100 text-slate-600 px-3 py-2 rounded-full text-xs font-bold">
          Model v{modelVersion}
        </span>
      </div>

      <div className="flex flex-wrap gap-3 mt-5">
        {labels.map((label) => {
          const confidenceValue =
            Number(confidence?.[label]) || 0;

          return (
            <div
              key={label}
              className="bg-violet-50 border border-violet-200 rounded-full px-4 py-2 flex items-center gap-2"
            >
              <span>{getLabelIcon(label)}</span>

              <span className="font-bold text-violet-900">
                {formatLabel(label)}
              </span>

              {confidenceValue > 0 && (
                <span className="text-xs text-violet-700 font-extrabold">
                  {Math.round(confidenceValue * 100)}%
                </span>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

function BestMatchCard({ animal }) {
  const matchPercentage = getMatchPercentage(animal);

  return (
    <article className="bg-white border border-slate-200 rounded-3xl overflow-hidden shadow-sm">
      <div className="p-6 md:p-7 border-b border-slate-200">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <p className="text-green-700 font-extrabold text-sm mb-2">
              #1 RECOMMENDED MATCH
            </p>

            <h2 className="text-4xl font-extrabold">
              {animal.name}
            </h2>

            <p className="text-slate-600 mt-2 capitalize">
              {animal.breed || "Mixed breed"} •{" "}
              {animal.type || "Pet"}
            </p>
          </div>

          <MatchBadge percentage={matchPercentage} large />
        </div>
      </div>

      <div className="p-6 md:p-7">
        <PetImage
          src={animal.image_url}
          alt={animal.name}
          type={animal.type}
          className="w-full h-[300px] md:h-[430px] rounded-2xl"
        />

        <div className="mt-6">
          <div className="flex justify-between gap-4 font-bold mb-2">
            <span>Compatibility score</span>
            <span>{matchPercentage}%</span>
          </div>

          <div className="h-3 rounded-full bg-slate-200 overflow-hidden">
            <div
              className="h-full bg-green-700 rounded-full transition-all duration-700"
              style={{
                width: `${matchPercentage}%`,
              }}
            />
          </div>
        </div>

        <div className="grid lg:grid-cols-[1.15fr_0.85fr] gap-5 mt-7">
          <div className="bg-violet-50 border border-violet-200 rounded-2xl p-6">
            <h3 className="text-xl font-extrabold text-violet-900 mb-3">
              🤖 AI recommendation
            </h3>

            <p className="text-slate-700 leading-8">
              {buildAiExplanation(animal)}
            </p>

            {animal.description && (
              <div className="mt-5 pt-5 border-t border-violet-200">
                <p className="font-extrabold text-violet-900 mb-2">
                  About {animal.name}
                </p>

                <p className="text-slate-700 leading-7">
                  {animal.description}
                </p>
              </div>
            )}
          </div>

          <div className="space-y-5">
            <div className="bg-green-50 border border-green-200 rounded-2xl p-5">
              <h3 className="text-lg font-extrabold text-green-900 mb-3">
                Why this pet matches
              </h3>

              <ul className="space-y-3 text-slate-700">
                {Array.isArray(animal.matchReasons) &&
                animal.matchReasons.length > 0 ? (
                  animal.matchReasons.map((reason, index) => (
                    <li
                      key={`${reason}-${index}`}
                      className="flex items-start gap-2"
                    >
                      <span className="text-green-700 font-extrabold">
                        ✓
                      </span>

                      <span>{reason}</span>
                    </li>
                  ))
                ) : (
                  <li className="flex items-start gap-2">
                    <span className="text-green-700 font-extrabold">
                      ✓
                    </span>

                    <span>
                      General lifestyle compatibility
                    </span>
                  </li>
                )}
              </ul>
            </div>

            <PetDetails animal={animal} />
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4 mt-7">
          <Link
            href={`/animals/${animal.id}`}
            className="block text-center border border-green-700 text-green-700 py-4 rounded-xl font-extrabold hover:bg-green-50 transition"
          >
            View Full Profile
          </Link>

          <Link
            href={`/adoption/${animal.id}`}
            className="block text-center bg-green-700 text-white py-4 rounded-xl font-extrabold hover:bg-green-800 transition"
          >
            Apply for Adoption
          </Link>
        </div>
      </div>
    </article>
  );
}

function RecommendationCard({ animal }) {
  const matchPercentage = getMatchPercentage(animal);

  return (
    <article className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm flex flex-col h-full">
      <div className="relative">
        <PetImage
          src={animal.image_url}
          alt={animal.name}
          type={animal.type}
          className="w-full h-56"
        />

        <div className="absolute top-4 right-4">
          <MatchBadge percentage={matchPercentage} />
        </div>
      </div>

      <div className="p-5 flex flex-col flex-1">
        <div>
          <h3 className="text-2xl font-extrabold text-green-900">
            {animal.name}
          </h3>

          <p className="text-sm text-slate-600 capitalize mt-1 min-h-[40px]">
            {animal.breed || "Mixed breed"} •{" "}
            {animal.type || "Pet"}
          </p>
        </div>

        <p className="text-slate-600 text-sm leading-6 mt-4 line-clamp-3 min-h-[72px]">
          {animal.description ||
            animal.temperament ||
            "A compatible pet based on your lifestyle description."}
        </p>

        <div className="mt-4 space-y-2 min-h-[72px]">
          {(animal.matchReasons || [])
            .slice(0, 2)
            .map((reason, index) => (
              <p
                key={`${reason}-${index}`}
                className="text-sm text-green-800 font-semibold flex items-start gap-2"
              >
                <span>✓</span>
                <span>{reason}</span>
              </p>
            ))}
        </div>

        <div className="mt-auto pt-5">
          <Link
            href={`/animals/${animal.id}`}
            className="block w-full text-center bg-slate-950 text-white py-3.5 rounded-xl font-bold hover:bg-slate-800 transition"
          >
            View Pet
          </Link>
        </div>
      </div>
    </article>
  );
}

function PetDetails({ animal }) {
  const details = [
    {
      label: "Age",
      value: animal.age,
    },
    {
      label: "Gender",
      value: animal.gender,
    },
    {
      label: "Size",
      value: animal.size,
    },
    {
      label: "Location",
      value: animal.location,
    },
  ].filter((item) => item.value);

  if (!details.length) {
    return null;
  }

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-2xl p-5">
      <h3 className="text-lg font-extrabold mb-4">
        Pet details
      </h3>

      <div className="grid grid-cols-2 gap-4">
        {details.map((item) => (
          <div key={item.label}>
            <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
              {item.label}
            </p>

            <p className="font-bold text-slate-800 mt-1 capitalize">
              {item.value}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

function MatchBadge({ percentage, large = false }) {
  return (
    <div
      className={`bg-green-100 text-green-800 text-center shadow-sm ${
        large
          ? "rounded-2xl px-6 py-4"
          : "rounded-full px-4 py-2"
      }`}
    >
      <p
        className={
          large
            ? "text-3xl font-extrabold"
            : "text-sm font-extrabold"
        }
      >
        {percentage}% Match
      </p>

      {large && (
        <p className="text-sm font-bold mt-1">
          {getMatchLabel(percentage)}
        </p>
      )}
    </div>
  );
}

function NoMatchesState() {
  return (
    <div className="bg-white border border-slate-200 rounded-3xl p-10 md:p-14 text-center shadow-sm">
      <div className="text-7xl mb-5">🐾</div>

      <h2 className="text-3xl font-extrabold mb-3">
        No available matches found
      </h2>

      <p className="text-slate-600 text-lg leading-8 max-w-xl mx-auto">
        Try adding more detail or describing a different pet type,
        activity level, or home environment.
      </p>
    </div>
  );
}

function PetImage({
  src,
  alt,
  type,
  className,
}) {
  const [failed, setFailed] = useState(false);

  const emoji =
    type?.toLowerCase() === "cat" ? "🐱" : "🐶";

  if (!src || failed) {
    return (
      <div
        className={`${className} bg-slate-200 flex flex-col items-center justify-center`}
      >
        <span className="text-7xl">{emoji}</span>

        <span className="text-slate-500 mt-3 text-sm">
          Image coming soon
        </span>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt || "Pet"}
      onError={() => setFailed(true)}
      className={`${className} object-cover bg-slate-200`}
    />
  );
}

function getMatchPercentage(animal) {
  const percentage = Number(animal?.matchPercentage);

  if (Number.isFinite(percentage)) {
    return Math.max(0, Math.min(100, Math.round(percentage)));
  }

  const score = Number(animal?.matchScore);

  if (Number.isFinite(score)) {
    return Math.max(0, Math.min(100, Math.round(score)));
  }

  return 0;
}

function buildAiExplanation(animal) {
  const reasons = Array.isArray(animal.matchReasons)
    ? animal.matchReasons
    : [];

  if (!reasons.length) {
    return `${animal.name} was selected because its available profile appears compatible with the lifestyle preferences detected by the AI. The shelter should confirm compatibility before adoption.`;
  }

  const formattedReasons = reasons
    .map((reason) => reason.toLowerCase())
    .join(", ");

  return `${animal.name} received a ${getMatchPercentage(
    animal
  )}% compatibility score because of ${formattedReasons}. This recommendation is based on your lifestyle description and the pet information provided by the shelter. The final adoption decision should also include a conversation with the shelter.`;
}

function formatLabel(label) {
  return label
    .split("_")
    .map(
      (word) =>
        word.charAt(0).toUpperCase() +
        word.slice(1)
    )
    .join(" ");
}

function getLabelIcon(label) {
  const icons = {
    prefers_dog: "🐶",
    prefers_cat: "🐱",
    apartment_friendly: "🏢",
    active: "🏃",
    calm: "😌",
    family_friendly: "👨‍👩‍👧",
    beginner_friendly: "🌱",
    low_maintenance: "🧹",
    independent: "🧘",
    affectionate: "💜",
    playful: "🎾",
    quiet: "🔕",
    protective: "🛡️",
    senior_friendly: "🌿",
    low_shedding: "✨",
  };

  return icons[label] || "🐾";
}

function getMatchLabel(score) {
  if (score >= 85) {
    return "Excellent Match";
  }

  if (score >= 70) {
    return "Strong Match";
  }

  if (score >= 55) {
    return "Good Match";
  }

  return "Possible Match";
}