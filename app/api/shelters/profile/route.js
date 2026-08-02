import pool from "@/lib/db";

export async function GET(request) {
  try {
    const { searchParams } = new URL(request.url);
    const shelterId = searchParams.get("shelter_id");

    if (!shelterId) {
      return Response.json(
        { error: "Shelter ID is required." },
        { status: 400 }
      );
    }

    const [rows] = await pool.query(
      `
      SELECT
        shelters.id AS shelter_id,
        shelters.user_id,
        shelters.shelter_name,
        shelters.location,
        shelters.contact_number,
        shelters.description,
        shelters.verification_link,
        shelters.status,
        users.name AS contact_person,
        users.email,
        users.phone
      FROM shelters
      INNER JOIN users
        ON shelters.user_id = users.id
      WHERE shelters.id = ?
      LIMIT 1
      `,
      [shelterId]
    );

    if (rows.length === 0) {
      return Response.json(
        { error: "Shelter profile not found." },
        { status: 404 }
      );
    }

    return Response.json(rows[0]);
  } catch (error) {
    console.error("Load shelter profile error:", error);

    return Response.json(
      {
        error:
          error.message || "Shelter profile could not be loaded.",
      },
      { status: 500 }
    );
  }
}

export async function PUT(request) {
  const connection = await pool.getConnection();

  try {
    const {
      shelter_id,
      contact_person,
      shelter_name,
      location,
      contact_number,
      description,
      verification_link,
    } = await request.json();

    if (
      !shelter_id ||
      !contact_person?.trim() ||
      !shelter_name?.trim() ||
      !location?.trim()
    ) {
      return Response.json(
        {
          error:
            "Contact person, shelter name, and location are required.",
        },
        { status: 400 }
      );
    }

    await connection.beginTransaction();

    const [shelterRows] = await connection.query(
      `
      SELECT user_id
      FROM shelters
      WHERE id = ?
      LIMIT 1
      `,
      [shelter_id]
    );

    if (shelterRows.length === 0) {
      await connection.rollback();

      return Response.json(
        { error: "Shelter profile not found." },
        { status: 404 }
      );
    }

    const userId = shelterRows[0].user_id;

    await connection.query(
      `
      UPDATE users
      SET
        name = ?,
        phone = ?
      WHERE id = ?
      `,
      [
        contact_person.trim(),
        contact_number?.trim() || null,
        userId,
      ]
    );

    await connection.query(
      `
      UPDATE shelters
      SET
        shelter_name = ?,
        location = ?,
        contact_number = ?,
        description = ?,
        verification_link = ?
      WHERE id = ?
      `,
      [
        shelter_name.trim(),
        location.trim(),
        contact_number?.trim() || null,
        description?.trim() || null,
        verification_link?.trim() || null,
        shelter_id,
      ]
    );

    await connection.commit();

    const [updatedRows] = await connection.query(
      `
      SELECT
        shelters.id AS shelter_id,
        shelters.user_id,
        shelters.shelter_name,
        shelters.location,
        shelters.contact_number,
        shelters.description,
        shelters.verification_link,
        shelters.status,
        users.name AS contact_person,
        users.email,
        users.phone
      FROM shelters
      INNER JOIN users
        ON shelters.user_id = users.id
      WHERE shelters.id = ?
      LIMIT 1
      `,
      [shelter_id]
    );

    return Response.json({
      message: "Shelter profile updated successfully.",
      shelter: updatedRows[0],
    });
  } catch (error) {
    await connection.rollback();

    console.error("Update shelter profile error:", error);

    return Response.json(
      {
        error:
          error.message || "Shelter profile could not be updated.",
      },
      { status: 500 }
    );
  } finally {
    connection.release();
  }
}