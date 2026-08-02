import pool from "@/lib/db";

export async function POST(request) {
  try {
    const { email, password } = await request.json();

    const [rows] = await pool.query(
      `
      SELECT 
        users.id,
        users.name,
        users.email,
        users.role,
        shelters.id AS shelter_id,
        shelters.shelter_name,
        shelters.status
      FROM users
      LEFT JOIN shelters ON users.id = shelters.user_id
      WHERE users.email = ? 
      AND users.password = ? 
      AND users.role = 'shelter'
      `,
      [email, password]
    );

    if (rows.length === 0) {
      return Response.json(
        { error: "Invalid shelter email or password" },
        { status: 401 }
      );
    }

    const shelter = rows[0];

    return Response.json({
      message: "Login successful",
      shelter,
    });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}