"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const RECOMMENDATION_STORAGE_KEY =
  "pawconnect_selected_recommendation";

export default function RecommendationCard({
  pet,
  position,
  lifestyleAnswers,
}) {
  const router = useRouter();

  const [imageFailed, setImageFailed] =
    useState(false);

  const score = Number(
    pet.compatibilityScore ??
      pet.compatibility_score ??
      0
  );

  const fallbackEmoji =
    pet.type?.toLowerCase() === "cat"
      ? "🐱"
      : "🐶";

  function handleApply() {
    try {
      const recommendationData = {
        animal_id: Number(pet.id),
        compatibility_score: score,
        lifestyle_answers:
          lifestyleAnswers || null,
        match_reasons:
          pet.matchReasons ??
          pet.match_reasons ??
          [],
        concerns: pet.concerns ?? [],
        ai_explanation:
          pet.aiExplanation ??
          pet.ai_explanation ??
          null,
        saved_at: new Date().toISOString(),
      };

      sessionStorage.setItem(
        RECOMMENDATION_STORAGE_KEY,
        JSON.stringify(recommendationData)
      );

      router.push(`/adoption/${pet.id}`);
    } catch (error) {
      console.error(
        "Unable to save recommendation:",
        error
      );

      /*
       * The user can still continue with a normal
       * application if browser storage fails.
       */
      router.push(`/adoption/${pet.id}`);
    }
  }

  return (
    <article className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
      <div className="grid md:grid-cols-[240px_1fr]">
        <div className="min-h-[240px] bg-slate-200">
          {pet.image_url && !imageFailed ? (
            <img
              src={pet.image_url}
              alt={
                pet.name || "Recommended pet"
              }
              onError={() =>
                setImageFailed(true)
              }
              className="h-full min-h-[240px] w-full object-cover"
            />
          ) : (
            <div className="flex h-full min-h-[240px] w-full items-center justify-center text-8xl">
              {fallbackEmoji}
            </div>
          )}
        </div>

        <div className="p-6 md:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="font-bold text-green-700">
                #{position} Recommended Match
              </p>

              <h3 className="mt-1 text-3xl font-extrabold">
                {pet.name || "Unnamed Pet"}
              </h3>

              <p className="mt-1 capitalize text-slate-600">
                {pet.breed || "Mixed breed"} •{" "}
                {pet.type || "Pet"}
              </p>
            </div>

            <ScoreBadge score={score} />
          </div>

          <CompatibilityBar score={score} />

          {pet.aiExplanation && (
            <AIExplanation
              explanation={pet.aiExplanation}
            />
          )}

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <ReasonList
              title="Why this pet matches"
              items={
                pet.matchReasons ??
                pet.match_reasons
              }
              type="positive"
            />

            <ReasonList
              title="Things to consider"
              items={pet.concerns}
              type="concern"
            />
          </div>

          <PetDetails pet={pet} />

          <div className="mt-7 flex flex-wrap gap-3">
            <Link
              href={`/animals/${pet.id}`}
              className="rounded-xl bg-green-700 px-5 py-3 font-bold text-white hover:bg-green-800"
            >
              View Pet Details
            </Link>

            <button
              type="button"
              onClick={handleApply}
              className="rounded-xl border border-green-700 px-5 py-3 font-bold text-green-700 hover:bg-green-50"
            >
              Apply for Adoption
            </button>
          </div>
        </div>
      </div>
    </article>
  );
}

function CompatibilityBar({ score }) {
  const safeScore = Math.min(
    Math.max(Number(score) || 0, 0),
    100
  );

  return (
    <div className="mt-6">
      <div className="mb-2 flex items-center justify-between text-sm font-bold">
        <span>Compatibility</span>
        <span>{safeScore}%</span>
      </div>

      <div className="h-3 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className="h-full rounded-full bg-green-700 transition-all duration-500"
          style={{
            width: `${safeScore}%`,
          }}
        />
      </div>
    </div>
  );
}

function ScoreBadge({ score }) {
  let label = "Possible Match";
  let classes =
    "bg-orange-100 text-orange-800";

  if (score >= 85) {
    label = "Excellent Match";
    classes =
      "bg-green-100 text-green-800";
  } else if (score >= 70) {
    label = "Good Match";
    classes =
      "bg-blue-100 text-blue-800";
  }

  return (
    <div
      className={`rounded-2xl px-4 py-3 text-center ${classes}`}
    >
      <p className="text-2xl font-extrabold">
        {score}%
      </p>

      <p className="text-xs font-bold">
        {label}
      </p>
    </div>
  );
}

function AIExplanation({ explanation }) {
  return (
    <div className="mt-6 rounded-2xl border border-purple-200 bg-purple-50 p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-purple-100 text-xl">
          🤖
        </div>

        <div>
          <h4 className="font-extrabold text-purple-900">
            AI Recommendation Explanation
          </h4>

          <p className="mt-2 leading-7 text-slate-700">
            {explanation}
          </p>
        </div>
      </div>
    </div>
  );
}

function ReasonList({
  title,
  items = [],
  type,
}) {
  const positive = type === "positive";

  return (
    <div
      className={`rounded-2xl border p-5 ${
        positive
          ? "border-green-200 bg-green-50"
          : "border-orange-200 bg-orange-50"
      }`}
    >
      <h4
        className={`font-extrabold ${
          positive
            ? "text-green-800"
            : "text-orange-800"
        }`}
      >
        {title}
      </h4>

      {Array.isArray(items) &&
      items.length > 0 ? (
        <ul className="mt-3 space-y-2">
          {items.map((item, index) => (
            <li
              key={`${item}-${index}`}
              className="flex items-start gap-2 text-sm leading-6"
            >
              <span
                className={
                  positive
                    ? "text-green-700"
                    : "text-orange-700"
                }
              >
                {positive ? "✓" : "•"}
              </span>

              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-slate-600">
          {positive
            ? "No additional match reasons were generated."
            : "No major concerns were identified."}
        </p>
      )}
    </div>
  );
}

function PetDetails({ pet }) {
  const details = [
    {
      label: "Energy",
      value: pet.energy_level,
    },
    {
      label: "Experience",
      value: pet.experience_required,
    },
    {
      label: "Daily attention",
      value: pet.daily_attention_hours
        ? `${pet.daily_attention_hours} hours`
        : null,
    },
    {
      label: "Location",
      value: pet.location,
    },
  ].filter((item) => item.value);

  if (details.length === 0) {
    return null;
  }

  return (
    <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
      {details.map((detail) => (
        <div
          key={detail.label}
          className="rounded-xl border border-slate-200 bg-slate-50 p-3"
        >
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">
            {detail.label}
          </p>

          <p className="mt-1 font-bold capitalize text-slate-800">
            {detail.value}
          </p>
        </div>
      ))}
    </div>
  );
}