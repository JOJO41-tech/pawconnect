import "server-only";
import { GoogleGenAI } from "@google/genai";

function createFallbackSummary({
  user,
  animal,
  reason,
  compatibilityScore,
}) {
  const scoreText =
    compatibilityScore !== null &&
    compatibilityScore !== undefined
      ? `The calculated compatibility score is ${compatibilityScore}%.`
      : "No compatibility score was provided.";

  return `${user.name} submitted an adoption application for ${animal.name}. ${scoreText} The applicant stated: "${reason}". The shelter should review the applicant's circumstances, discuss the pet's needs, and complete its normal adoption assessment before making a decision.`;
}

function buildPrompt({
  user,
  animal,
  reason,
  compatibilityScore,
  lifestyleAnswers,
}) {
  return `
Create a short assessment for shelter staff reviewing a pet adoption application.

Applicant:
- Name: ${user.name || "Unknown"}
- Email: ${user.email || "Not provided"}
- Phone: ${user.phone || "Not provided"}
- Adoption reason: ${reason}

Lifestyle questionnaire:
- Preferred pet type: ${
    lifestyleAnswers?.preferredType || "Not provided"
  }
- Home type: ${lifestyleAnswers?.homeType || "Not provided"}
- Children in home: ${
    lifestyleAnswers?.hasChildren === true
      ? "Yes"
      : lifestyleAnswers?.hasChildren === false
        ? "No"
        : "Not provided"
  }
- Other pets in home: ${
    lifestyleAnswers?.hasOtherPets === true
      ? "Yes"
      : lifestyleAnswers?.hasOtherPets === false
        ? "No"
        : "Not provided"
  }
- Pet ownership experience: ${
    lifestyleAnswers?.experienceLevel || "Not provided"
  }
- Available daily attention: ${
    lifestyleAnswers?.availableAttentionHours || "Not provided"
  } hours
- Activity level: ${
    lifestyleAnswers?.activityLevel || "Not provided"
  }

Pet:
- Name: ${animal.name}
- Type: ${animal.type}
- Breed: ${animal.breed || "Mixed breed"}
- Size: ${animal.size || "Unknown"}
- Age: ${animal.age || "Unknown"}
- Energy level: ${animal.energy_level || "Unknown"}
- Experience required: ${
    animal.experience_required || "Unknown"
  }
- Daily attention required: ${
    animal.daily_attention_hours || "Unknown"
  } hours
- Apartment friendly: ${
    animal.apartment_friendly ? "Yes" : "No"
  }
- Child friendly: ${animal.child_friendly ? "Yes" : "No"}
- Pet friendly: ${animal.pet_friendly ? "Yes" : "No"}

Compatibility score:
${
  compatibilityScore !== null &&
  compatibilityScore !== undefined
    ? `${compatibilityScore}%`
    : "Not available"
}

Requirements:
- Write one paragraph between 70 and 110 words.
- Write for shelter staff, not the adopter.
- Explain important strengths and possible concerns.
- Use only the supplied information.
- Do not invent facts.
- Do not approve or reject the application.
- State that the shelter must conduct its normal review.
- Return only the paragraph.
`.trim();
}

export async function generateShelterSummary(data) {
  if (!process.env.GEMINI_API_KEY) {
    console.warn(
      "GEMINI_API_KEY is missing. Using fallback shelter summary."
    );

    return createFallbackSummary(data);
  }

  try {
    const ai = new GoogleGenAI({
      apiKey: process.env.GEMINI_API_KEY,
    });

    const response = await ai.models.generateContent({
      model: "gemini-2.5-flash",
      contents: buildPrompt(data),
      config: {
        systemInstruction:
          "You assist animal shelter staff by summarizing adoption applications responsibly. Never invent facts and never make the final approval decision.",
        temperature: 0.3,
      },
    });

    const summary = response.text?.trim();

    return summary || createFallbackSummary(data);
  } catch (error) {
    console.error(
      "Gemini shelter summary generation failed:",
      error
    );

    return createFallbackSummary(data);
  }
}