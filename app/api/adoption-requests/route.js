import pool from "@/lib/db";
import { generateShelterSummary } from "@/lib/geminiShelterSummary";

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);

    const userId = searchParams.get("user_id");
    const shelterId = searchParams.get("shelter_id");

    let sql = `
      SELECT
        ar.id,
        ar.user_id,
        ar.animal_id,
        ar.reason,
        ar.status,
        ar.compatibility_score,
        ar.ai_summary,
        ar.lifestyle_answers,
        ar.created_at,

        u.name AS user_name,
        u.email AS user_email,
        u.phone AS user_phone,

        a.name AS animal_name,
        a.type AS animal_type,
        a.breed AS animal_breed,
        a.image_url,
        a.shelter_id,
        a.adoption_status,

        s.shelter_name

      FROM adoption_requests ar

      LEFT JOIN users u
        ON ar.user_id = u.id

      LEFT JOIN animals a
        ON ar.animal_id = a.id

      LEFT JOIN shelters s
        ON a.shelter_id = s.id
    `;

    const values = [];
    const conditions = [];

    if (userId) {
      conditions.push("ar.user_id = ?");
      values.push(userId);
    }

    if (shelterId) {
      conditions.push("a.shelter_id = ?");
      values.push(shelterId);
    }

    if (conditions.length > 0) {
      sql += ` WHERE ${conditions.join(" AND ")}`;
    }

    sql += " ORDER BY ar.id DESC";

    const [rows] = await pool.query(sql, values);

    const formattedRows = rows.map((row) => ({
      ...row,
      lifestyle_answers:
        typeof row.lifestyle_answers === "string"
          ? safeParseJSON(row.lifestyle_answers)
          : row.lifestyle_answers,
    }));

    return Response.json(formattedRows);
  } catch (error) {
    console.error("GET adoption requests error:", error);

    return Response.json(
      {
        error:
          error.message ||
          "Failed to load adoption requests.",
      },
      { status: 500 }
    );
  }
}

export async function POST(request) {
  try {
    const body = await request.json();

    const {
      user_id,
      animal_id,
      reason,
      compatibility_score = null,
      lifestyle_answers = null,
    } = body;

    if (!user_id || !animal_id || !reason?.trim()) {
      return Response.json(
        {
          error:
            "User, animal, and adoption reason are required.",
        },
        { status: 400 }
      );
    }

    const parsedUserId = Number(user_id);
    const parsedAnimalId = Number(animal_id);

    if (
      !Number.isInteger(parsedUserId) ||
      parsedUserId <= 0 ||
      !Number.isInteger(parsedAnimalId) ||
      parsedAnimalId <= 0
    ) {
      return Response.json(
        {
          error:
            "User ID and animal ID must be valid numbers.",
        },
        { status: 400 }
      );
    }

    const parsedScore =
      compatibility_score === null ||
      compatibility_score === undefined ||
      compatibility_score === ""
        ? null
        : Number(compatibility_score);

    if (
      parsedScore !== null &&
      (!Number.isFinite(parsedScore) ||
        parsedScore < 0 ||
        parsedScore > 100)
    ) {
      return Response.json(
        {
          error:
            "Compatibility score must be between 0 and 100.",
        },
        { status: 400 }
      );
    }

    const [users] = await pool.query(
      `
      SELECT
        id,
        name,
        email,
        phone
      FROM users
      WHERE id = ?
      LIMIT 1
      `,
      [parsedUserId]
    );

    if (users.length === 0) {
      return Response.json(
        {
          error: "User not found.",
        },
        { status: 404 }
      );
    }

    const [animals] = await pool.query(
      `
      SELECT
        id,
        shelter_id,
        name,
        type,
        breed,
        size,
        age,
        gender,
        temperament,
        location,
        adoption_status,
        energy_level,
        apartment_friendly,
        child_friendly,
        pet_friendly,
        experience_required,
        daily_attention_hours
      FROM animals
      WHERE id = ?
      LIMIT 1
      `,
      [parsedAnimalId]
    );

    if (animals.length === 0) {
      return Response.json(
        {
          error: "Animal not found.",
        },
        { status: 404 }
      );
    }

    const animal = animals[0];
    const user = users[0];

    if (
      String(animal.adoption_status || "").toLowerCase() !==
      "available"
    ) {
      return Response.json(
        {
          error:
            "This animal is not available for adoption.",
        },
        { status: 400 }
      );
    }

    const [existingRequests] = await pool.query(
      `
      SELECT id
      FROM adoption_requests
      WHERE user_id = ?
        AND animal_id = ?
        AND status = 'pending'
      LIMIT 1
      `,
      [parsedUserId, parsedAnimalId]
    );

    if (existingRequests.length > 0) {
      return Response.json(
        {
          error:
            "You already submitted a pending application.",
        },
        { status: 409 }
      );
    }

    const safeLifestyleAnswers =
      lifestyle_answers &&
      typeof lifestyle_answers === "object" &&
      !Array.isArray(lifestyle_answers)
        ? lifestyle_answers
        : null;

    let aiSummary = null;

    try {
      aiSummary = await generateShelterSummary({
        user,
        animal,
        reason: reason.trim(),
        compatibilityScore: parsedScore,
        lifestyleAnswers: safeLifestyleAnswers,
      });
    } catch (error) {
      console.error(
        "AI shelter summary generation error:",
        error
      );

      aiSummary =
        "AI summary could not be generated. Please review the applicant information manually.";
    }

    const [result] = await pool.query(
      `
      INSERT INTO adoption_requests (
        user_id,
        animal_id,
        reason,
        status,
        compatibility_score,
        ai_summary,
        lifestyle_answers
      )
      VALUES (?, ?, ?, 'pending', ?, ?, ?)
      `,
      [
        parsedUserId,
        parsedAnimalId,
        reason.trim(),
        parsedScore,
        aiSummary,
        safeLifestyleAnswers
          ? JSON.stringify(safeLifestyleAnswers)
          : null,
      ]
    );

    return Response.json(
      {
        message:
          "Adoption application submitted successfully.",
        id: result.insertId,
        compatibility_score: parsedScore,
        ai_summary: aiSummary,
      },
      { status: 201 }
    );
  } catch (error) {
    console.error("POST adoption request error:", error);

    return Response.json(
      {
        error:
          error.message ||
          "Application submission failed.",
      },
      { status: 500 }
    );
  }
}

export async function PUT(request) {
  const connection = await pool.getConnection();
  let transactionStarted = false;

  try {
    const body = await request.json();

    const requestId = Number(body.id);
    const newStatus = String(body.status || "")
      .trim()
      .toLowerCase();

    const allowedStatuses = [
      "approved",
      "rejected",
    ];

    if (
      !Number.isInteger(requestId) ||
      requestId <= 0 ||
      !allowedStatuses.includes(newStatus)
    ) {
      return Response.json(
        {
          error:
            "A valid request ID and status are required.",
        },
        { status: 400 }
      );
    }

    await connection.beginTransaction();
    transactionStarted = true;

    const [requests] = await connection.query(
      `
      SELECT
        ar.id,
        ar.animal_id,
        ar.status AS request_status,
        a.adoption_status
      FROM adoption_requests ar
      INNER JOIN animals a
        ON ar.animal_id = a.id
      WHERE ar.id = ?
      LIMIT 1
      FOR UPDATE
      `,
      [requestId]
    );

    if (requests.length === 0) {
      await connection.rollback();
      transactionStarted = false;

      return Response.json(
        {
          error: "Adoption request not found.",
        },
        { status: 404 }
      );
    }

    const adoptionRequest = requests[0];

    const animalId =
      adoptionRequest.animal_id;

    const currentRequestStatus = String(
      adoptionRequest.request_status || ""
    ).toLowerCase();

    const currentAnimalStatus = String(
      adoptionRequest.adoption_status || ""
    ).toLowerCase();

    if (currentRequestStatus !== "pending") {
      await connection.rollback();
      transactionStarted = false;

      return Response.json(
        {
          error: `This application has already been ${currentRequestStatus}.`,
        },
        { status: 409 }
      );
    }

    if (newStatus === "approved") {
      if (currentAnimalStatus === "adopted") {
        await connection.rollback();
        transactionStarted = false;

        return Response.json(
          {
            error:
              "This animal has already been adopted.",
          },
          { status: 409 }
        );
      }

      const [approvedResult] =
        await connection.query(
          `
          UPDATE adoption_requests
          SET status = 'approved'
          WHERE id = ?
            AND status = 'pending'
          `,
          [requestId]
        );

      if (approvedResult.affectedRows === 0) {
        throw new Error(
          "The adoption request could not be approved."
        );
      }

      await connection.query(
        `
        UPDATE animals
        SET adoption_status = 'adopted'
        WHERE id = ?
        `,
        [animalId]
      );

      await connection.query(
        `
        UPDATE adoption_requests
        SET status = 'rejected'
        WHERE animal_id = ?
          AND id <> ?
          AND status = 'pending'
        `,
        [animalId, requestId]
      );
    }

    if (newStatus === "rejected") {
      const [rejectedResult] =
        await connection.query(
          `
          UPDATE adoption_requests
          SET status = 'rejected'
          WHERE id = ?
            AND status = 'pending'
          `,
          [requestId]
        );

      if (rejectedResult.affectedRows === 0) {
        throw new Error(
          "The adoption request could not be rejected."
        );
      }

      const [approvedRequests] =
        await connection.query(
          `
          SELECT id
          FROM adoption_requests
          WHERE animal_id = ?
            AND status = 'approved'
          LIMIT 1
          `,
          [animalId]
        );

      if (approvedRequests.length === 0) {
        await connection.query(
          `
          UPDATE animals
          SET adoption_status = 'available'
          WHERE id = ?
            AND adoption_status <> 'adopted'
          `,
          [animalId]
        );
      }
    }

    await connection.commit();
    transactionStarted = false;

    return Response.json({
      message: `Adoption request ${newStatus} successfully.`,
      request_id: requestId,
      animal_id: animalId,
      status: newStatus,
    });
  } catch (error) {
    if (transactionStarted) {
      try {
        await connection.rollback();
      } catch (rollbackError) {
        console.error(
          "Transaction rollback error:",
          rollbackError
        );
      }
    }

    console.error(
      "PUT adoption request error:",
      error
    );

    return Response.json(
      {
        error:
          error.message ||
          "Request update failed.",
      },
      { status: 500 }
    );
  } finally {
    connection.release();
  }
}

function safeParseJSON(value) {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}