import pool from "@/lib/db";

export async function POST(request) {
  try {
    const body = await request.json();

    const {
      name,
      email,
      password,
      phone,
      shelter_name,
      location,
      contact_number,
      description,
      verification_link,
    } = body;

    const [userResult] = await pool.query(
      `INSERT INTO users (name, email, password, role, phone)
       VALUES (?, ?, ?, ?, ?)`,
      [name, email, password, "shelter", phone]
    );

    const userId = userResult.insertId;

    await pool.query(
      `INSERT INTO shelters
      (user_id, shelter_name, location, contact_number, description, verification_link, status)
      VALUES (?, ?, ?, ?, ?, ?, ?)`,
      [
        userId,
        shelter_name,
        location,
        contact_number,
        description,
        verification_link,
        "pending",
      ]
    );

    return Response.json({
      message: "Shelter account created successfully.",
    });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}