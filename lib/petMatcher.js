function normalize(value) {
  return String(value || "").trim().toLowerCase();
}

function getExperienceValue(level) {
  const levels = {
    beginner: 1,
    intermediate: 2,
    experienced: 3,
  };

  return levels[normalize(level)] || 1;
}

export function calculatePetMatch(pet, answers) {
  let score = 0;
  let maximumScore = 0;

  const reasons = [];
  const concerns = [];

  // Preferred pet type
  maximumScore += 20;

  const preferredType = normalize(answers.preferredType);
  const petType = normalize(pet.type);

  if (
    !preferredType ||
    preferredType === "any" ||
    preferredType === petType
  ) {
    score += 20;

    if (preferredType !== "any") {
      reasons.push(`Matches your preferred pet type.`);
    }
  } else {
    concerns.push(
      `You preferred a ${answers.preferredType}, but ${pet.name} is a ${pet.type}.`
    );
  }

  // Living environment
  maximumScore += 20;

  if (normalize(answers.homeType) === "house") {
    score += 20;
    reasons.push("Suitable for your living environment.");
  } else if (Number(pet.apartment_friendly) === 1) {
    score += 20;
    reasons.push("Suitable for apartment living.");
  } else {
    concerns.push("May not be suitable for apartment living.");
  }

  // Children
  maximumScore += 15;

  if (!answers.hasChildren) {
    score += 15;
  } else if (Number(pet.child_friendly) === 1) {
    score += 15;
    reasons.push("Reported as friendly with children.");
  } else {
    concerns.push("May not be suitable for a home with children.");
  }

  // Other pets
  maximumScore += 15;

  if (!answers.hasOtherPets) {
    score += 15;
  } else if (Number(pet.pet_friendly) === 1) {
    score += 15;
    reasons.push("Reported as friendly with other pets.");
  } else {
    concerns.push("May need careful introduction to other pets.");
  }

  // Owner experience
  maximumScore += 15;

  const userExperience = getExperienceValue(
    answers.experienceLevel
  );

  const requiredExperience = getExperienceValue(
    pet.experience_required
  );

  if (userExperience >= requiredExperience) {
    score += 15;
    reasons.push(
      `Suitable for your ${answers.experienceLevel} experience level.`
    );
  } else {
    concerns.push(
      `May require a more experienced pet owner.`
    );
  }

  // Daily attention
  maximumScore += 15;

  const availableHours = Number(
    answers.availableAttentionHours || 0
  );

  const requiredHours = Number(
    pet.daily_attention_hours || 2
  );

  if (availableHours >= requiredHours) {
    score += 15;
    reasons.push(
      "Your available time meets the pet's daily attention needs."
    );
  } else if (availableHours >= requiredHours - 1) {
    score += 8;
    concerns.push(
      `This pet may need slightly more daily attention.`
    );
  } else {
    concerns.push(
      `This pet needs about ${requiredHours} hours of attention per day.`
    );
  }

  // Activity level
  maximumScore += 15;

  const userActivity = normalize(answers.activityLevel);
  const petEnergy = normalize(pet.energy_level);

  if (userActivity === petEnergy) {
    score += 15;
    reasons.push("The pet's energy level matches your lifestyle.");
  } else if (
    (userActivity === "medium" && petEnergy === "low") ||
    (userActivity === "high" && petEnergy === "medium")
  ) {
    score += 10;
    reasons.push(
      "The pet's energy level is reasonably compatible with your lifestyle."
    );
  } else {
    concerns.push(
      `The pet has a ${pet.energy_level || "medium"} energy level.`
    );
  }

  const compatibilityScore = Math.round(
    (score / maximumScore) * 100
  );

  return {
    ...pet,
    compatibilityScore,
    matchReasons: reasons,
    concerns,
  };
}

export function rankPets(pets, answers) {
  return pets
    .filter(
      (pet) =>
        normalize(pet.adoption_status) === "available"
    )
    .map((pet) => calculatePetMatch(pet, answers))
    .sort(
      (firstPet, secondPet) =>
        secondPet.compatibilityScore -
        firstPet.compatibilityScore
    );
}