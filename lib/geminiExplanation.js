import "server-only";
import { GoogleGenAI } from "@google/genai";

function createFallbackExplanation(pet) {
  const reasons = Array.isArray(pet.matchReasons)
    ? pet.matchReasons.slice(0, 3)
    : [];

  if (reasons.length === 0) {
    return `${pet.name} may be compatible with your lifestyle based on the calculated match score. Review the pet's full profile and contact the shelter before making a final adoption decision.`;
  }

  return `${pet.name} may be a suitable match because ${reasons
    .join(", ")
    .toLowerCase()} Review the pet's full profile and consult the shelter before making a final decision.`;
}

function buildPrompt(questionnaire, pet) {
  const matchReasons = Array.isArray(pet.matchReasons)
    ? pet.matchReasons
    : [];

  const concerns = Array.isArray(pet.concerns)
    ? pet.concerns
    : [];

  return `
Explain this pet adoption recommendation.

Adopter:
- Preferred pet type: ${questionnaire.preferredType}
- Home type: ${questionnaire.homeType}
- Children: ${questionnaire.hasChildren ? "Yes" : "No"}
- Other pets: ${questionnaire.hasOtherPets ? "Yes" : "No"}
- Experience: ${questionnaire.experienceLevel}
- Daily available time: ${questionnaire.availableAttentionHours} hours
- Activity level: ${questionnaire.activityLevel}

Pet:
- Name: ${pet.name}
- Type: ${pet.type}
- Breed: ${pet.breed || "Mixed breed"}
- Energy level: ${pet.energy_level || "Unknown"}
- Experience required: ${pet.experience_required || "Unknown"}
- Daily attention needed: ${
    pet.daily_attention_hours || "Unknown"
  } hours
- Compatibility score: ${pet.compatibilityScore}%
- Match reasons: ${
    matchReasons.length
      ? matchReasons.join("; ")
      : "No reasons supplied"
  }
- Concerns: ${
    concerns.length
      ? concerns.join("; ")
      : "No major concerns identified"
  }

Requirements:
- Write one paragraph between 60 and 90 words.
- Use simple and friendly English.
- Explain the strongest matching reasons.
- Mention a concern only when one is supplied.
- Do not invent health, behavior, or shelter information.
- Do not guarantee successful adoption.
- Mention that the shelter should help make the final decision.
- Return only the paragraph.
`.trim();
}

export async function generatePetExplanation(
  questionnaire,
  pet
) {
  if (!process.env.GEMINI_API_KEY) {
    console.warn("GEMINI_API_KEY is missing.");

    return createFallbackExplanation(pet);
  }

  try {
    const ai = new GoogleGenAI({
      apiKey: process.env.GEMINI_API_KEY,
    });

    const response = await ai.models.generateContent({
      model: "gemini-3.6-flash",
      contents: buildPrompt(questionnaire, pet),
      config: {
        systemInstruction:
          "Explain pet adoption recommendations using only the supplied information. Never invent facts.",
        temperature: 0.4,
      },
    });

    const explanation = response.text?.trim();

    return explanation || createFallbackExplanation(pet);
  } catch (error) {
    console.error("Gemini explanation failed:", error);

    return createFallbackExplanation(pet);
  }
}