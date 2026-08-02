import pool from "@/lib/db";

export async function GET() {
  try {
    const [rows] = await pool.query(
      "SELECT * FROM volunteer_opportunities ORDER BY id DESC"
    );

    return Response.json(rows);
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const { title, description, location, status } = await request.json();

    await pool.query(
      `INSERT INTO volunteer_opportunities
      (shelter_id, title, description, location, status)
      VALUES (?, ?, ?, ?, ?)`,
      [1, title, description, location, status || "open"]
    );

    return Response.json({ message: "Volunteer post created" });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}

export async function DELETE(request) {
  try {
    const { id } = await request.json();

    await pool.query("DELETE FROM volunteer_opportunities WHERE id = ?", [id]);

    return Response.json({ message: "Volunteer post deleted" });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}