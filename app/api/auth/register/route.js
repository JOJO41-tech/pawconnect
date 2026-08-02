import pool from "@/lib/db";

export async function POST(request) {
  try {
    const { name, email, password, phone } = await request.json();

    if (!name?.trim() || !email?.trim() || !password) {
      return Response.json(
        {
          error: "Name, email, and password are required.",
        },
        { status: 400 }
      );
    }

    const normalizedEmail = email.trim().toLowerCase();

    const [existingUsers] = await pool.query(
      `
      SELECT id
      FROM users
      WHERE email = ?
      LIMIT 1
      `,
      [normalizedEmail]
    );

    if (existingUsers.length > 0) {
      return Response.json(
        {
          error: "An account with this email already exists.",
        },
        { status: 409 }
      );
    }

    const [result] = await pool.query(
      `
      INSERT INTO users
      (
        name,
        email,
        password,
        role,
        phone
      )
      VALUES (?, ?, ?, 'user', ?)
      `,
      [
        name.trim(),
        normalizedEmail,
        password,
        phone?.trim() || null,
      ]
    );

    return Response.json(
      {
        message: "User account created successfully.",
        user: {
          id: result.insertId,
          name: name.trim(),
          email: normalizedEmail,
          role: "user",
          phone: phone?.trim() || null,
        },
      },
      { status: 201 }
    );
  } catch (error) {
    console.error("User registration error:", error);

    return Response.json(
      {
        error: error.message || "User registration failed.",
      },
      { status: 500 }
    );
  }
}