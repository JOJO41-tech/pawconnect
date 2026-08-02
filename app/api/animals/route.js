import pool from "@/lib/db";

export async function GET() {
  try {
    const [rows] = await pool.query(
      "SELECT * FROM animals ORDER BY id DESC"
    );

    return Response.json(rows);
  } catch (error) {
    return Response.json(
      { error: error.message },
      { status: 500 }
    );
  }
}

export async function POST(request) {
  try {
    const body = await request.json();

    const {
      shelter_id,
      name,
      type,
      breed,
      size,
      age,
      gender,
      temperament,
      location,
      health_status,
      vaccination_status,
      sterilization_status,
      description,
      image_url,
      adoption_status,

      // AI Fields
      energy_level,
      apartment_friendly,
      child_friendly,
      pet_friendly,
      experience_required,
      daily_attention_hours,
    } = body;

    if (!name || !type) {
      return Response.json(
        { error: "Animal name and type are required." },
        { status: 400 }
      );
    }

    const [result] = await pool.query(
      `
      INSERT INTO animals
      (
        shelter_id,
        name,
        type,
        breed,
        size,
        age,
        gender,
        temperament,
        location,
        health_status,
        vaccination_status,
        sterilization_status,
        description,
        image_url,
        adoption_status,
        energy_level,
        apartment_friendly,
        child_friendly,
        pet_friendly,
        experience_required,
        daily_attention_hours
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `,
      [
        shelter_id || 1,
        name,
        type,
        breed || null,
        size || null,
        age || null,
        gender || null,
        temperament || null,
        location || null,
        health_status || null,
        vaccination_status || null,
        sterilization_status || null,
        description || null,
        image_url || null,
        adoption_status || "available",

        energy_level || "Medium",
        apartment_friendly ?? 1,
        child_friendly ?? 1,
        pet_friendly ?? 1,
        experience_required || "Beginner",
        daily_attention_hours || 2,
      ]
    );

    return Response.json(
      {
        message: "Animal added successfully.",
        id: result.insertId,
      },
      { status: 201 }
    );
  } catch (error) {
    return Response.json(
      { error: error.message },
      { status: 500 }
    );
  }
}

export async function PUT(request) {
  try {
    const body = await request.json();

    const {
      id,
      name,
      type,
      breed,
      size,
      age,
      gender,
      temperament,
      location,
      health_status,
      vaccination_status,
      sterilization_status,
      description,
      image_url,
      adoption_status,

      // AI Fields
      energy_level,
      apartment_friendly,
      child_friendly,
      pet_friendly,
      experience_required,
      daily_attention_hours,
    } = body;

    if (!id) {
      return Response.json(
        { error: "Animal ID is required." },
        { status: 400 }
      );
    }

    const [result] = await pool.query(
      `
      UPDATE animals
      SET
        name = ?,
        type = ?,
        breed = ?,
        size = ?,
        age = ?,
        gender = ?,
        temperament = ?,
        location = ?,
        health_status = ?,
        vaccination_status = ?,
        sterilization_status = ?,
        description = ?,
        image_url = ?,
        adoption_status = ?,
        energy_level = ?,
        apartment_friendly = ?,
        child_friendly = ?,
        pet_friendly = ?,
        experience_required = ?,
        daily_attention_hours = ?
      WHERE id = ?
      `,
      [
        name,
        type,
        breed || null,
        size || null,
        age || null,
        gender || null,
        temperament || null,
        location || null,
        health_status || null,
        vaccination_status || null,
        sterilization_status || null,
        description || null,
        image_url || null,
        adoption_status || "available",

        energy_level || "Medium",
        apartment_friendly ?? 1,
        child_friendly ?? 1,
        pet_friendly ?? 1,
        experience_required || "Beginner",
        daily_attention_hours || 2,

        id,
      ]
    );

    if (result.affectedRows === 0) {
      return Response.json(
        { error: "Animal not found." },
        { status: 404 }
      );
    }

    return Response.json({
      message: "Animal updated successfully.",
    });
  } catch (error) {
    return Response.json(
      { error: error.message },
      { status: 500 }
    );
  }
}

export async function DELETE(request) {
  try {
    const { id } = await request.json();

    if (!id) {
      return Response.json(
        { error: "Animal ID is required." },
        { status: 400 }
      );
    }

    const [result] = await pool.query(
      "DELETE FROM animals WHERE id = ?",
      [id]
    );

    if (result.affectedRows === 0) {
      return Response.json(
        { error: "Animal not found." },
        { status: 404 }
      );
    }

    return Response.json({
      message: "Animal deleted successfully.",
    });
  } catch (error) {
    return Response.json(
      { error: error.message },
      { status: 500 }
    );
  }
}