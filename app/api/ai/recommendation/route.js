import { NextResponse } from "next/server";
import db from "@/lib/db";

export async function POST(request) {
  try {
    const body = await request.json();
    const text = body?.text?.trim();

    if (!text) {
      return NextResponse.json(
        {
          error:
            "Please describe your lifestyle and pet preferences.",
        },
        { status: 400 }
      );
    }

    // Get available animals from database
    const [animals] = await db.query(`
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
      FROM animals
      WHERE LOWER(adoption_status) = 'available'
      ORDER BY id DESC
      LIMIT 100
    `);

    if (!animals.length) {
      return NextResponse.json(
        {
          error: "No available animals found.",
        },
        { status: 404 }
      );
    }

    // Send everything to FastAPI
    const aiResponse = await fetch(
      "http://127.0.0.1:8000/recommend",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        cache: "no-store",
        body: JSON.stringify({
          text,
          animals,
        }),
      }
    );

    const result = await aiResponse.json();

    if (!aiResponse.ok) {
      return NextResponse.json(result, {
        status: aiResponse.status,
      });
    }

    return NextResponse.json(result);
  } catch (error) {
    console.error(error);

    return NextResponse.json(
      {
        error: error.message,
      },
      {
        status: 500,
      }
    );
  }
}