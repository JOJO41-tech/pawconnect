import pool from "@/lib/db";

export async function GET() {
  try {
    const [rows] = await pool.query(`
      SELECT 
        volunteer_requests.id,
        volunteer_requests.message,
        volunteer_requests.status,
        volunteer_requests.created_at,
        users.name AS user_name,
        users.email AS user_email,
        volunteer_opportunities.title AS opportunity_title
      FROM volunteer_requests
      JOIN users ON volunteer_requests.user_id = users.id
      JOIN volunteer_opportunities 
      ON volunteer_requests.opportunity_id = volunteer_opportunities.id
      ORDER BY volunteer_requests.id DESC
    `);

    return Response.json(rows);
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}

export async function PUT(request) {
  try {
    const { id, status } = await request.json();

    await pool.query(
      "UPDATE volunteer_requests SET status = ? WHERE id = ?",
      [status, id]
    );

    return Response.json({ message: "Volunteer request updated" });
  } catch (error) {
    return Response.json({ error: error.message }, { status: 500 });
  }
}