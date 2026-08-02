import pool from "@/lib/db";

export async function POST(request) {
  try {
    const { email, password } = await request.json();

    if (!email?.trim() || !password) {
      return Response.json(
        { error: "Email and password are required." },
        { status: 400 }
      );
    }

    const normalizedEmail = email.trim().toLowerCase();

    const [rows] = await pool.query(
      `
      SELECT
        id,
        name,
        email,
        role,
        phone
      FROM users
      WHERE email = ?
      AND password = ?
      AND role = 'user'
      LIMIT 1
      `,
      [normalizedEmail, password]
    );

    if (rows.length === 0) {
      return Response.json(
        { error: "Invalid user email or password." },
        { status: 401 }
      );
    }

    const user = rows[0];

    return Response.json({
      message: "Login successful.",
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role,
        phone: user.phone,
      },
    });
  } catch (error) {
    console.error("User login error:", error);

    return Response.json(
      { error: error.message || "Login failed." },
      { status: 500 }
    );
  }
}