import pool from "@/lib/db";

export async function GET(request, context) {
  try {
    const { id } = await context.params;

    if (!id) {
      return Response.json(
        { error: "Animal ID is required." },
        { status: 400 }
      );
    }

    const [rows] = await pool.query(
      `
      SELECT
        animals.*,
        shelters.shelter_name,
        shelters.location AS shelter_location,
        shelters.contact_number,
        shelters.description AS shelter_description,
        shelters.verification_link
      FROM animals
      LEFT JOIN shelters
        ON animals.shelter_id = shelters.id
      WHERE animals.id = ?
      LIMIT 1
      `,
      [id]
    );

    if (rows.length === 0) {
      return Response.json(
        { error: "Animal not found." },
        { status: 404 }
      );
    }

    return Response.json(rows[0]);
  } catch (error) {
    console.error("GET animal error:", error);

    return Response.json(
      { error: error.message || "Failed to load animal." },
      { status: 500 }
    );
  }
}